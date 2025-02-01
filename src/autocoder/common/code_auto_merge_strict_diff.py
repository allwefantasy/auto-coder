import os
import difflib
import diff_match_patch as dmp_module
from autocoder.common import AutoCoderArgs, git_utils
from typing import List,Tuple
import pydantic
import byzerllm
from loguru import logger
import hashlib
from pathlib import Path
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common.code_modification_ranker import CodeModificationRanker

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str

def safe_abs_path(res):
    "Gives an abs path, which safely returns a full (not 8.3) windows path"
    res = Path(res).resolve()
    return str(res)

def apply_hunk(content, hunk):
    before, after = hunk_to_before_after(hunk)
    
    # Get line numbers from @@ ... @@ markers
    line_info = hunk[0].split("@@")[1].strip()
    s_line_num = int(line_info.split(" ")[1].lstrip("+"))

    # Split content into lines
    content_lines = content.splitlines()
    
    # Merge changes using difflib
    merged_lines = list(difflib.ndiff(before.splitlines(), after.splitlines()))
    
    # Apply changes to original content
    j = 0
    content_out = content_lines[:s_line_num]
    for line in merged_lines:
        if line.startswith("- "):
            continue
        elif line.startswith("+ "):
            content_out.append(line[2:])
        elif line.startswith("  "):
            if j < len(content_lines):
                content_out.append(content_lines[s_line_num+j])
            j += 1
    
    content_out.extend(content_lines[s_line_num+j:])

    return "\n".join(content_out)


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


class CodeAutoMergeStrictDiff:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args


    def parse_diff_block(self,text: str) -> List[PathAndCode]:
        lines = text.split('\n')
        lines_len = len(lines)    
        start_marker_count = 0       
        inline_start_marker_count = 0 
        block = []
        path_and_code_list = []

        def guard(index):
            return index+1 < lines_len 

        def start_marker(line,index):
            return line.startswith('```diff') and guard(index)
        
        def inline_start_marker(line,index):
            return line.startswith('```') and not line.startswith('```diff') and line.strip() != '```'

        def end_marker(line,index):
            return line.startswith('```') and line.strip() == '```'
        

        for (index,line) in enumerate(lines):
            if start_marker(line,index) and start_marker_count == 0:
                start_marker_count += 1        
            elif (start_marker(line,index) or inline_start_marker(line,index)) and start_marker_count > 0:
                inline_start_marker_count += 1     
                block.append(line)    
            elif end_marker(line,index) and start_marker_count == 1 and inline_start_marker_count == 0:
                start_marker_count -= 1            
                if block:
                    # ori_path = block[0][4:0].strip()                       
                    new_path = block[1][4:].strip()                    
                    content = '\n'.join(block)                                
                    block = []
                    path_and_code_list.append(PathAndCode(path=new_path,content=content))       
            elif end_marker(line,index) and inline_start_marker_count > 0:
                inline_start_marker_count -= 1   
                block.append(line)                 
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

        ranker = CodeModificationRanker(self.llm, self.args)
        ranked_result = ranker.rank_modifications(generate_result)
        # Filter out contents with failed blocks
        for content,conversations in zip(ranked_result.contents,ranked_result.conversations):
            merge_result = self._merge_code_without_effect(content)
            if not merge_result.failed_blocks:
                return CodeGenerateResult(contents=[content], conversations=[conversations])
        # If all have failed blocks, return the first one
        return CodeGenerateResult(contents=[ranked_result.contents[0]], conversations=[ranked_result.conversations[0]])
    

    def abs_root_path(self, path):
        if path.startswith(self.args.source_dir):
            return safe_abs_path(Path(path))
        res = Path(self.args.source_dir) / path
        return safe_abs_path(res)            

    def _merge_code_without_effect(self, content: str) -> MergeCodeWithoutEffect:
        """Merge code without any side effects like git operations or file writing.
        Returns a tuple of:
        - list of (file_path, new_content) tuples for successfully merged blocks
        - list of (file_path, content) tuples for failed to merge blocks"""
        diff_blocks = self.parse_diff_block(content)
        file_content_mapping = {}
        failed_blocks = []
        
        for block in diff_blocks:
            path = block.path
            content = block.content
            full_path = self.abs_root_path(path)
            
            if not os.path.exists(full_path):
                file_content_mapping[full_path] = content
                continue
                
            if full_path not in file_content_mapping:
                with open(full_path, "r") as f:
                    file_content_mapping[full_path] = f.read()
            
            try:
                import patch
                patch_obj = patch.fromstring(content.encode('utf-8'))
                root_path = None
                if not path.startswith(self.args.source_dir):
                    root_path = self.args.source_dir

                # Create a copy of the content to apply patch
                temp_content = file_content_mapping[full_path]
                success = patch_obj.apply(root=root_path, content=temp_content)
                if success:
                    file_content_mapping[full_path] = temp_content
                else:
                    failed_blocks.append((full_path, content))
            except Exception as e:
                logger.warning(f"Failed to apply patch to {full_path}: {str(e)}")
                failed_blocks.append((full_path, content))
                
        return MergeCodeWithoutEffect(
            success_blocks=[(path, content) for path, content in file_content_mapping.items()],
            failed_blocks=failed_blocks
        )

    def _merge_code(self, content: str, force_skip_git: bool = False):        
        total = 0
        
        file_content = open(self.args.file).read()
        md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        # get the file name 
        file_name = os.path.basename(self.args.file)
        
        if not force_skip_git:
            try:
                git_utils.commit_changes(self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}")
            except Exception as e:            
                logger.error(self.git_require_msg(source_dir=self.args.source_dir, error=str(e)))
                return            
       
        diff_blocks = self.parse_diff_block(content)
        for diff_blocks in diff_blocks:
            path = diff_blocks.path
            content = diff_blocks.content          

            import patch
            patch_obj = patch.fromstring(content.encode('utf-8'))
            root_path = None
            if not path.startswith(self.args.source_dir):
                root_path = self.args.source_dir

            success = patch_obj.apply(root=root_path)
            if not success:
                raise Exception("Error applying diff to file: " + path)
                            
        logger.info(f"Merged {total} files into the project.")
        if not force_skip_git:
            commit_result = git_utils.commit_changes(self.args.source_dir, f"auto_coder_{file_name}_{md5}")
            git_utils.print_commit_info(commit_result=commit_result)

    @byzerllm.prompt(render="jinja2")
    def git_require_msg(self, source_dir: str, error: str) -> str:
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
