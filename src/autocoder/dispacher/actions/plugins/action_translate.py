from autocoder.common import AutoCoderArgs,TranslateArgs,TranslateReadme,split_code_into_segments,SourceCode
from autocoder.pyproject import PyProject,Level1PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.index.index import build_index_and_filter_files
from autocoder.common.code_auto_merge import CodeAutoMerge
from autocoder.common.code_auto_generate import CodeAutoGenerate
from typing import Optional,Generator
import byzerllm
import os
import time
from loguru import logger
from prompt_toolkit import prompt, print_formatted_text
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import confirm, radiolist_dialog
from prompt_toolkit.styles import Style
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.markup import MarkdownLexer

@byzerllm.prompt()
def translate_readme(content:str,lang:str,instruction:Optional[str]=None)->str:
    '''
    你做翻译时，需要遵循如下要求：
    
    {%- if instruction %}
    {{ instruction }}
    {%- endif %}    

    请将下面的内容翻译成{{ lang }}：

    {{ content }}     
    '''    

def get_translate_part(content: str) -> str:
    return content

class ActionTranslate():
    def __init__(self,args:AutoCoderArgs,llm:Optional[byzerllm.ByzerLLM]=None) -> None:
        self.args = args
        self.llm = llm        

    def run(self):
        args = self.args        
        if not args.project_type.startswith("translate"):
            return False
        
        if args.project_type == "translate" and args.query is not None and self.llm is not None:
            t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": args.query
            }],response_class=TranslateArgs)                
            tranlate_args:TranslateArgs = t[0].value
            if tranlate_args:
                lang = tranlate_args.target_lang
                suffixes = tranlate_args.file_suffix
                new_file_mark = tranlate_args.new_file_mark
                file_list = tranlate_args.file_list
                output_dir = tranlate_args.output_dir  
                should_translate_file_name = tranlate_args.should_translate_file_name
        else:        
            [_, lang, suffixes, new_file_mark,file_list_str,output_dir,should_translate_file_name] = args.project_type.split("/")
            file_list = file_list_str.split(",")
        
        tranlate_args = TranslateArgs(target_lang=lang,file_suffix=suffixes,new_file_mark=new_file_mark,file_list=file_list,output_dir=output_dir,should_translate_file_name=should_translate_file_name)                           

        # Display the translation parameters for user confirmation
        print_formatted_text(HTML(f"""
<h3>Please confirm the following translation parameters:</h3>

<table>
  <tr>
    <th>Parameter</th>
    <th>Value</th>
  </tr>
  <tr>
    <td>1. Target Language</td>
    <td>{lang}</td>
  </tr>
  <tr>
    <td>2. File Suffixes</td>  
    <td>{suffixes}</td>
  </tr>
  <tr>
    <td>3. New File Mark</td>
    <td>{new_file_mark}</td>
  </tr>
  <tr>  
    <td>4. Translate File Name</td>
    <td>{should_translate_file_name}</td>
  </tr>
  <tr>
    <td>5. File List</td>
    <td>{file_list}</td>  
  </tr>
</table>
        """))

        if not confirm("Are the above parameters correct?"):
            param_options = [
                ("1", "Target Language"),
                ("2", "File Suffixes"),  
                ("3", "New File Mark"),
                ("4", "Translate File Name"),
                ("5", "File List")
            ]
            selected_param = radiolist_dialog(
                title="Select parameter to modify",
                text="Choose the parameter you want to change:",
                values=param_options
            ).run()

            if selected_param == "1":
                lang = prompt("Enter the new target language: ")
            elif selected_param == "2":
                suffixes = prompt("Enter the new file suffixes (comma-separated): ")
            elif selected_param == "3":  
                new_file_mark = prompt("Enter the new file mark: ")
            elif selected_param == "4":
                should_translate_file_name = confirm("Translate file names?")
            elif selected_param == "5":
                file_list = prompt("Enter the new file list (comma-separated): ").split(",")

        def file_filter(file_path, suffixes):
            for suffix in suffixes:
                if suffix.startswith("."):
                    if file_path.endswith(f"-{new_file_mark}{suffix}"):
                        return False
                else:
                    if file_path.endswith(f"-{new_file_mark}.{suffix}"):
                        return False
            return True
        
        args.project_type = suffixes
        pp = SuffixProject(args=args, llm=self.llm,
                            file_filter=file_filter                               
                            ) 
        pp.run()                        
        for source in pp.sources:
            if file_list and source.module_name not in file_list:
                continue
            logger.info(f"Translating {source.module_name}...")
            max_tokens = self.args.model_max_length or 2000
            segments = split_code_into_segments(source_code=source.source_code,max_tokens=max_tokens)
            temp_result = []
            segment_count = 0
            for segment in segments:                    
                content = translate_readme(content=segment, lang=lang,instruction=args.query)
                t = self.llm.chat_oai(conversations=[{
                "role": "user",
                "content": content
                }])                                
                temp_result.append(get_translate_part(t[0].output)) 
                time.sleep(args.anti_quota_limit) 
                segment_count += 1
                print(f"Translated {segment_count}({len(content)}) of {len(segments)} segments from {source.module_name}",flush=True)
            readme = TranslateReadme(filename=source.module_name,content="".join(temp_result))
            filename, extension = os.path.splitext(readme.filename) 
            file_short_name,_ = os.path.splitext(os.path.basename(filename))
            
            if new_file_mark:
                new_file_mark = f"-{new_file_mark}"
            
            if should_translate_file_name:
                file_short_name = translate_readme.with_llm(self.llm).run(content=file_short_name, lang=lang,instruction=args.query)
                file_short_name = file_short_name.replace(" ","_")
                
            if output_dir:
                new_filename = os.path.join(output_dir,f"{file_short_name}{new_file_mark}{extension}")                                                  
            else:
                new_filename = f"{filename}{new_file_mark}{extension}"

            logger.info(f"Writing to {new_filename}...")    
            with open(new_filename, "w") as file:        
                file.write(readme.content)
        return True