import os
import json
import time
from typing import List
from datetime import datetime
from autocoder.common import SourceCode, AutoCoderArgs
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import pydantic
import byzerllm
import hashlib

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
            