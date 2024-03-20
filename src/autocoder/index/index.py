import os
import json
import time
from typing import List
from datetime import datetime
from autocoder.common import SourceCode, AutoCoderArgs

import pydantic
import byzerllm
import hashlib

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
    def __init__(self, llm, sources: List[SourceCode], args:AutoCoderArgs):
        self.sources = sources
        self.source_dir = args.source_dir
        self.anti_quota_limit = args.anti_quota_limit
        self.index_dir = os.path.join(self.source_dir, ".auto-coder")
        self.index_file = os.path.join(self.index_dir, "index.json")
        self.llm = llm
        self.args = args

        # 如果索引目录不存在,则创建它
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

    @byzerllm.prompt(lambda self: self.llm, render="jinja2")
    def _get_related_files(self,indices:str, file_paths: str) -> FileList:
        '''
        下面是所有文件以及对应的符号信息：
        
        {{ indices }}

        请参考上面的信息，找到被下列文件使用或者引用到的文件列表：
        
        {{ file_paths }}

        如果没有相关的文件，返回空即可
        '''
        

    @byzerllm.prompt(lambda self: self.llm, render="jinja2")
    def get_all_file_symbols(self, path: str, code: str) -> str:
        '''
        下列是文件 {{ path }} 的源码：
        
        {{ code }}
        
        从上述内容中获取文件中的符号。需要获取的符号类型包括：
        
        1. 函数
        2. 类  
        3. 变量
        4. 所有导入语句 
        
        如果没有任何符号,返回"没有任何符号"。
        最终结果按如下格式返回:

        符号类型: 符号名称, 符号名称, ...        
        '''

    def build_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, "r") as file:
                index_data = json.load(file)
        else:
            index_data = {}

        updated_sources = []

        for source in self.sources:
            file_path = source.module_name                                   
            md5 = hashlib.md5(source.source_code.encode('utf-8')).hexdigest()
            print(f"try to build index for {file_path} md5: {md5}")
            if source.source_code.strip() == "":
                continue

            if source.module_name in index_data and index_data[source.module_name]["md5"] == md5:
                continue
            
            try:
                print(f"parse and update index for {file_path} md5: {md5}")
                source_code = source.source_code
                if len(source.source_code) > self.args.model_max_input_length:
                    print(f"Warning: The length of source code is too long ({len(source.source_code)}) > model_max_input_length({self.args.model_max_input_length}) , keep the first {self.args.model_max_input_length} characters to avoid failure of the model limit")
                    source_code = source.source_code[:self.args.model_max_input_length]
                symbols = self.get_all_file_symbols(source.module_name, source_code)
                time.sleep(self.anti_quota_limit)
            except Exception as e:
                print(f"Error: {e}")
                continue

            index_data[source.module_name] = {
                "symbols": symbols,
                "last_modified": os.path.getmtime(file_path),
                "md5": md5
            }
            updated_sources.append(source)

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
     
    def _get_meta_str(self, max_chunk_size=4096):
        index_items = self.read_index()
        output = []
        current_chunk = []
        current_size = 0
        
        for item in index_items:
            item_str = f"##{item.module_name}\n{item.symbols}\n\n"
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
        
        for chunk in self._get_meta_str():
            result = self._get_related_files(chunk, "\n".join(file_paths))
            all_results.extend(result.file_list)
        
        return FileList(file_list=all_results)

    def get_target_files_by_query(self, query: str) -> FileList:
        all_results = []
        
        for chunk in self._get_meta_str():
            result = self._get_target_files_by_query(chunk, query)
            all_results.extend(result.file_list)
        
        return FileList(file_list=all_results) 
    
    @byzerllm.prompt(lambda self: self.llm, render="jinja2",print_prompt=True)
    def _get_target_files_by_query(self,indices:str,query:str)->FileList:
        '''
        下面是所有文件以及对应的符号信息：
        
        {{ indices }}

        请参考上面的信息，根据用户的问题寻找相关文件。如果没有相关的文件，返回空即可。

        用户的问题是：{{ query }}
        '''

    


def build_index_and_filter_files(llm,args:AutoCoderArgs,sources:List[SourceCode])->str:
    final_files = []
    if not args.skip_build_index and llm:        
        index_manager = IndexManager(llm=llm,sources=sources,args=args)
        index_manager.build_index()
        target_files = index_manager.get_target_files_by_query(args.query)
        if target_files is not None:    
            print(f"Target Files: {target_files.file_list}",flush=True)
            related_fiels = index_manager.get_related_files([file.file_path for file in target_files.file_list])            
            if related_fiels is not None:                            
                print(f"Related Files: {related_fiels.file_list}",flush=True)                
                for file in target_files.file_list + related_fiels.file_list:
                    file_path = file.file_path.strip()
                    if file_path.startswith("##"):
                        final_files.append(file_path.strip()[2:]) 
                    else:
                        final_files.append(file_path) 
        if not final_files:
            print("Warning: No related files found, use all files",flush=True)
            final_files = [file.module_name for file in sources]                          
    else:
        final_files = [file.module_name for file in sources]

    

    source_code = "" 
    for file in sources:
        if file.module_name in final_files:
            source_code += f"##File: {file.module_name}\n"
            source_code += f"{file.source_code}\n\n" 
    return source_code 