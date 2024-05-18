from typing import List,Dict,Tuple
from autocoder.common.types import Mode
from autocoder.common import AutoCoderArgs
import byzerllm


class CodeAutoGenerate:
    def __init__(self,llm:byzerllm.ByzerLLM,args:AutoCoderArgs) -> None:
        self.llm = llm
        self.args = args       


    @byzerllm.prompt(llm = lambda self: self.llm)
    def auto_implement_function(self,instruction:str, content:str)->str:
        '''
        下面是一些文件路径以及每个文件对应的源码：

        {{ content }}

        请参考上面的内容，重新实现所有文件下方法体标记了如下内容的方法：

        ```python
        raise NotImplementedError("This function should be implemented by the model.")
        ```
        
        {{ instruction }}
            
        '''          

    @byzerllm.prompt(llm = lambda self: self.llm)
    def multi_round_instruction(self,instruction:str, content:str)->str:
        '''
        {%- if content %}
        下面是一些文件路径以及每个文件对应的源码：

        {{ content }}  
        {%- endif %}


        下面是用户的需求：
        
        {{ instruction }}

        你生成的代码要符合这个格式：
        
        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```    

        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```

        其中，{lang}是代码的语言，{CODE}是代码的内容, {FILE_PATH} 是文件的路径，他们都在代码块中，请严格按上面的格式进行内容生成。                
        每次生成一个文件的代码，然后询问我是否继续，当我回复继续，继续生成下一个文件的代码。当没有后续任务时，请回复 "__完成__" 或者 "__EOF__"。
        请确保每份代码的完整性，而不要只生成修改部分。
        '''

    @byzerllm.prompt(llm = lambda self: self.llm)
    def single_round_instruction(self,instruction:str, content:str)->str:
        '''
        {%- if content %}
        下面是一些文件路径以及每个文件对应的源码：

        {{ content }}  
        {%- endif %}


        下面是用户的需求：
        
        {{ instruction }}

        你生成的代码要符合这个格式：
        
        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```    

        ```{lang}
        ##File: {FILE_PATH}
        {CODE}
        ```

        其中，{lang}是代码的语言，{CODE}是代码的内容, {FILE_PATH} 是文件的路径，他们都在代码块中，请严格按上面的格式进行内容生成。
            
        请确保每份代码的完整性，而不要只生成修改部分。
        '''    
    
    def single_round_run(self,query:str,source_content:str)-> Tuple[str,Dict[str,str]]:
        llm_config = {"human_as_model":self.args.human_as_model} 

        if self.args.template == "common":
            init_prompt = self.single_round_instruction.prompt(instruction=query,content=source_content)    
        elif self.args.template == "auto_implement":
            init_prompt = self.auto_implement_function.prompt(instruction=query,content=source_content)
        
        with open(self.args.target_file, "w") as file:
            file.write(init_prompt)

        conversations = [
            {
                "role": "user",
                "content": init_prompt
            }
        ]

        t = self.llm.chat_oai(conversations=conversations,llm_config=llm_config)
        conversations.append({
            "role": "assistant",
            "content": t[0].output
        })
        return [t[0].output], conversations

    def multi_round_run(self,query:str,source_content:str,max_steps:int=10)-> Tuple[List[str],List[Dict[str,str]]]:   
        llm_config = {"human_as_model":self.args.human_as_model}        
        result = []
        
        if self.args.template == "common":
            init_prompt = self.multi_round_instruction.prompt(instruction=query,content=source_content)    
        elif self.args.template == "auto_implement":
            init_prompt = self.auto_implement_function.prompt(instruction=query,content=source_content)

        conversations = [
            {
                "role": "user",
                "content": init_prompt
            }
        ]                

        with open(self.args.target_file, "w") as file:
            file.write(init_prompt)

        t = self.llm.chat_oai(conversations=conversations,llm_config=llm_config)
        
        result.append(t[0].output)

        conversations.append({
                "role": "assistant",
                "content": t[0].output
        })

        if "__完成__" in t[0].output:
            return result, conversations

        current_step = 0

        while current_step < max_steps:        
                                
            conversations.append({
                "role": "user",
                "content": "继续"
            })

            with open(self.args.target_file, "w") as file:
                file.write("继续")
                  
            t = self.llm.chat_oai(conversations=conversations, llm_config=llm_config)
            
            result.append(t[0].output)
            conversations.append({
                "role": "assistant",
                "content": t[0].output
            })
            current_step += 1   
            
            if "__完成__" in t[0].output or "__EOF__" in t[0].output:
                return result, conversations         
            

        return result, conversations 
         