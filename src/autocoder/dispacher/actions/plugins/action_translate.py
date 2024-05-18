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
from rich import print
from rich.table import Table

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

def confirm_translation_parameters(translate_args: TranslateArgs) -> TranslateArgs:
    while True:
        table = Table(title="Translation Parameters")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_row("Target Language", translate_args.target_lang)
        table.add_row("File Suffixes", translate_args.file_suffix)
        table.add_row("New File Mark", translate_args.new_file_mark)
        table.add_row("Translate File Name", str(translate_args.should_translate_file_name))
        table.add_row("File List", ", ".join(translate_args.file_list))
        table.add_row("Output Directory", translate_args.output_dir)
        print(table)

        if confirm("Are the above parameters correct?"):
            break

        param_options = [
            ("1", "Target Language"),
            ("2", "File Suffixes"), 
            ("3", "New File Mark"),
            ("4", "Translate File Name"),
            ("5", "File List"),
            ("6", "Output Directory")
        ]
        selected_param = radiolist_dialog(
            title="Select parameter to modify",
            text="Choose the parameter you want to change:",
            values=param_options
        ).run()

        if selected_param == "1":
            translate_args.target_lang = prompt("Enter the new target language: ")
        elif selected_param == "2":
            translate_args.file_suffix = prompt("Enter the new file suffixes (comma-separated): ")
        elif selected_param == "3":
            translate_args.new_file_mark = prompt("Enter the new file mark: ")
        elif selected_param == "4":
            translate_args.should_translate_file_name = confirm("Translate file names?")
        elif selected_param == "5":
            translate_args.file_list = prompt("Enter the new file list (comma-separated): ").split(",")
        elif selected_param == "6":
            translate_args.output_dir = prompt("Enter the new output directory: ")

    return translate_args

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
        
        translate_args = TranslateArgs(target_lang=lang,file_suffix=suffixes,new_file_mark=new_file_mark,file_list=file_list,output_dir=output_dir,should_translate_file_name=should_translate_file_name)                           

        translate_args = confirm_translation_parameters(translate_args)
        
        def file_filter(file_path, suffixes):
            for suffix in suffixes:
                if suffix.startswith("."):
                    if file_path.endswith(f"-{translate_args.new_file_mark}{suffix}"):
                        return False
                else:
                    if file_path.endswith(f"-{translate_args.new_file_mark}.{suffix}"):
                        return False
            return True
        
        args.project_type = translate_args.file_suffix
        pp = SuffixProject(args=args, llm=self.llm,
                            file_filter=file_filter                               
                            ) 
        pp.run()                        
        for source in pp.sources:
            if translate_args.file_list and source.module_name not in translate_args.file_list:
                continue
            logger.info(f"Translating {source.module_name}...")
            max_tokens = self.args.model_max_length or 2000
            segments = split_code_into_segments(source_code=source.source_code,max_tokens=max_tokens)
            temp_result = []
            segment_count = 0
            for segment in segments:                    
                content = translate_readme(content=segment, lang=translate_args.target_lang,instruction=args.query)
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
            
            if translate_args.new_file_mark:
                new_file_mark = f"-{translate_args.new_file_mark}"
            
            if translate_args.should_translate_file_name:
                file_short_name = translate_readme.with_llm(self.llm).run(content=file_short_name, lang=translate_args.target_lang,instruction=args.query)
                file_short_name = file_short_name.replace(" ","_")
                
            if translate_args.output_dir:
                new_filename = os.path.join(translate_args.output_dir,f"{file_short_name}{new_file_mark}{extension}")                                                  
            else:
                new_filename = f"{filename}{new_file_mark}{extension}"

            logger.info(f"Writing to {new_filename}...")    
            with open(new_filename, "w") as file:        
                file.write(readme.content)
        return True