import os
import difflib
from autocoder.common import AutoCoderArgs,git_utils
from typing import List,Union,Tuple
import pydantic
import byzerllm
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common.printer import Printer
import hashlib
from pathlib import Path
from itertools import groupby
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.common.search_replace import (
    SearchTextNotUnique,
    all_preprocs,
    diff_lines,
    flexible_search_and_replace,
    search_and_replace,
)
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common.code_modification_ranker import CodeModificationRanker
from autocoder.common import files as FileUtils

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str

def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)    

def do_replace(fname, content, hunk):
    fname = Path(fname)

    before_text, after_text = hunk_to_before_after(hunk)

    # does it want to make a new file?
    if not fname.exists() and not before_text.strip():
        fname.touch()
        content = ""

    if content is None:
        return

    # TODO: handle inserting into new file
    if not before_text.strip():
        # append to existing file, or start a new file
        new_content = content + after_text
        return new_content

    new_content = None

    new_content = apply_hunk(content, hunk)
    if new_content:
        return new_content


def collapse_repeats(s):
    return "".join(k for k, g in groupby(s))


def apply_hunk(content, hunk):
    before_text, after_text = hunk_to_before_after(hunk)

    res = directly_apply_hunk(content, hunk)
    if res:
        return res

    hunk = make_new_lines_explicit(content, hunk)

    # just consider space vs not-space
    ops = "".join([line[0] for line in hunk])
    ops = ops.replace("-", "x")
    ops = ops.replace("+", "x")
    ops = ops.replace("\n", " ")

    cur_op = " "
    section = []
    sections = []

    for i in range(len(ops)):
        op = ops[i]
        if op != cur_op:
            sections.append(section)
            section = []
            cur_op = op
        section.append(hunk[i])

    sections.append(section)
    if cur_op != " ":
        sections.append([])

    all_done = True
    for i in range(2, len(sections), 2):
        preceding_context = sections[i - 2]
        changes = sections[i - 1]
        following_context = sections[i]

        res = apply_partial_hunk(content, preceding_context, changes, following_context)
        if res:
            content = res
        else:
            all_done = False
            # FAILED!
            # this_hunk = preceding_context + changes + following_context
            break

    if all_done:
        return content


def flexi_just_search_and_replace(texts):
    strategies = [
        (search_and_replace, all_preprocs),
    ]

    return flexible_search_and_replace(texts, strategies)


def make_new_lines_explicit(content, hunk):
    before, after = hunk_to_before_after(hunk)

    diff = diff_lines(before, content)

    back_diff = []
    for line in diff:
        if line[0] == "+":
            continue
        # if line[0] == "-":
        #    line = "+" + line[1:]

        back_diff.append(line)

    new_before = directly_apply_hunk(before, back_diff)
    if not new_before:
        return hunk

    if len(new_before.strip()) < 10:
        return hunk

    before = before.splitlines(keepends=True)
    new_before = new_before.splitlines(keepends=True)
    after = after.splitlines(keepends=True)

    if len(new_before) < len(before) * 0.66:
        return hunk

    new_hunk = difflib.unified_diff(new_before, after, n=max(len(new_before), len(after)))
    new_hunk = list(new_hunk)[3:]

    return new_hunk


def cleanup_pure_whitespace_lines(lines):
    res = [
        line if line.strip() else line[-(len(line) - len(line.rstrip("\r\n")))] for line in lines
    ]
    return res


def normalize_hunk(hunk):
    before, after = hunk_to_before_after(hunk, lines=True)

    before = cleanup_pure_whitespace_lines(before)
    after = cleanup_pure_whitespace_lines(after)

    diff = difflib.unified_diff(before, after, n=max(len(before), len(after)))
    diff = list(diff)[3:]
    return diff


def directly_apply_hunk(content, hunk):
    before, after = hunk_to_before_after(hunk)

    if not before:
        return

    before_lines, _ = hunk_to_before_after(hunk, lines=True)
    before_lines = "".join([line.strip() for line in before_lines])

    # Refuse to do a repeated search and replace on a tiny bit of non-whitespace context
    if len(before_lines) < 10 and content.count(before) > 1:
        return

    try:
        new_content = flexi_just_search_and_replace([before, after, content])
    except SearchTextNotUnique:
        new_content = None

    return new_content


