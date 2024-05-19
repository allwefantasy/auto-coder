import os
import json
import time
from typing import List,Dict,Any
from datetime import datetime
from autocoder.common import SourceCode, AutoCoderArgs
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import pydantic
import byzerllm
import hashlib
import textwrap
import tabulate

from loguru import logger

class IndexItem(pydantic.BaseModel):
   module_name: str
   symbols: str
   last_modified: float
   md5: str  # 新增文件内容的MD5哈希值字段


class TargetFile(pydantic.BaseModel):
   file_path: str
   reason: str = pydantic.Field(...,description="The reason why the file is the target file") 

class FileList(pydantic.BaseModel):
   file_list: List[TargetFile]


class IndexManager:
   def __init__(self, llm:byzerllm.ByzerLLM, sources: List[SourceCode], args:AutoCoderArgs):
       self.sources = sources
       self.source_dir = args.source_dir
       self.anti_quota_limit = args.index_model_anti_quota_limit or args.anti_quota_limit
       self.index_dir = os.path.join(self.source_dir, ".auto-coder")
       self.index_file = os.path.join(self.index_dir, "index.json")
       if llm and (s := llm.get_sub_client("index_model")):            
           self.index_llm =s
       else:
           self.index_llm =llm

       self.llm = llm    
       self.args = args
       self.max_input_length = args.index_model_max_input_length or args.model_max_input_length

       # 如果索引目录不存在,则创建它
       if not os.path.exists(self.index_dir):
           os.makedirs(self.index_dir)

   @byzerllm.prompt(lambda self: self.llm, render="jinja2")
   def _get_related_files(self,indices:str, file_paths: str) -> FileList:
       '''
       下面是所有文件以及对应的符号信息：
       
       {{ indices }}
       
       注意，
       1. 找到的文件名必须出现在上面的文件列表中
       2. 如果没有相关的文件，返回空即可
        
       请参考上面的信息，找到被下列文件使用或者引用到的文件列表：
       
       {{ file_paths }}    
       '''
       

   @byzerllm.prompt(lambda self: self.index_llm, render="jinja2")
   def get_all_file_symbols(self, path: str, code: str) -> str:
       '''        
       你的目标是从给定的代码中获取代码里的符号，需要获取的符号类型包括：
       
       1. 函数
       2. 类  
       3. 变量
       4. 所有导入语句 
           
       如果没有任何符号,返回空字符串就行。
       如果有符号，按如下格式返回:
           
       ```
       {符号类型}: {符号名称}, {符号名称}, ...
       ```

       注意：
       1. 直接输出结果，不要尝试使用任何代码        
       2. 不要分析代码的内容和目的
       
       下面是一段示例：

       ## 输入 
       下列是文件 /test.py 的源码：
       
       import os
       import time
       from loguru import logger
       import byzerllm

       a = ""

       @byzerllm.prompt(render="jinja")
       def auto_implement_function_template(instruction:str, content:str)->str:

       ## 输出

       函数：auto_implement_function_template
       变量：a
       类：
       导入语句：import os,import time,from loguru import logger,import byzerllm

       现在，让我们开始一个新的任务:
       
       ## 输入 
       下列是文件 {{ path }} 的源码：
       
       {{ code }}

       ## 输出
       '''

   def split_text_into_chunks(self, text, max_chunk_size=4096):
       lines = text.split("\n")
       chunks = []
       current_chunk = []
       current_length = 0
       for line in lines:
           if current_length + len(line) + 1 <= self.max_input_length:
               current_chunk.append(line)
               current_length += len(line) + 1
           else:
               chunks.append("\n".join(current_chunk))
               current_chunk = [line]
               current_length = len(line) + 1
       if current_chunk:
           chunks.append("\n".join(current_chunk))
       return chunks 

   def build_index_for_single_source(self,source: SourceCode):
       file_path = source.module_name
       if not os.path.exists(file_path):
           return None

       ext = os.path.splitext(file_path)[1].lower()  
       if ext in [".md",".html",".txt",".doc",".pdf"]:
           return None

       if source.source_code.strip() == "":
           return None
       
       md5 = hashlib.md5(source.source_code.encode('utf-8')).hexdigest()       

       try:               
           start_time = time.monotonic()
           source_code = source.source_code
           if len(source.source_code) > self.max_input_length:
               logger.warning(f"Warning: The length of source code is too long ({len(source.source_code)}) > model_max_input_length({self.max_input_length}), splitting into chunks...")
               chunks = self.split_text_into_chunks(source_code,self.max_input_length-1000)
               symbols = []
               for chunk in chunks:
                   chunk_symbols = self.get_all_file_symbols(source.module_name, chunk)
                   time.sleep(self.anti_quota_limit)
                   symbols.append(chunk_symbols)
               symbols = "\n".join(symbols)
           else:
               symbols = self.get_all_file_symbols(source.module_name, source_code)
               time.sleep(self.anti_quota_limit)
           
           logger.info(f"Parse and update index for {file_path} md5: {md5} took {time.monotonic() - start_time:.2f}s") 
           
       except Exception as e:
           logger.warning(f"Error: {e}")
           return None

       return {
           "module_name": source.module_name,
           "symbols": symbols,
           "last_modified": os.path.getmtime(file_path),
           "md5": md5
       }

   def build_index(self):
       if os.path.exists(self.index_file):
           with open(self.index_file, "r") as file:
               index_data = json.load(file)
       else:
           index_data = {}                   

       updated_sources = []

       with ThreadPoolExecutor(max_workers=self.args.index_build_workers) as executor:
                        
           wait_to_build_files = []
           for source in self.sources:
               md5 = hashlib.md5(source.source_code.encode('utf-8')).hexdigest() 
               if source.module_name not in index_data or index_data[source.module_name]["md5"] != md5:
                   wait_to_build_files.append(source)

           counter = 0 
           num_files = len(wait_to_build_files) 
           total_files = len(self.sources)
           logger.info(f"Total Files: {total_files}, Need to Build Index: {num_files}")       

           futures = [executor.submit(self.build_index_for_single_source, source) for source in wait_to_build_files]           
           for future in as_completed(futures):
               result = future.result()
               if result is not None:  
                   counter += 1
                   logger.info(f"Building Index:{counter}/{num_files}...")                 
                   module_name = result["module_name"]
                   index_data[module_name] = result
                   updated_sources.append(module_name)
                       
       if updated_sources:
           with open(self.index_file, "w") as file:
               json.dump(index_data, file, ensure_ascii=False, indent=2)

       return index_data      

   def read_index(self) -> List[IndexItem]:
       if not os.path.exists(self.index_file):
           return []

       with open(self.index_file, "r") as file:
           index_data = json.load(file)

       index_items = []
       for module_name, data in index_data.items():
           index_item = IndexItem(
               module_name=module_name,
               symbols=data["symbols"],
               last_modified=data["last_modified"],
               md5=data["md5"]
           )
           index_items.append(index_item)

       return index_items
    
   def _get_meta_str(self, max_chunk_size=4096,skip_symbols:bool = False):
       index_items = self.read_index()
       output = []
       current_chunk = []
       current_size = 0
       
       for item in index_items:
           item_str = f"##{item.module_name}\n{item.symbols}\n\n"
           if skip_symbols:
               item_str = f"{item.module_name}\n"
           item_size = len(item_str)
           
           if current_size + item_size > max_chunk_size:
               yield "".join(current_chunk)
               current_chunk = [item_str]
               current_size = item_size
           else:
               current_chunk.append(item_str)
               current_size += item_size
       
       if current_chunk:
           yield "".join(current_chunk) 

   def get_related_files(self, file_paths: List[str]):
       all_results = []
       lock = threading.Lock() 

       def process_chunk(chunk, chunk_count):
           result = self._get_related_files(chunk, "\n".join(file_paths))
           if result is not None:
               with lock:  
                   all_results.extend(result.file_list)
           else:
               logger.warning(f"Fail to find related files for chunk {chunk_count}. This may be caused by the model limit or the query not being suitable for the files.")
           time.sleep(self.args.anti_quota_limit)

       with ThreadPoolExecutor(max_workers=self.args.index_filter_workers) as executor:
           futures = []
           chunk_count = 0
           for chunk in self._get_meta_str(max_chunk_size=self.max_input_length-1000):
               future = executor.submit(process_chunk, chunk, chunk_count)
               futures.append(future)
               chunk_count += 1

           for future in as_completed(futures):
               future.result()

       all_results = list({file.file_path: file for file in all_results}.values())
       return FileList(file_list=all_results)
   
   def _query_index_with_thread(self,query,func):
        all_results = []
        lock = threading.Lock()
        
        def process_chunk(chunk):
            result = self._get_target_files_by_query(chunk, query)            
            if result is not None:
                with lock:
                    all_results.extend(result.file_list)
            else:
                logger.warning(f"Fail to find target files for chunk. This is caused by the model response not being in JSON format or the JSON being empty.")
            time.sleep(self.args.anti_quota_limit)

        with ThreadPoolExecutor(max_workers=self.args.index_filter_workers) as executor:
            futures = []
            for chunk in func():
                future = executor.submit(process_chunk, chunk)
                futures.append(future)

            for future in as_completed(futures):
                future.result()
        return all_results        

   def get_target_files_by_query(self, query: str) -> FileList:
        all_results:List[TargetFile] = []
        
        def w():
            return self._get_meta_str(skip_symbols=True,max_chunk_size=self.max_input_length-1000)

        logger.info("Find the related files by query according to the files...")
        temp_result = self._query_index_with_thread(query,w)
        all_results.extend(temp_result)            
        
        if self.args.index_filter_level >= 1:                
            logger.info("Find the related files by query according to the symbols...")
            def w():
                return self._get_meta_str(skip_symbols=False,max_chunk_size=self.max_input_length-1000)
            temp_result = self._query_index_with_thread(query,w)            
            all_results.extend(temp_result)
        
                
        all_results = list({file.file_path: file for file in all_results}.values())
        return FileList(file_list=all_results) 
   
   @byzerllm.prompt(lambda self: self.llm, render="jinja2",check_result=True)
   def _get_target_files_by_query(self,indices:str,query:str)->FileList:
       '''
       下面是已知文件以及对应的符号信息：
       
       {{ indices }}
                
       用户的问题是：
       
       {{ query }}        

       现在，请根据用户的问题以及的前面的文件以及符号信息，寻找相关文件路径。如果没有找到，返回空即可。
       '''


