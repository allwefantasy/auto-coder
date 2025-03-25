import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs, git_utils, SourceCodeList, SourceCode
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common.text import TextSimilarity
from autocoder.memory.active_context_manager import ActiveContextManager
import pydantic
import byzerllm

import hashlib
import subprocess
import tempfile
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json
from typing import Union, List, Tuple, Dict
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common.code_modification_ranker import CodeModificationRanker
from autocoder.common import files as FileUtils
from autocoder.common.printer import Printer
from autocoder.shadows.shadow_manager import ShadowManager

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str


class CodeAutoMergeDiff:
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
    ):
        self.llm = llm
        self.args = args
        self.printer = Printer()        

    def run_pylint(self, code: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            result = subprocess.run(
                [
                    "pylint",
                    "--disable=all",
                    "--enable=E0001,W0311,W0312",
                    temp_file_path,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            os.unlink(temp_file_path)
            if result.returncode != 0:
                error_message = result.stdout.strip() or result.stderr.strip()
                self.printer.print_in_terminal("pylint_check_failed", error_message=error_message)
                return False, error_message
            return True, ""
        except subprocess.CalledProcessError as e:
            error_message = f"Error running pylint: {str(e)}"
            self.printer.print_in_terminal("pylint_error", error_message=error_message)
            os.unlink(temp_file_path)
            return False, error_message

    def get_edits(self, content: str):
        edits = self.parse_whole_text(content)
        result = []
        for edit in edits:
            result.append((edit.path, edit.content))
        return result        

    def get_source_code_list_from_shadow_files(self, shadow_files: Dict[str, str]) -> SourceCodeList:
        """
        将影子文件转换为SourceCodeList对象
        
        参数:
            shadow_files (Dict[str, str]): 映射 {影子文件路径: 内容}
            
        返回:
            SourceCodeList: 包含原始路径和内容的SourceCodeList对象
        """
        sources = []
        shadow_manager = ShadowManager(self.args.source_dir,event_file_id=self.args.event_file)
        for shadow_path, content in shadow_files.items():
            # 将影子路径转换回原始文件路径
            file_path = shadow_manager.from_shadow_path(shadow_path)            
            # 创建SourceCode对象并添加到sources列表
            source = SourceCode(module_name=file_path, source_code=content)
            sources.append(source)
        
        return SourceCodeList(sources)

    def _merge_code_without_effect(self, content: str) -> MergeCodeWithoutEffect:
        """Merge code without any side effects like git operations, linting or file writing.
        Returns a tuple of:
        - list of (file_path, new_content) tuples for successfully merged blocks
        - list of (file_path, hunk) tuples for failed to merge blocks"""
        edits = self.get_edits(content)
        file_content_mapping = {}
        failed_blocks = []

        for path, hunk in edits:
            if not os.path.exists(path):
                file_content_mapping[path] = hunk
            else:
                if path not in file_content_mapping:
                    file_content_mapping[path] = FileUtils.read_file(path)
                existing_content = file_content_mapping[path]

                try:
                    new_content = self.apply_hunk(existing_content, hunk)
                    if new_content:
                        file_content_mapping[path] = new_content
                    else:
                        failed_blocks.append((path, hunk))
                except Exception as e:
                    failed_blocks.append((path, hunk))

        return MergeCodeWithoutEffect(
            success_blocks=[(path, content)
                            for path, content in file_content_mapping.items()],
            failed_blocks=failed_blocks
        )
    
    def apply_hunk(self, content: str, hunk: str) -> str:
        """Apply a unified diff hunk to content"""
        import difflib
        import re
        
        # Split hunk into lines
        lines = hunk.splitlines()
        
        # Extract file paths
        old_path = lines[0].replace("--- ", "").strip()
        new_path = lines[1].replace("+++ ", "").strip()
        
        # Skip the file paths and the @@ line
        lines = lines[2:]
        
        # Find the @@ line
        for i, line in enumerate(lines):
            if line.startswith("@@ "):
                lines = lines[i+1:]
                break
                
        # Create a patch
        patch = "\n".join(lines)
        
        # Apply the patch
        try:
            result = difflib.unified_diff(content.splitlines(keepends=True),
                                        patch.splitlines(keepends=True),
                                        fromfile=old_path,
                                        tofile=new_path)
            # Convert back to string
            return "".join(result)
        except Exception as e:
            return None

    def _merge_code(self, content: str, force_skip_git: bool = False):
        file_content = FileUtils.read_file(self.args.file)
        md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
        file_name = os.path.basename(self.args.file)

        edits = self.get_edits(content)
        changes_to_make = []
        changes_made = False
        unmerged_blocks = []
        merged_blocks = []

        # First, check if there are any changes to be made
        file_content_mapping = {}
        for path, hunk in edits:
            if not os.path.exists(path):
                changes_to_make.append((path, None, hunk))
                file_content_mapping[path] = hunk
                merged_blocks.append((path, "", hunk, 1))
                changes_made = True
            else:
                if path not in file_content_mapping:
                    file_content_mapping[path] = FileUtils.read_file(path)
                existing_content = file_content_mapping[path]
                new_content = self.apply_hunk(existing_content, hunk)
                if new_content:
                    changes_to_make.append(
                        (path, existing_content, new_content))
                    file_content_mapping[path] = new_content
                    merged_blocks.append((path, hunk, new_content, 1))
                    changes_made = True
                else:
                    unmerged_blocks.append(
                        (path, hunk, existing_content, 0))

        if unmerged_blocks:
            if self.args.request_id and not self.args.skip_events:
                # collect unmerged blocks
                event_data = []
                for file_path, head, update, similarity in unmerged_blocks:
                    event_data.append(
                        {
                            "file_path": file_path,
                            "head": head,
                            "update": update,
                            "similarity": similarity,
                        }
                    )
                return
            
            self.printer.print_in_terminal("unmerged_blocks_warning", num_blocks=len(unmerged_blocks))
            self._print_unmerged_blocks(unmerged_blocks)
            return

        # lint check
        for file_path, new_content in file_content_mapping.items():
            if file_path.endswith(".py"):
                pylint_passed, error_message = self.run_pylint(new_content)
                if not pylint_passed:
                    self.printer.print_in_terminal("pylint_file_check_failed", 
                                                  file_path=file_path, 
                                                  error_message=error_message)

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

        if self.args.request_id and not self.args.skip_events:
            # collect modified files
            event_data = []
            for code in merged_blocks:
                file_path, head, update, similarity = code
                event_data.append(
                    {
                        "file_path": file_path,
                        "head": head,
                        "update": update,
                        "similarity": similarity,
                    }
                )

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
                                         total_blocks=len(edits))
            
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