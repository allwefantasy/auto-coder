from autocoder.common import AutoCoderArgs,ExecuteSteps
from autocoder.suffixproject import SuffixProject
from typing import Optional
import byzerllm
import os
import re

class ActionCopilot():
    def __init__(self,args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None) -> None:
        self.args = args
        self.llm = llm  
    
    @byzerllm.prompt(lambda self:self.llm,render="jinja")
    def get_execute_steps(self,s:str)->ExecuteSteps:
        '''
        根据用户的问题，对问题进行拆解，然后生成执行步骤。

        用户的问题是：{{ s }}

        每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。
        '''

    @byzerllm.prompt(render="jinja")
    def get_all_file_symbols(self,path:str,code:str)->str: 
        '''
        下列是文件 {{ path }} 的源码：
        
        {{ code }}
        
        从上述内容中获取文件中的符号。需要获取的符号类型包括：函数、类、变量、模块、包
        按如下格式返回：

        符号类型: 符号名称        
        '''             


    def run(self):
        args = self.args        
        if not args.project_type.startswith("copilot"):    
            return False                                            
        pp = SuffixProject(source_dir=args.source_dir, 
                            git_url=args.git_url, 
                            target_file=args.target_file, 
                            project_type=".py",
                            file_filter=None                               
                            ) 
        pp.run()            
        # for source in pp.sources:
        #     file_symbols = self.get_all_file_symbols(source.module_name,source.source_code)
        #     print(file_symbols,flush=True)
        
        final_v = ExecuteSteps([])
        q = self.get_execute_steps(args.query) 
        conversations = [{
                "role":"user",
                "content":q
            }]
               
        t = self.llm.chat_oai(conversations=conversations,response_class=ExecuteSteps)
       
        while t[0].value and t[0].value.steps:
            conversations.append({
                "role":"assistant",
                "content":t[0].response.output
            })
            conversations.append({
                "role":"user",
                "content":"继续"
            })
            print("====================================",flush=True)
            print(t[0].value.steps,flush=True)
            final_v.steps += t[0].value.steps
            t = self.llm.chat_oai(conversations=conversations,response_class=ExecuteSteps)                                

        return True
                     