def apply_partial_hunk(content, preceding_context, changes, following_context):
    len_prec = len(preceding_context)
    len_foll = len(following_context)

    use_all = len_prec + len_foll

    # if there is a - in the hunk, we can go all the way to `use=0`
    for drop in range(use_all + 1):
        use = use_all - drop

        for use_prec in range(len_prec, -1, -1):
            if use_prec > use:
                continue

            use_foll = use - use_prec
            if use_foll > len_foll:
                continue

            if use_prec:
                this_prec = preceding_context[-use_prec:]
            else:
                this_prec = []

            this_foll = following_context[:use_foll]

            res = directly_apply_hunk(content, this_prec + changes + this_foll)
            if res:
                return res


def find_diffs(content):
    # We can always fence with triple-quotes, because all the udiff content
    # is prefixed with +/-/space.

    if not content.endswith("\n"):
        content = content + "\n"

    lines = content.splitlines(keepends=True)
    line_num = 0
    edits = []
    while line_num < len(lines):
        while line_num < len(lines):
            line = lines[line_num]
            if line.startswith("```diff"):
                line_num, these_edits = process_fenced_block(lines, line_num + 1)
                edits += these_edits
                break
            line_num += 1

    # For now, just take 1!
    # edits = edits[:1]

    return edits


def process_fenced_block(lines, start_line_num):
    for line_num in range(start_line_num, len(lines)):
        line = lines[line_num]
        if line.startswith("```"):
            break

    block = lines[start_line_num:line_num]
    block.append("@@ @@")

    if block[0].startswith("--- ") and block[1].startswith("+++ "):
        # Extract the file path, considering that it might contain spaces
        fname = block[1][4:].strip()
        block = block[2:]
    else:
        fname = None

    edits = []

    keeper = False
    hunk = []
    op = " "
    for line in block:
        hunk.append(line)
        if len(line) < 2:
            continue

        if line.startswith("+++ ") and hunk[-2].startswith("--- "):
            if hunk[-3] == "\n":
                hunk = hunk[:-3]
            else:
                hunk = hunk[:-2]

            edits.append((fname, hunk))
            hunk = []
            keeper = False

            fname = line[4:].strip()
            continue

        op = line[0]
        if op in "-+":
            keeper = True
            continue
        if op != "@":
            continue
        if not keeper:
            hunk = []
            continue

        hunk = hunk[:-1]
        edits.append((fname, hunk))
        hunk = []
        keeper = False

    return line_num + 1, edits


def hunk_to_before_after(hunk, lines=False):
    before = []
    after = []
    op = " "
    for line in hunk:
        if len(line) < 2:
            op = " "
            line = line
        else:
            op = line[0]
            line = line[1:]

        if op == " ":
            before.append(line)
            after.append(line)
        elif op == "-":
            before.append(line)
        elif op == "+":
            after.append(line)

    if lines:
        return before, after

    before = "".join(before)
    after = "".join(after)

    return before, after

no_match_error = """UnifiedDiffNoMatch: hunk failed to apply!

{path} does not contain lines that match the diff you provided!
Try again.
DO NOT skip blank lines, comments, docstrings, etc!
The diff needs to apply cleanly to the lines in {path}!

{path} does not contain these {num_lines} exact lines in a row:
```
{original}```
"""


not_unique_error = """UnifiedDiffNotUnique: hunk failed to apply!

{path} contains multiple sets of lines that match the diff you provided!
Try again.
Use additional ` ` lines to provide context that uniquely indicates which code needs to be changed.
The diff needs to apply to a unique set of lines in {path}!

{path} contains multiple copies of these {num_lines} lines:
```
{original}```
"""

other_hunks_applied = (
    "Note: some hunks did apply successfully. See the updated source code shown above.\n\n"
)

