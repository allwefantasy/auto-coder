from autocoder.common import AutoCoderArgs,ExecuteSteps,ExecuteStep,EnvInfo,detect_env,chat_with_llm_step_by_step
from autocoder.common.JupyterClient import JupyterNotebook
from autocoder.common.ShellClient import ShellClient
from autocoder.suffixproject import SuffixProject
from autocoder.index.index import IndexManager
from typing import Optional,Dict,Any,List
import byzerllm
import time
import os
import re

class ActionCopilot():
    def __init__(self,args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None) -> None:
        self.args = args
        self.llm = llm         
        self.env_info = detect_env()  
    
    @byzerllm.prompt(render="jinja2")
    def get_execute_steps(self,s:str,env_info:Dict[str,Any],source_code:Optional[str]=None)->str:
        '''        
        根据用户的问题，对问题进行拆解，然后生成执行步骤。

        环境信息如下:
        操作系统: {{ env_info.os_name }} {{ env_info.os_version }}  
        Python版本: {{ env_info.python_version }}
        {%- if env_info.conda_env %}
        Conda环境: {{ env_info.conda_env }}
        {%- endif %}
        {%- if env_info.virtualenv %}  
        虚拟环境: {{ env_info.virtualenv }}
        {%- endif %}
        {%- if env_info.has_bash %} 
        支持Bash
        {%- else %}
        不支持Bash
        {%- endif %}

        {%- if source_code %}
        下面是一系列文件以及它们的源码：
        {{ source_code }}
        {%- endif %}

        用户的问题是：{{ s }}

        每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。        
        '''               

    def execute_steps(self, steps: ExecuteSteps) -> str:
        jupyter_client = JupyterNotebook()
        shell_client = ShellClient()

        output = ""
        for step in steps.steps:
            if step.lang == "python":
                output += f"Python Code:\n{step.code}\n"
                output += "Output:\n"
                result, error = jupyter_client.add_and_run(step.code)
                output += result + "\n"
                if error:
                    output += f"Error: {str(error)}\n"
            elif step.lang == "shell":  
                output += f"Shell Command:\n{step.code}\n"
                output += "Output:\n"
                stdout, stderr = shell_client.add_and_run(step.code)
                output += stdout + "\n"
                if stderr:
                    output += f"Error: {stderr}\n"
            else:
                output += f"Unknown step type: {step.lang}\n"
            
            output += "-" * 20 + "\n"
        
        jupyter_client.close()
        shell_client.close()
        
        return output
    
    def get_suffix_from_project_type(self,project_type:str)->List[str]:
        # copilot/.py
        # handle situation like "copilot/.py", "copilot/.ts,py", or "copilot"
        # return ".py" or ".ts,.py" or ""       
        if project_type.startswith("copilot"):
            if len(project_type.split("/")) > 1:
                suffix_str = project_type.split("/")[1].strip()
                suffixs = suffix_str.split(",")
                result = []
                for suffix in suffixs:                    
                    if not suffix.startswith("."):
                        suffix = "." + suffix
                    result.append(suffix)
                
                return result            
        return []

    def run(self):
        args = self.args        
        if not args.project_type.startswith("copilot"):    
            return False  

        suffixs = self.get_suffix_from_project_type(args.project_type)        
        pp = SuffixProject(source_dir=args.source_dir, 
                            git_url=args.git_url, 
                            target_file=args.target_file, 
                            project_type=",".join(suffixs) or ".py",
                            file_filter=None                               
                            ) 
        pp.run()
                
        index_manager = IndexManager(llm=self.llm,sources=pp.sources,args=args)
        index_manager.build_index()
        target_files = index_manager.get_target_files_by_query(args.query)
        print(f"Target Files: {target_files.file_list}",flush=True)
        related_fiels = index_manager.get_related_files(target_files.file_list)        
        print(f"Related Files: {related_fiels.file_list}",flush=True)
        
        final_files = []

        for file in target_files.file_list + related_fiels.file_list:
            if file.file_path.strip().startswith("##"):
                final_files.append(file.file_path.strip()[2:])            

        source_code = "" 
        for file in pp.sources:
            if file.module_name in final_files:
                source_code += f"##File: {file.module_name}\n"
                source_code += f"{file.source_code}\n\n"                                     

        final_v = ExecuteSteps(steps=[])
        q = self.get_execute_steps(args.query,env_info = self.env_info.dict(),source_code=source_code) 
        conversations = [{
                "role":"user",
                "content":q
            }] 

        print(f"{conversations[0]['role']}: {conversations[0]['content']}\n",flush=True)   

        (result,_) = chat_with_llm_step_by_step(self.llm,conversations=conversations,
                                                            response_class=ExecuteStep,
                                                            max_steps=30,
                                                            anti_quota_limit=args.anti_quota_limit)

        for item in result:
            final_v.steps.append(item)                            
        
        # 执行步骤并保存结果
        result = self.execute_steps(final_v)
        
        # 将结果写入文件
        with open(args.target_file, "w") as f:
            f.write("=================CONVERSATION==================\n\n")
            for conversation in conversations:
                f.write(f"{conversation['role']}: {conversation['content']}\n")

            f.write("=================RESULT==================\n\n")
            f.write(result)

        return True