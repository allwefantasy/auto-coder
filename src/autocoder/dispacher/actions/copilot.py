from autocoder.common import AutoCoderArgs,ExecuteSteps,ExecuteStep,EnvInfo,detect_env,chat_with_llm_step_by_step
from autocoder.common.JupyterClient import JupyterNotebook
from autocoder.common.ShellClient import ShellClient
from autocoder.suffixproject import SuffixProject
from autocoder.common.search import Search,SearchEngine
from autocoder.index.index import build_index_and_filter_files
from typing import Optional,Dict,Any,List
import byzerllm
from enum import Enum
import pydantic

class UserIntent(Enum):
    CREATE_NEW_PROJECT = "CREATE_NEW_PROJECT"
    OPTIMIZE_EXISTING_PROJECT = "OPTIMIZE_EXISTING_PROJECT"
    UNKNOWN = "UNKNOWN"


class RUserIntent(pydantic.BaseModel):
    user_intent:UserIntent= pydantic.Field(UserIntent.UNKNOWN,description="用户意图,默认为UNKNOWN")

class StepNum(pydantic.BaseModel):
    step_num:int= pydantic.Field(1,description="总共步骤数")

class ActionCopilot():
    def __init__(self,args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None) -> None:
        self.args = args
        self.llm = llm         
        self.env_info = detect_env()  
        self.user_intent = UserIntent.UNKNOWN
    
    @byzerllm.prompt(render="jinja2")
    def get_execute_steps(self,s:str,
                          env_info:Dict[str,Any],
                          context:Optional[str]=None,
                          source_code:Optional[str]=None)->str:
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

        用户的问题是：{{ s }}

        每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。        
        ''' 

    @byzerllm.prompt(render="jinja2")
    def get_step_num(self,s:str,
                          env_info:Dict[str,Any],
                          context:Optional[str]=None,
                          source_code:Optional[str]=None)->str:
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

        用户的问题是：{{ s }}  

        根据问题，回答以下内容：
        1. 详细的执行步骤，每个步骤需要包含一个shell/python 代码块。
        2. 总共有多少步      
        '''    
       
    @byzerllm.prompt(render="jinja2")
    def get_execute_steps_for_create_project(self,s:str,context:str,source_code:str)->str:
        '''        
        你熟悉各种编程语言以及相关框架对应的项目结构。现在，你需要
        根据用户的问题，根据提供的信息，对问题进行拆解，然后生成执行步骤，当执行完所有步骤，最终帮生成一个符合对应编程语言规范以及相关框架的项目结构。
        整个过程只能使用 python/shell。

        {%- if source_code %}
        下面是一系列文件以及它们的源码：
        {{ source_code }}
        {%- endif %}        
        
        现在请参考下面内容：

        {{ context }}        
        
        每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。        
        '''                          

    def execute_steps(self, steps: ExecuteSteps) -> str:
        jupyter_client = JupyterNotebook()
        shell_client = ShellClient(working_dir=steps.steps[0].cwd)
        
        try:
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
        except Exception as e:
            output += f"Error: {str(e)}\n"
        finally:    
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

        if args.query and self.llm:
            t = self.llm.chat_oai(conversations=[
              {
                "role":"user",
                "content":args.query
              }
            ],response_class=RUserIntent) 
            
            if t[0].value:
                self.user_intent = t[0].value.user_intent         



        suffixs = self.get_suffix_from_project_type(args.project_type)  
        args.project_type = ",".join(suffixs) or ".py"      
        pp = SuffixProject(args=args,
                           llm = self.llm,file_filter=None) 
        pp.run()
        
        print(f"Intent: {self.user_intent}",flush=True)        
        
        source_code = ""
        search_context = ""
        step_num = -1
        first_response = ""

        if args.search_engine and args.search_engine_token:
            if args.search_engine == "bing":
                search_engine = SearchEngine.BING
            else:
                search_engine = SearchEngine.GOOGLE

            searcher=Search(llm=self.llm,search_engine=search_engine,subscription_key=args.search_engine_token)
            search_context = searcher.answer_with_the_most_related_context(args.query)
        
        first_response = search_context
        if self.llm:
            print("try to get the total steps...",flush=True)
            q1 = self.get_step_num(args.query,env_info = self.env_info.dict(),
                                    source_code=source_code,
                                    context=search_context)
            t = self.llm.chat_oai(conversations=[{
                "role":"user",
                "content":q1
            }])                
            first_response = t[0].output
            
            t = self.llm.chat_oai(conversations=[{
                "role":"user",
                "content":first_response
            }],response_class=StepNum,enable_default_sys_message=True)
            
            if t[0].value:
                step_num = t[0].value.step_num
                print(f"total steps to finish the user's question: {step_num}",flush=True)
            else:
                print(f"fail to get the step num for the user's quesion: {t[0]}",flush=True)    

        if self.user_intent == UserIntent.CREATE_NEW_PROJECT: 
            source_code = build_index_and_filter_files(llm=self.llm,args=args,sources=pp.sources)                                                                        
            q = self.get_execute_steps_for_create_project(s=args.query,context=first_response,source_code=source_code)
        else:                                       
            source_code = build_index_and_filter_files(llm=self.llm,args=args,sources=pp.sources) 
            q = self.get_execute_steps(args.query,env_info = self.env_info.dict(),
                                       context=first_response,
                                       source_code=source_code)  

        if self.llm is None:
            print("model is not specified and we will generate prompt to the target file",flush=True)
            with open(args.target_file, "w") as f:
                f.write(q)
            return True                  

        final_v = ExecuteSteps(steps=[])            
        conversations = [{
                "role":"user",
                "content":q
            }] 
        print(f"=============================Collect AUTO STEPS===========================================",flush=True)
        print(f"{conversations[0]['role']}: {conversations[0]['content']}\n",flush=True)   

        (result,_) = chat_with_llm_step_by_step(self.llm,conversations=conversations,
                                                            response_class=ExecuteStep,
                                                            max_steps=step_num,                                                            
                                                            anti_quota_limit=args.anti_quota_limit)

        for item in result:            
            final_v.steps.append(item)                            
        
        # 执行步骤并保存结果
        result = self.execute_steps(final_v)
        print(result,flush=True)
        
        # 将结果写入文件
        with open(args.target_file, "w") as f:
            f.write("=================CONVERSATION==================\n\n")
            for conversation in conversations:
                f.write(f"{conversation['role']}: {conversation['content']}\n")

            f.write("=================RESULT==================\n\n")
            f.write(result)

        return True