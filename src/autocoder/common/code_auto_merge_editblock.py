import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs, git_utils
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common.text import TextSimilarity
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
import pydantic
import byzerllm

import hashlib
import subprocess
import tempfile
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json
from typing import Union, List, Tuple
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common.code_modification_ranker import CodeModificationRanker
from autocoder.common import files as FileUtils
from autocoder.common.printer import Printer

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str


class CodeAutoMergeEditBlock:
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
        fence_0: str = "```",
        fence_1: str = "```",
    ):
        self.llm = llm
        self.args = args
        self.fence_0 = fence_0
        self.fence_1 = fence_1
        self.printer = Printer()
    
    def parse_whole_text(self, text: str) -> List[PathAndCode]:
        '''
        从文本中抽取如下格式代码(two_line_mode)：

        ```python
        ##File: /project/path/src/autocoder/index/index.py
        <<<<<<< SEARCH
        =======
        >>>>>>> REPLACE
        ```

        或者 (one_line_mode)

        ```python:/project/path/src/autocoder/index/index.py
        <<<<<<< SEARCH
        =======
        >>>>>>> REPLACE
        ```

        '''
        HEAD = "<<<<<<< SEARCH"
        DIVIDER = "======="
        UPDATED = ">>>>>>> REPLACE"
        lines = text.split("\n")
        lines_len = len(lines)
        start_marker_count = 0
        block = []
        path_and_code_list = []
        # two_line_mode or one_line_mode
        current_editblock_mode = "two_line_mode"
        current_editblock_path = None

        def guard(index):
            return index + 1 < lines_len

        def start_marker(line, index):
            nonlocal current_editblock_mode
            nonlocal current_editblock_path
            if (
                line.startswith(self.fence_0)
                and guard(index)
                and ":" in line
                and lines[index + 1].startswith(HEAD)
            ):

                current_editblock_mode = "one_line_mode"
                current_editblock_path = line.split(":", 1)[1].strip()
                return True

            if (
                line.startswith(self.fence_0)
                and guard(index)
                and lines[index + 1].startswith("##File:")
            ):
                current_editblock_mode = "two_line_mode"
                current_editblock_path = None
                return True

            return False

        def end_marker(line, index):
            return line.startswith(self.fence_1) and UPDATED in lines[index - 1]

        for index, line in enumerate(lines):
            if start_marker(line, index) and start_marker_count == 0:
                start_marker_count += 1
            elif end_marker(line, index) and start_marker_count == 1:
                start_marker_count -= 1
                if block:
                    if current_editblock_mode == "two_line_mode":
                        path = block[0].split(":", 1)[1].strip()
                        content = "\n".join(block[1:])
                    else:
                        path = current_editblock_path
                        content = "\n".join(block)
                    block = []
                    path_and_code_list.append(
                        PathAndCode(path=path, content=content))
            elif start_marker_count > 0:
                block.append(line)

        return path_and_code_list

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

    @byzerllm.prompt()
    def git_require_msg(self, source_dir: str, error: str) -> str:
        """
        auto_merge only works for git repositories.

        Try to use git init in the source directory.

        ```shell
        cd {{ source_dir }}
        git init .
        ```

        Then try to run auto-coder again.
        Error: {{ error }}
        """

    def get_edits(self, content: str):
        edits = self.parse_whole_text(content)
        HEAD = "<<<<<<< SEARCH"
        DIVIDER = "======="
        UPDATED = ">>>>>>> REPLACE"
        result = []
        for edit in edits:
            heads = []
            updates = []
            c = edit.content
            in_head = False
            in_updated = False
            for line in c.splitlines():
                if line.strip() == HEAD:
                    in_head = True
                    continue
                if line.strip() == DIVIDER:
                    in_head = False
                    in_updated = True
                    continue
                if line.strip() == UPDATED:
                    in_head = False
                    in_updated = False
                    continue
                if in_head:
                    heads.append(line)
                if in_updated:
                    updates.append(line)
            result.append((edit.path, "\n".join(heads), "\n".join(updates)))
        return result        

    def _merge_code_without_effect(self, content: str) -> MergeCodeWithoutEffect:
        """Merge code without any side effects like git operations, linting or file writing.
        Returns a tuple of:
        - list of (file_path, new_content) tuples for successfully merged blocks
        - list of (file_path, head, update) tuples for failed to merge blocks"""
        codes = self.get_edits(content)
        file_content_mapping = {}
        failed_blocks = []

        for block in codes:
            file_path, head, update = block
            if not os.path.exists(file_path):
                file_content_mapping[file_path] = update
            else:
                if file_path not in file_content_mapping:
                    file_content_mapping[file_path] = FileUtils.read_file(file_path)
                existing_content = file_content_mapping[file_path]

                # First try exact match
                new_content = (
                    existing_content.replace(head, update, 1)
                    if head
                    else existing_content + "\n" + update
                )

                # If exact match fails, try similarity match
                if new_content == existing_content and head:
                    similarity, best_window = TextSimilarity(
                        head, existing_content
                    ).get_best_matching_window()
                    if similarity > self.args.editblock_similarity:
                        new_content = existing_content.replace(
                            best_window, update, 1
                        )

                if new_content != existing_content:
                    file_content_mapping[file_path] = new_content
                else:
                    failed_blocks.append((file_path, head, update))

        return MergeCodeWithoutEffect(
            success_blocks=[(path, content)
                            for path, content in file_content_mapping.items()],
            failed_blocks=failed_blocks
        )
    

    def _merge_code(self, content: str, force_skip_git: bool = False):
        file_content = FileUtils.read_file(self.args.file)
        md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
        file_name = os.path.basename(self.args.file)

        codes = self.get_edits(content)
        changes_to_make = []
        changes_made = False
        unmerged_blocks = []
        merged_blocks = []

        # First, check if there are any changes to be made
        file_content_mapping = {}
        for block in codes:
            file_path, head, update = block
            if not os.path.exists(file_path):
                changes_to_make.append((file_path, None, update))
                file_content_mapping[file_path] = update
                merged_blocks.append((file_path, "", update, 1))
                changes_made = True
            else:
                if file_path not in file_content_mapping:
                    file_content_mapping[file_path] = FileUtils.read_file(file_path)
                existing_content = file_content_mapping[file_path]
                new_content = (
                    existing_content.replace(head, update, 1)
                    if head
                    else existing_content + "\n" + update
                )
                if new_content != existing_content:
                    changes_to_make.append(
                        (file_path, existing_content, new_content))
                    file_content_mapping[file_path] = new_content
                    merged_blocks.append((file_path, head, update, 1))
                    changes_made = True
                else:
                    # If the SEARCH BLOCK is not found exactly, then try to use
                    # the similarity ratio to find the best matching block
                    similarity, best_window = TextSimilarity(
                        head, existing_content
                    ).get_best_matching_window()
                    if similarity > self.args.editblock_similarity:
                        new_content = existing_content.replace(
                            best_window, update, 1)
                        if new_content != existing_content:
                            changes_to_make.append(
                                (file_path, existing_content, new_content)
                            )
                            file_content_mapping[file_path] = new_content
                            merged_blocks.append(
                                (file_path, head, update, similarity))
                            changes_made = True
                    else:
                        unmerged_blocks.append(
                            (file_path, head, update, similarity))

        if unmerged_blocks:                        
            self.printer.print_in_terminal("unmerged_blocks_warning", num_blocks=len(unmerged_blocks))
            self._print_unmerged_blocks(unmerged_blocks)
            return
        
        if changes_made and not force_skip_git and not self.args.skip_commit:
            try:
                git_utils.commit_changes(
                    self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}"
                )
            except Exception as e:
                self.printer.print_str_in_terminal(
                    self.git_require_msg(source_dir=self.args.source_dir, error=str(e)),
                    style="red"
                )
                return
            
        # Now, apply the changes
        for file_path, new_content in file_content_mapping.items():
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(new_content)

        if changes_made:
            if not force_skip_git and not self.args.skip_commit:
                try:
                    commit_result = git_utils.commit_changes(
                        self.args.source_dir,
                        f"{self.args.query}\nauto_coder_{file_name}",
                    )
                    
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
                except Exception as e:
                    self.printer.print_str_in_terminal(
                        self.git_require_msg(source_dir=self.args.source_dir, error=str(e)),
                        style="red"
                    )
            else:
                self.print_merged_blocks(merged_blocks)
            
            self.printer.print_in_terminal("merge_success", 
                                         num_files=len(file_content_mapping.keys()),
                                         num_changes=len(changes_to_make),
                                         total_blocks=len(codes))
            
        else:
            self.printer.print_in_terminal("no_changes_made")

    def _print_unmerged_blocks(self, unmerged_blocks: List[tuple]):
        self.printer.print_in_terminal("unmerged_blocks_title", style="bold red")
        for file_path, head, update, similarity in unmerged_blocks:
            self.printer.print_str_in_terminal(
                f"\n{self.printer.get_message_from_key_with_format('unmerged_file_path',file_path=file_path)}",
                style="bold blue"
            )
            self.printer.print_str_in_terminal(
                f"\n{self.printer.get_message_from_key_with_format('unmerged_search_block',similarity=similarity)}",
                style="bold green"
            )
            syntax = Syntax(head, "python", theme="monokai", line_numbers=True)
            self.printer.console.print(Panel(syntax, expand=False))
            self.printer.print_in_terminal("unmerged_replace_block", style="bold yellow")
            syntax = Syntax(update, "python", theme="monokai", line_numbers=True)
            self.printer.console.print(Panel(syntax, expand=False))
        self.printer.print_in_terminal("unmerged_blocks_total", num_blocks=len(unmerged_blocks), style="bold red")


    def print_merged_blocks(self, merged_blocks: List[tuple]):
        """Print search/replace blocks for user review using rich library"""
        from rich.syntax import Syntax
        from rich.panel import Panel

        # Group blocks by file path
        file_blocks = {}
        for file_path, head, update, similarity in merged_blocks:
            if file_path not in file_blocks:
                file_blocks[file_path] = []
            file_blocks[file_path].append((head, update, similarity))

        # Generate formatted text for each file
        formatted_text = ""
        for file_path, blocks in file_blocks.items():
            formatted_text += f"##File: {file_path}\n"
            for head, update, similarity in blocks:
                formatted_text += "<<<<<<< SEARCH\n"
                formatted_text += head + "\n"
                formatted_text += "=======\n"
                formatted_text += update + "\n"
                formatted_text += ">>>>>>> REPLACE\n"
            formatted_text += "\n"

        # Print with rich panel
        self.printer.print_in_terminal("merged_blocks_title", style="bold green")
        self.printer.console.print(
            Panel(
                Syntax(formatted_text, "diff", theme="monokai"),
                title="Merged Changes",
                border_style="green",
                expand=False
            )
        )
