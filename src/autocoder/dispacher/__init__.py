
from autocoder.common import AutoCoderArgs,TranslateArgs,TranslateReadme
from autocoder.pyproject import PyProject,Level1PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from typing import Optional
import byzerllm
import os

@byzerllm.prompt(render="jinja")
def auto_implement_function_template(instruction:str, content:str)->str:
    '''
    下面是一些文件路径以及每个文件对应的源码：

    {{ content }}

    请参考上面的内容，重新实现所有文件下方法体标记了如下内容的方法：

    ```python
    raise NotImplementedError("This function should be implemented by the model.")
    ```
    
    {{ instruction }}
        
    '''
    pass

@byzerllm.prompt(render="jinja")
def instruction_template(instruction:str, content:str)->str:
    '''
    下面是一些文件路径以及每个文件对应的源码：

    {{ content }}    
    
    {{ instruction }}
        
    '''
    pass

@byzerllm.prompt(render="jinja")
def translate_readme(content:str,lang:str)->str:
    '''
    下面是一些文件路径以及每个文件对应的内容：

    {{ content }}    
    
    请参考上面的内容，将上面的每一个文件对应的内容翻译成{{ lang }}。
    
    '''
    pass

class ActionTSProject:
    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None) -> None:
        self.args = args
        self.llm = llm

    def run(self):
        args = self.args
        if args.project_type != "ts":
            return False
        pp = TSProject(source_dir=args.source_dir, git_url=args.git_url, target_file=args.target_file)
        pp.run()
        self.process_content(pp.output())
        return True

    def process_content(self, content: str):
        args = self.args
        if args.template == "common":
            instruction = args.query or "Please implement the following methods"
            content = instruction_template(instruction=instruction, content=content)
        elif args.template == "auto_implement":
            content = auto_implement_function_template(instruction="", content=content)

        if args.execute:
            t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": content
            }])
            content = t[0].output

        with open(args.target_file, "w") as file:
            file.write(content)

class ActionPyScriptProject:
    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None) -> None:
        self.args = args
        self.llm = llm
    
    def run(self)-> bool:
        args = self.args  
        if args.project_type != "py-script":
            return False
        pp = Level1PyProject(script_path=args.script_path, package_name=args.package_name)
        content = pp.run()
        self.process_content(content)
        return True

    def process_content(self, content: str):
        args = self.args
        if args.template == "common":
            instruction = args.query or "Please implement the following methods"
            content = instruction_template(instruction=instruction, content=content)
        elif args.template == "auto_implement":
            content = auto_implement_function_template(instruction="", content=content)

        if args.execute:
            t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": content
            }])
            content = t[0].output
        with open(self.args.target_file, "w") as file:
            file.write(content)

class ActionPyProject:
    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None) -> None:
        self.args = args
        self.llm = llm
    
    def run(self):
        args = self.args
        if args.project_type != "py":
            return False
        pp = PyProject(source_dir=args.source_dir, git_url=args.git_url, target_file=args.target_file)
        pp.run()
        self.process_content(pp.output())
        return True

    def process_content(self, content: str):
        args = self.args
        if args.template == "common":
            instruction = args.query or "Please implement the following methods"
            content = instruction_template(instruction=instruction, content=content)
        elif args.template == "auto_implement":
            content = auto_implement_function_template(instruction="", content=content)

        if args.execute:
            t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": content
            }])
            content = t[0].output

        with open(args.target_file, "w") as file:
            file.write(content)
        
class ActionSuffixProject:
    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None) -> None:
        self.args = args
        self.llm = llm
        
    def run(self):
        args = self.args        
        pp = SuffixProject(source_dir=args.source_dir, git_url=args.git_url, target_file=args.target_file, project_type=args.project_type)
        pp.run()
        self.process_content(pp.output())

    def process_content(self, content: str):
        args = self.args
        if args.template == "common":
            instruction = args.query or "Please implement the following methods"
            content = instruction_template(instruction=instruction, content=content)
        elif args.template == "auto_implement":
            content = auto_implement_function_template(instruction="", content=content)

        if args.execute:
            t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": content
            }])
            content = t[0].output

        with open(args.target_file, "w") as file:
            file.write(content)

class ActionTranslate():
    def __init__(self,args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None) -> None:
        self.args = args
        self.llm = llm        

    def run(self):
        args = self.args        
        if args.project_type.startswith("translate"):
            if args.project_type == "translate" and args.query is not None and self.llm is not None:
                # we should extract the message from query
                t = self.llm.chat_oai(conversations=[{
                    "role": "user",
                    "content": args.query
                }],response_class=TranslateArgs)                
                tranlate_args:TranslateArgs = t[0].value
                if tranlate_args:
                    lang = tranlate_args.target_lang
                    suffixes = tranlate_args.file_suffix
                    new_file_mark = tranlate_args.new_file_mark
            else:        
                #translate/中文/.md/cn
                [_, lang, suffixes, new_file_mark] = args.project_type.split("/")
            
            print(f"lang:{lang}, suffixes:{suffixes}, new_file_mark:{new_file_mark}",flush=True)
            def file_filter(file_path, suffixes):
                for suffix in suffixes:
                    if suffix.startswith("."):
                        if file_path.endswith(f"-{new_file_mark}{suffix}"):
                            return False
                    else:
                        if file_path.endswith(f"-{new_file_mark}.{suffix}"):
                            return False
                return True
            
            pp = SuffixProject(source_dir=args.source_dir, 
                                git_url=args.git_url, 
                                target_file=args.target_file, 
                                project_type=suffixes,
                                file_filter=file_filter                               
                                ) 
            pp.run()            
            for source in pp.sources:
                content = translate_readme(content=source.source_code, lang=lang)
                t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": content
                }]) 
                readme = TranslateReadme(filename=source.module_name,content=t[0].output)
                filename, extension = os.path.splitext(readme.filename)                                                   
                chinese_filename = f"{filename}-{new_file_mark}{extension}"
                with open(chinese_filename, "w") as file:        
                    file.write(readme.content)

            # t = self.llm.chat_oai(conversations=[{
            #     "role": "user",
            #     "content": content
            # }], response_class=Translates)         
            # readmes: Translates = t[0].value
            # if not readmes:
            #     # output = t[0].response.output.strip()
            #     # if output and output.startswith("```json\n"):
            #     #     output = output[len("```json"):-3]
            #     #     readmes = Translates.parse_raw(output)                                        
            #     # else:    
            #     print(f"Fail to translate the content. {t[0]}")
            #     raise Exception(f"Fail to translate the content.")            
                

class Dispacher():
    def __init__(self, args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None):
        self.args = args
        self.llm = llm 

    def dispach(self):
        args = self.args
        actions = [ActionTranslate(args=args,llm=self.llm),
                    ActionTSProject(args=args,llm=self.llm),
                    ActionPyScriptProject(args=args,llm=self.llm),
                    ActionPyProject(args=args,llm=self.llm),
                    ActionSuffixProject(args=args,llm=self.llm)]
        for action in actions:
            if action.run():
                return                
        
    