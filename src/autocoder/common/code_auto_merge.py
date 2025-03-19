import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs, git_utils
from typing import List, Union, Tuple
import pydantic
import byzerllm
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
from autocoder.common.code_modification_ranker import CodeModificationRanker
import hashlib
from autocoder.common import files as FileUtils
from autocoder.common.printer import Printer
from autocoder.common.auto_coder_lang import get_message
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.memory.active_context_manager import ActiveContextManager

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str

class CodeAutoMerge:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.printer = Printer()


    def parse_whole_text_v2(self,text: str) -> List[PathAndCode]:
        lines = text.split('\n')
        lines_len = len(lines)    
        start_marker_count = 0       
        inline_start_marker_count = 0 
        block = []
        path_and_code_list = []

        def guard(index):
            return index+1 < lines_len 

        def start_marker(line,index):
            return line.startswith('```') and guard(index) and lines[index+1].startswith('##File:')
        
        def inline_start_marker(line,index):
            return line.startswith('```') and line.strip() != '```'

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
                    path = block[0].split(":", 1)[1].strip()
                    content = '\n'.join(block[1:])                                
                    block = []
                    path_and_code_list.append(PathAndCode(path=path,content=content))       
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


    def parse_text(self, text: str) -> List[PathAndCode]:
        parsed_blocks = []

        lines = text.split("\n")
        file_path = None
        content_lines = []

        for line in lines:
            if line.startswith("##File:") or line.startswith("## File:"):
                if file_path is not None:
                    parsed_blocks.append(PathAndCode(path=file_path,content="\n".join(content_lines)))
                    content_lines = []

                file_path = line.split(":", 1)[1].strip()
            else:
                content_lines.append(line)

        if file_path is not None:
            parsed_blocks.append(PathAndCode(path=file_path,content="\n".join(content_lines)))

        return parsed_blocks
    
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

    def _merge_code_without_effect(self, content: str) -> MergeCodeWithoutEffect:
        """Merge code without any side effects like git operations or file writing.
        Returns a tuple of:
        - list of (file_path, new_content) tuples for successfully merged blocks
        - list of (file_path, content) tuples for failed to merge blocks"""
        codes = self.parse_whole_text_v2(content)
        file_content_mapping = {}
        failed_blocks = []
        
        for block in codes:
            file_path = block.path
            if not os.path.exists(file_path):
                file_content_mapping[file_path] = block.content
            else:
                if file_path not in file_content_mapping:
                    file_content_mapping[file_path] = FileUtils.read_file(file_path)
                if file_content_mapping[file_path] != block.content:
                    file_content_mapping[file_path] = block.content
                else:
                    failed_blocks.append((file_path, block.content))
                
        return MergeCodeWithoutEffect(
            success_blocks=[(path, content) for path, content in file_content_mapping.items()],
            failed_blocks=failed_blocks
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
                self.printer.print_in_terminal("git_init_required", 
                    source_dir=self.args.source_dir, error=str(e))
                return

        codes = self.parse_whole_text_v2(content)
        for block in codes:
            file_path = block.path
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w") as f:
                self.printer.print_in_terminal("upsert_file", file_path=file_path)
                total += 1
                f.write(block.content)

        self.printer.print_in_terminal("files_merged", total=total)
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
