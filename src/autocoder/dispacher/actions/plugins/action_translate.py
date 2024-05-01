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
    # pattern = re.compile(r"^>>>>>(.+)", re.MULTILINE | re.DOTALL)
    # match = pattern.search(content)
    # if match:
    #     return match.group(1)
    # else:
    #     lines = content.splitlines()
    #     if len(lines) >= 1 and lines[0].strip().startswith(">>>>>"):
    #         return "\n".join([lines[0][len(">>>>>")+1:]]+lines[1:])
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
            # we should extract the message from query
            # then we can know what we should do e.g. translate the markdown file from Chinese to English
            # here lang is the target language, suffixes is the file suffixes, new_file_mark is added to the new file name.
            ## for example, if the original file name is README.md, the new file name will be README-<new_file_mark>.md
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
            #translate/中文/.md/cn/xxxx.md,xxxx2.md
            [_, lang, suffixes, new_file_mark,file_list_str,output_dir,should_translate_file_name] = args.project_type.split("/")
            file_list = file_list_str.split(",")
        
        logger.info(f"lang:{lang}, suffixes:{suffixes}, new_file_mark:{new_file_mark}  should_translate_file_name:{should_translate_file_name} file list: {file_list}",flush=True)
        # human input confirm
        input_confirm = input("Please confirm the above information is correct, input 'y' to continue, input 'n' to exit:")
        if input_confirm != "y":
            return True        

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