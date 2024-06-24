from autocoder.common import (AutoCoderArgs,ExecuteSteps,
                              ExecuteStep,EnvInfo,
                              detect_env,chat_with_llm_step_by_step,SourceCode)
from autocoder.common.JupyterClient import JupyterNotebook
from autocoder.common.ShellClient import ShellClient
from autocoder.common.types import Mode,StepNum
from typing import Optional,Dict,Any,List
import byzerllm
from loguru import logger


class CodeAutoExecute:
    def __init__(self,llm,args,mode:Mode=Mode.SINGLE_ROUND) -> None:
        self.llm = llm
        self.args = args
        self.mode = mode

    @byzerllm.prompt(llm=lambda self: self.llm)
    def get_execute_steps(self,query:str,                          
                          context:Optional[str]=None,
                          source_code:Optional[str]=None,mode:Mode=Mode.SINGLE_ROUND)->ExecuteSteps:
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

        {%- if context %}
        现在请参考下面内容：

        {{ context }}
        {%- endif %}

        用户的问题是：{{ query }} 

        {{ mode }}       
        ''' 
        parameters= {
            "env_info":detect_env()
        }
        if mode == Mode.MULTI_ROUND:
            parameters["mode"] = "每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。"
        return parameters    

    @byzerllm.prompt(llm=lambda self: self.llm)
    def get_step_num(self,query:str,                          
                          context:Optional[str]=None,
                          source_code:Optional[str]=None)->StepNum:
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

        现在请参考下面内容：

        {{ context }}        

        用户的问题是：{{ query }}  

        根据问题，回答以下内容：
        1. 详细的执行步骤，每个步骤需要包含一个shell/python 代码块。
        2. 总共有多少步      
        '''  
        return {
            "env_info":detect_env()
        }  
    
    def execute_steps(self, steps: ExecuteSteps) -> str:
        jupyter_client = JupyterNotebook()
        shell_client = ShellClient(working_dir=steps.steps[0].cwd)
        
        try:
            output = ""
            for step in steps.steps:
                if step.lang and step.lang.lower() in ["python","py","python3"]:
                    output += f"Python Code:\n{step.code}\n"
                    output += "Output:\n"
                    result, error = jupyter_client.add_and_run(step.code)
                    output += result + "\n"
                    if error:
                        output += f"Error: {str(error)}\n"
                elif step.lang and step.lang.lower() in ["shell", "bash", "sh", "zsh", "ksh", "csh","powershell","cmd"]:  
                    output += f"Shell Command:\n{step.code}\n"
                    output += "Output:\n"                    
                    stdout, stderr = shell_client.add_and_run(step.code)
                    output += stdout + "\n"
                    if stderr:
                        output += f"Error: {stderr}\n"
                else:
                    output += f"Unknown step type: {step.lang}\n"
                
                output += "-" * 20 + "\n"
        except Exception as e:
            output += f"Error: {str(e)}\n"
        finally:    
            jupyter_client.close()
            shell_client.close()
        
        return output
    
    def run(self,query:str,context:str,source_code:str):
        
        if self.mode == Mode.SINGLE_ROUND:
            steps = self.get_execute_steps.run(query=query,context=context,source_code=source_code)

            print("\n\n=================================Execute Steps===========================================")
            print(steps)
            output = self.execute_steps(steps)

            print("\n\n=================================Execute Result===========================================")
            print(output)
            return
        if self.mode == Mode.MULTI_ROUND:
            step_num = self.get_step_num.run(query=query,context=context,source_code=source_code)
            
            final_v = ExecuteSteps(steps=[])            
            conversations = [{
                    "role":"user",
                    "content":step_num.content
                }] 
            print(f"=============================Collect AUTO STEPS===========================================",flush=True)
            print(f"{conversations[0]['role']}: {conversations[0]['content']}\n",flush=True)   

            (result,_) = chat_with_llm_step_by_step(self.llm,conversations=conversations,
                                                                response_class=ExecuteStep,
                                                                max_steps=step_num.step_num,                                                            
                                                                anti_quota_limit=self.args.anti_quota_limit)

            for item in result:            
                final_v.steps.append(item)                            
            
            # 执行步骤并保存结果
            if not final_v.steps:
                logger.error("No steps to execute, this may be caused by the model's response")
                return
            
            result = self.execute_steps(final_v)
            logger.info(result)            





    
        

