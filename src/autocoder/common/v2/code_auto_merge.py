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


class CodeAutoMerge:
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

    def _merge_code(self, content: str, force_skip_git: bool = False):
        file_content = FileUtils.read_file(self.args.file)
        md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
        file_name = os.path.basename(self.args.file)

        if not force_skip_git and not self.args.skip_commit:
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

        merge_result = self._merge_code_without_effect(content)
        if not merge_result.success_blocks:
            self.printer.print_in_terminal("no_changes_to_merge")
            return

        # Apply changes
        for file_path, new_content in merge_result.success_blocks:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(new_content)

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
            self.print_merged_blocks(merge_result.success_blocks)
            
        self.printer.print_in_terminal("merge_success", 
                                     num_files=len(merge_result.success_blocks),
                                     num_changes=len(merge_result.success_blocks),
                                     total_blocks=len(merge_result.success_blocks) + len(merge_result.failed_blocks))

    def merge_code(self, generate_result: CodeGenerateResult, force_skip_git: bool = False):
        result = self.choose_best_choice(generate_result)
        self._merge_code(result.contents[0], force_skip_git)
        return result 