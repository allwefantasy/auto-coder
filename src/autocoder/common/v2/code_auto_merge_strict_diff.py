import os
import difflib
import diff_match_patch as dmp_module
from pathlib import Path
from typing import List, Dict, Tuple
import pydantic
import byzerllm
from autocoder.common import AutoCoderArgs, git_utils
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common.v2.code_auto_merge import CodeAutoMerge
from autocoder.common import files as FileUtils

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

class CodeAutoMergeStrictDiff(CodeAutoMerge):
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
                file_content_mapping[full_path] = FileUtils.read_file(full_path)
            
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
                self.printer.print_in_terminal("merge_failed", style="yellow", path=full_path, error=str(e))
                failed_blocks.append((full_path, content))
                
        return MergeCodeWithoutEffect(
            success_blocks=[(path, content) for path, content in file_content_mapping.items()],
            failed_blocks=failed_blocks
        )

    def print_diff_blocks(self, diff_blocks: List[PathAndCode]):
        """Print diff blocks for user review using rich library"""
        from rich.syntax import Syntax
        from rich.panel import Panel

        # Group blocks by file path
        file_blocks = {}
        for block in diff_blocks:
            if block.path not in file_blocks:
                file_blocks[block.path] = []
            file_blocks[block.path].append(block.content)

        # Generate formatted text for each file
        formatted_text = ""
        for path, contents in file_blocks.items():
            formatted_text += f"##File: {path}\n"
            for content in contents:
                formatted_text += content + "\n"
            formatted_text += "\n"

        # Print with rich panel
        self.printer.print_in_terminal("diff_blocks_title", style="bold green")
        self.printer.console.print(
            Panel(
                Syntax(formatted_text, "diff", theme="monokai"),
                title="Diff Blocks",
                border_style="green",
                expand=False
            )
        )

    def _merge_code(self, content: str, force_skip_git: bool = False):        
        total = 0
        
        file_content = FileUtils.read_file(self.args.file)
        md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        file_name = os.path.basename(self.args.file)
        
        if not force_skip_git and not self.args.skip_commit:
            try:
                git_utils.commit_changes(self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}")
            except Exception as e:            
                self.printer.print_in_terminal("git_init_required", style="red", source_dir=self.args.source_dir, error=str(e))
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
                            
        self.printer.print_in_terminal("files_merged_total", total=total)
        if not force_skip_git and not self.args.skip_commit:
            commit_result = git_utils.commit_changes(
                self.args.source_dir, f"{self.args.query}\nauto_coder_{file_name}"
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
                active_context_manager.process_changes(self.args)
            
            git_utils.print_commit_info(commit_result=commit_result)
        else:
            # Print diff blocks for review
            self.print_diff_blocks(diff_blocks) 