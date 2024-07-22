
import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs,git_utils
from typing import List
import pydantic
import byzerllm
from loguru import logger
import hashlib

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str

class CodeAutoMerge:
    def __init__(self, llm:byzerllm.ByzerLLM,args:AutoCoderArgs):
        self.llm = llm
        self.args = args  


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

    def merge_code(self, content: str,force_skip_git:bool=False):        
        total = 0
        
        file_content = open(self.args.file).read()
        md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()
        # get the file name 
        file_name = os.path.basename(self.args.file)
        
        if not force_skip_git:
            try:
                git_utils.commit_changes(self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}")
            except Exception as e:            
                logger.error(self.git_require_msg(source_dir=self.args.source_dir,error=str(e)))
                return            

        # codes =  code_utils.extract_code(content)
        # for (lang,code) in codes:            
        #     parsed_blocks = self.parse_text(code)

        #     for block in parsed_blocks:
        #         file_path = block.path
        #         os.makedirs(os.path.dirname(file_path), exist_ok=True)

        #         with open(file_path, "w") as f:
        #             logger.info(f"Upsert path: {file_path}")
        #             total += 1
        #             f.write(block.content)
        codes = self.parse_whole_text_v2(content)
        for block in codes:
            file_path = block.path
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, "w") as f:
                logger.info(f"Upsert path: {file_path}")
                total += 1
                f.write(block.content)

        logger.info(f"Merged {total} files into the project.")
        if not force_skip_git:
            commit_result = git_utils.commit_changes(self.args.source_dir, f"auto_coder_{file_name}_{md5}")
            git_utils.print_commit_info(commit_result=commit_result)
