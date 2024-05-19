from autocoder.common import SourceCode,AutoCoderArgs
from autocoder import common as FileUtils  
from autocoder.utils.rest import HttpDoc
from autocoder.rag.simple_rag import SimpleRAG
import os
from typing import Optional,Generator,List,Dict,Any

from git import Repo
import byzerllm
from autocoder.common.search import Search,SearchEngine

class TSProject():
    
    def __init__(self,args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None):        
        self.args = args
        self.directory = args.source_dir
        self.git_url = args.git_url        
        self.target_file = args.target_file 
        self.sources = []   
        self.llm = llm    

    def output(self):
        return open(self.target_file, "r").read()                    

    def read_file_content(self,file_path):
        with open(file_path, "r") as file:
            return file.read()            

    def is_likely_useful_file(self,file_path):
        # Ignore hidden files and directories
        if any(part.startswith(".") for part in file_path.split(os.path.sep)):
            return False

        # Ignore common build output, dependency and configuration directories
        ignore_dirs = [
            "node_modules",
            "dist",
            "build",
            "coverage",
            "public",
            "config",
            "__tests__",
            "__mocks__",
        ]
        if any(dir in file_path.split(os.path.sep) for dir in ignore_dirs):
            return False

        # Ignore common non-source files in React + TS projects 
        ignore_extensions = [
            ".json",
            ".md",
            ".txt",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".svg",
            ".ico",
            ".css",
            ".less",
            ".scss",
            ".sass",
            ".map",
        ]
        if any(file_path.endswith(ext) for ext in ignore_extensions):
            return False
        
        # Include .ts, .tsx, .js and .jsx files
        include_extensions = [".ts", ".tsx", ".js", ".jsx"]
        if any(file_path.endswith(ext) for ext in include_extensions):
            return True

        return False    

    def convert_to_source_code(self,file_path):        
        if not self.is_likely_useful_file(file_path):
            return None
               
        module_name = file_path
        source_code = self.read_file_content(file_path)

        if not FileUtils.has_sufficient_content(source_code,min_line_count=1):
            return None
                        
        return SourceCode(module_name=module_name, source_code=source_code)
    

    def get_source_codes(self)->Generator[SourceCode,None,None]:
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                source_code = self.convert_to_source_code(file_path)
                if source_code is not None:
                    yield source_code
                    
    def get_rest_source_codes(self) -> Generator[SourceCode, None, None]:
        if self.args.urls:
            http_doc = HttpDoc(args = self.args, llm=self.llm,urls=self.args.urls.split(","))
            sources = http_doc.crawl_urls()  
            for source in sources:
                source.tag = "REST"       
            return sources
        return [] 
    
    def get_rag_source_codes(self):
        if not self.args.enable_rag_search and not self.args.enable_rag_context:
            return []
        rag = SimpleRAG(self.llm,self.args,self.args.source_dir)
        docs = rag.search(self.args.query)
        for doc in docs:
            doc.tag = "RAG"
        return docs

    def get_search_source_codes(self):
        temp = self.get_rag_source_codes()
        if self.args.search_engine and self.args.search_engine_token:
            if self.args.search_engine == "bing":
                search_engine = SearchEngine.BING
            else:
                search_engine = SearchEngine.GOOGLE

            searcher=Search(args=self.args,llm=self.llm,search_engine=search_engine,subscription_key=self.args.search_engine_token)
            search_query = self.args.search or self.args.query
            search_context = searcher.answer_with_the_most_related_context(search_query)  
            return temp + [SourceCode(module_name="SEARCH_ENGINE", source_code=search_context,tag="SEARCH")]
        return temp + []       

    def run(self):
        if self.git_url is not None:
            self.clone_repository()

        if self.target_file is None:          
            for code in self.get_rest_source_codes():
                self.sources.append(code)
                print(f"##File: {code.module_name}")
                print(code.source_code)

            for code in self.get_search_source_codes():
                self.sources.append(code)
                print(f"##File: {code.module_name}")
                print(code.source_code)    

            for code in self.get_source_codes():
                self.sources.append(code)
                print(f"##File: {code.module_name}")
                print(code.source_code)                
        else:            
            with open(self.target_file, "w") as file:
                for code in self.get_rest_source_codes():
                    self.sources.append(code)
                    file.write(f"##File: {code.module_name}\n")
                    file.write(f"{code.source_code}\n\n")

                for code in self.get_search_source_codes():
                    self.sources.append(code)
                    file.write(f"##File: {code.module_name}\n")
                    file.write(f"{code.source_code}\n\n")    
                    
                for code in self.get_source_codes():
                    self.sources.append(code)
                    file.write(f"##File: {code.module_name}\n")
                    file.write(f"{code.source_code}\n\n")
                    
    
    def clone_repository(self):   
        if self.git_url is None:
            raise ValueError("git_url is required to clone the repository")
             
        if os.path.exists(self.directory):
            print(f"Directory {self.directory} already exists. Skipping cloning.")
        else:
            print(f"Cloning repository {self.git_url} into {self.directory}")
            Repo.clone_from(self.git_url, self.directory)