class CodeAutoMergeDiff:
    def __init__(self, llm:byzerllm.ByzerLLM,args:AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.printer = Printer()

    def get_edits(self,content:str):        
        # might raise ValueError for malformed ORIG/UPD blocks
        raw_edits = list(find_diffs(content))

        last_path = None
        edits = []
        for path, hunk in raw_edits:
            if path:
                last_path = path
            else:
                path = last_path
            edits.append((path, hunk))

        return edits

    def merge_code(self, generate_result: CodeGenerateResult, force_skip_git: bool = False):
        result = self.choose_best_choice(generate_result)
        self._merge_code(result.contents[0], force_skip_git)
        return result

    def choose_best_choice(self, generate_result: CodeGenerateResult) -> CodeGenerateResult:
        if len(generate_result.contents) == 1:
            return generate_result
        
        merge_results = []
        for content,conversations in zip(generate_result.contents,generate_result.conversations):
            merge_result = self._merge_code_without_effect(content)
            merge_results.append(merge_result)

        # If all merge results are None, return first one
        if all(len(result.failed_blocks) != 0 for result in merge_results):
            self.printer.print_in_terminal("all_merge_results_failed")
            return CodeGenerateResult(contents=[generate_result.contents[0]], conversations=[generate_result.conversations[0]])
        
        # If only one merge result is not None, return that one
        not_none_indices = [i for i, result in enumerate(merge_results) if len(result.failed_blocks) == 0]
        if len(not_none_indices) == 1:
            idx = not_none_indices[0]
            self.printer.print_in_terminal("only_one_merge_result_success")
            return CodeGenerateResult(contents=[generate_result.contents[idx]], conversations=[generate_result.conversations[idx]])        

        # 最后，如果有多个，那么根据质量排序再返回
        ranker = CodeModificationRanker(self.llm, self.args)
        ranked_result = ranker.rank_modifications(generate_result,merge_results)        
         
        ## 得到的结果，再做一次合并，第一个通过的返回 , 返回做合并有点重复低效，未来修改。
        for content,conversations in zip(ranked_result.contents,ranked_result.conversations):
            merge_result = self._merge_code_without_effect(content)
            if not merge_result.failed_blocks:
                return CodeGenerateResult(contents=[content], conversations=[conversations])

        # 最后保底，但实际不会出现
        return CodeGenerateResult(contents=[ranked_result.contents[0]], conversations=[ranked_result.conversations[0]])
    
    @byzerllm.prompt(render="jinja2")
    def git_require_msg(self,source_dir:str,error:str)->str:
        '''
        auto_merge only works for git repositories.
         
        Try to use git init in the source directory. 
        
        ```shell
        cd {{ source_dir }}
        git init .
        ```

        Then try to run auto-coder again.
        Error: {{ error }}
        '''
    
    def abs_root_path(self, path):
        if path.startswith(self.args.source_dir):
            return safe_abs_path(Path(path))
        res = Path(self.args.source_dir) / path
        return safe_abs_path(res)

    def apply_edits(self, edits):
        seen = set()
        uniq = []
        for path, hunk in edits:
            hunk = normalize_hunk(hunk)
            if not hunk:
                continue

            this = [path + "\n"] + hunk
            this = "".join(this)

            if this in seen:
                continue
            seen.add(this)

            uniq.append((path, hunk))

        errors = []
        for path, hunk in uniq:
            full_path = self.abs_root_path(path)

            if not os.path.exists(full_path):            
                with open(full_path, "w") as f:
                    f.write("")
            
            content = FileUtils.read_file(full_path)

            original, _ = hunk_to_before_after(hunk)

            try:
                content = do_replace(full_path, content, hunk)
            except SearchTextNotUnique:
                errors.append(
                    not_unique_error.format(
                        path=path, original=original, num_lines=len(original.splitlines())
                    )
                )
                continue

            if not content:
                errors.append(
                    no_match_error.format(
                        path=path, original=original, num_lines=len(original.splitlines())
                    )
                )
                continue

            # SUCCESS!
            with open(full_path, "w") as f:
                f.write(content)            

        if errors:
            errors = "\n\n".join(errors)
            if len(errors) < len(uniq):
                errors += other_hunks_applied
            raise ValueError(errors)    

    def _merge_code_without_effect(self, content: str) -> MergeCodeWithoutEffect:
        """Merge code without any side effects like git operations or file writing.
        Returns a tuple of:
        - list of (file_path, new_content) tuples for successfully merged blocks
        - list of (file_path, hunk) tuples for failed to merge blocks"""
        edits = self.get_edits(content)
        file_content_mapping = {}
        failed_blocks = []
        
        for path, hunk in edits:
            full_path = self.abs_root_path(path)
            if not os.path.exists(full_path):
                _, after = hunk_to_before_after(hunk)
                file_content_mapping[full_path] = after
                continue
                
            if full_path not in file_content_mapping:
                file_content_mapping[full_path] = FileUtils.read_file(full_path)
            
            content = file_content_mapping[full_path]
            new_content = do_replace(full_path, content, hunk)
            if new_content:
                file_content_mapping[full_path] = new_content
            else:
                failed_blocks.append((full_path, "\n".join(hunk)))
                
        return MergeCodeWithoutEffect(
            success_blocks=[(path, content) for path, content in file_content_mapping.items()],
            failed_blocks=failed_blocks
        )

    def print_edits(self, edits: List[Tuple[str, List[str]]]):
        """Print diffs for user review using rich library"""
        from rich.syntax import Syntax
        from rich.panel import Panel

        # Group edits by file path
        file_edits = {}
        for path, hunk in edits:
            if path not in file_edits:
                file_edits[path] = []
            file_edits[path].append(hunk)

        # Generate formatted text for each file
        formatted_text = ""
        for path, hunks in file_edits.items():
            formatted_text += f"##File: {path}\n"
            for hunk in hunks:
                formatted_text += "".join(hunk)
            formatted_text += "\n"

        # Print with rich panel
        self.printer.print_in_terminal("edits_title", style="bold green")
        self.printer.console.print(
            Panel(
                Syntax(formatted_text, "diff", theme="monokai"),
                title="Edits",
                border_style="green",
                expand=False
            )
        )

    def _merge_code(self, content: str,force_skip_git:bool=False):        
        total = 0
        
        file_content = FileUtils.read_file(self.args.file)
        md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        # get the file name 
        file_name = os.path.basename(self.args.file)
        
        if not force_skip_git and not self.args.skip_commit:
            try:
                git_utils.commit_changes(self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}")
            except Exception as e:            
                self.printer.print_in_terminal("git_init_required", style="red", source_dir=self.args.source_dir, error=str(e))
                return            
       
        edits = self.get_edits(content)        
        self.apply_edits(edits)        

        self.printer.print_in_terminal("files_merged_total", total=total)
        if not force_skip_git and not self.args.skip_commit:
            commit_result = git_utils.commit_changes(self.args.source_dir, f"{self.args.query}\nauto_coder_{file_name}")

            action_yml_file_manager = ActionYmlFileManager(self.args.source_dir)
            action_file_name = os.path.basename(self.args.file)
            add_updated_urls = []
            commit_result.changed_files
            for file in commit_result.changed_files:
                add_updated_urls.append(os.path.join(self.args.source_dir, file))

            self.args.add_updated_urls = add_updated_urls
            update_yaml_success = action_yml_file_manager.update_yaml_field(action_file_name, "add_updated_urls", add_updated_urls)
            if not update_yaml_success:                        
                self.printer.print_in_terminal("yaml_save_error", style="red", yaml_file=action_file_name)    
            
            if self.args.enable_active_context:
                active_context_manager = ActiveContextManager(self.llm, self.args.source_dir)
                task_id = active_context_manager.process_changes(self.args)
                self.printer.print_in_terminal("active_context_background_task", 
                                             style="blue",
                                             task_id=task_id)
                          
            git_utils.print_commit_info(commit_result=commit_result)
        else:
            # Print edits for review
            self.print_edits(edits)    