def build_index_and_filter_files(llm,args:AutoCoderArgs,sources:List[SourceCode])->str:
   
    def get_file_path(file_path):
        if file_path.startswith("##"):
            return file_path.strip()[2:]
        return file_path

    final_files:Dict[str,TargetFile] = {}      

    if not args.skip_build_index and llm:  

        ## keep Rest/RAG/Search sources
        for source in sources:
            if source.tag in ["REST","RAG","SEARCH"]:
                final_files[get_file_path(source.module_name)]=TargetFile(file_path=source.module_name,reason="Rest/Rag/Search")
            
        logger.info("Building index for all files...")
        index_manager = IndexManager(llm=llm,sources=sources,args=args)
        index_manager.build_index()
        
        logger.info(f"Finding related files in the index...")
        start_time = time.monotonic()
        target_files = index_manager.get_target_files_by_query(args.query)
        
        if target_files:
            for file in target_files.file_list:
                    logger.info(f"Target File: {file.file_path} reason: {file.reason}")    
                    file_path = file.file_path.strip()
                    final_files[get_file_path(file_path)] = file

        if target_files is not None and args.index_filter_level >= 2:                                    
            related_fiels = index_manager.get_related_files([file.file_path for file in target_files.file_list])            
            if related_fiels is not None:                                            
                for temp_file in related_fiels.file_list:
                        logger.info(f"Related File: {temp_file.file_path} reason: {temp_file.reason}")              
                
                for file in related_fiels.file_list:
                        file_path = file.file_path.strip()
                        final_files[get_file_path(file_path)] = file
        
        if not final_files:
            logger.warning("Warning: No related files found, use all files")
            for source in sources:
                final_files[get_file_path(source.module_name)]=TargetFile(file_path=source.module_name,reason="No related files found, use all files")
        
        logger.info(f"Find related files took {time.monotonic() - start_time:.2f}s")
    else:
        for source in sources:
            final_files[get_file_path(source.module_name)]=TargetFile(file_path=source.module_name,reason="Index is not enabled or the model is not available. Use all files.")
    
    def display_table_and_get_selections(data):
        from prompt_toolkit.shortcuts import checkboxlist_dialog 
        from prompt_toolkit.styles import Style       
        choices = [(file,f"{file} - {reason}") for file, reason in data]
        selected_files = [file for file, _ in choices]

        style = Style.from_dict({
            'dialog': 'bg:#88ff88',
            'dialog frame.label': 'bg:#ffffff #000000',
            'dialog.body': 'bg:#88ff88 #000000',
            'dialog shadow': 'bg:#00aa00',
        })

        result = checkboxlist_dialog(
            title="Target Files",
            text="Tab to switch between buttons, and Space/Enter to select/deselect.",
            values=choices,
            style=style,
            default_values=selected_files
        ).run()
        
        return [file for file in result] if result else []
            
    def print_selected(data):
        def wrap_text_in_table(data, max_width=None):
            if max_width is None:
                max_width = os.get_terminal_size().columns
            wrapped_data = []
            for row in data:
                wrapped_row = [textwrap.fill(str(cell), width=max_width) for cell in row]
                wrapped_data.append(wrapped_row)
            return wrapped_data
        terminal_width = os.get_terminal_size().columns
        separator = "=" * terminal_width
        print(separator, flush=True)
        print("Target Files You Selected".center(terminal_width), flush=True)
        print(separator, flush=True)

        table_data = [["File Path", "Reason"]]
        for file, reason in data:
            table_data.append([file, reason])

        wrapped_data = wrap_text_in_table(table_data)
        table_output = tabulate.tabulate(wrapped_data, headers="firstrow", tablefmt="grid")
        print(table_output, flush=True)

    if args.skip_confirm:
        final_filenames = [file.file_path for file in final_files.values()]        
    else: 
        target_files_data = [(file.file_path, file.reason) for file in final_files.values()]
        if not target_files_data:
            logger.warning("No target files found, try to rewrite the query and run again.")            
            final_filenames = []
        else:
            final_filenames = display_table_and_get_selections(target_files_data)
        
    print_selected([(file.file_path, file.reason) for file in final_files.values() if file.file_path in final_filenames])    

    source_code = "" 
    for file in sources:
        if file.module_name in final_filenames:
            source_code += f"##File: {file.module_name}\n"
            source_code += f"{file.source_code}\n\n" 
    return source_code