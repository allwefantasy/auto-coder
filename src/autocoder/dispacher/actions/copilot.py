from autocoder.common import AutoCoderArgs,ExecuteSteps,ExecuteStep,EnvInfo,detect_env
from autocoder.common.JupyterClient import JupyterNotebook
from autocoder.common.ShellClient import ShellClient
from autocoder.suffixproject import SuffixProject
from typing import Optional,Dict,Any,List
import byzerllm
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

    @byzerllm.prompt(lambda self:self.llm,render="jinja2")
    def get_all_file_symbols(self,path:str,code:str)->str: 
        '''
        下列是文件 {{ path }} 的源码：
        
        {{ code }}
        
        从上述内容中获取文件中的符号。需要获取的符号类型包括：函数、类、变量、模块、包
        按如下格式返回：

        符号类型: 符号名称        
        '''             

    def execute_steps(self, steps: ExecuteSteps) -> str:
        jupyter_client = JupyterNotebook()
        shell_client = ShellClient()
        print(steps, flush=True)
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
        
        source_code = None
        if suffixs:
            source_code = pp.output()

        final_v = ExecuteSteps(steps=[])
        q = self.get_execute_steps(args.query,env_info = self.env_info.dict(),source_code=source_code) 
        conversations = [{
                "role":"user",
                "content":q
            }] 

        print(f"{conversations[0]['role']}: {conversations[0]['content']}\n",flush=True)   
               
        t = self.llm.chat_oai(conversations=conversations,response_class=ExecuteStep)        
        max_steps = 30
        total_steps = max_steps
        current_step = 0
        
        if not t[0].value:
            total_steps = t[0].value.total_steps
            if total_steps == 1:
                current_step = 1

        while current_step < total_steps and max_steps>0 and t[0].value:                             
            total_steps = t[0].value.total_steps                
            final_v.steps.append(t[0].value)
            conversations.append({
                "role":"assistant",
                "content":t[0].response.output
            })
            print(f"{conversations[-1]['role']}: {conversations[-1]['content']}\n",flush=True)

            conversations.append({
                "role":"user",
                "content":"继续"
            })            
            print(f"{conversations[-1]['role']}: {conversations[-1]['content']}\n",flush=True)

            t = self.llm.chat_oai(conversations=conversations,response_class=ExecuteStep)
            max_steps -= 1  
            current_step += 1                              
        
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