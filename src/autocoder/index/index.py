##File: /home/winubuntu/projects/ByzerRawCopilot/src/autocoder/index/index.py

import os
import json
from typing import List
from datetime import datetime
from autocoder.common import SourceCode

from pydantic import BaseModel
import byzerllm

class IndexItem(BaseModel):
    module_name: str
    symbols: str
    last_modified: str

class IndexManager:
    def __init__(self, llm,sources: List[SourceCode], source_dir: str):
        self.sources = sources
        self.source_dir = source_dir
        self.index_dir = os.path.join(source_dir, ".auto-coder")
        self.index_file = os.path.join(self.index_dir, "index.json")
        self.llm = llm

        # 如果索引目录不存在,则创建它
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

    @byzerllm.prompt(lambda self:self.llm,render="jinja2")
    def get_all_file_symbols(self,path:str,code:str)->str: 
        '''
        下列是文件 {{ path }} 的源码：
        
        {{ code }}
        
        从上述内容中获取文件中的符号。需要获取的符号类型包括：函数、类、变量、模块、包。 如果没有任何符号，返回"没有任何符号"。
        按如下格式返回：

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
            if os.path.exists(file_path):
                last_modified = os.path.getmtime(file_path)
                if source.module_name in index_data and index_data[source.module_name]["last_modified"] == last_modified:
                    continue

                symbols = self.get_all_file_symbols(source.module_name, source.source_code)                
                index_data[source.module_name] = {
                    "symbols": symbols,
                    "last_modified": last_modified
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
                last_modified=data["last_modified"]
            )
            index_items.append(index_item)

        return index_items