from autocoder.common import SourceCode,AutoCoderArgs
from autocoder import common as FileUtils
from autocoder.utils.rest import HttpDoc
import os
from typing import Optional,Generator,List,Dict,Any
from git import Repo
import ast
import importlib
import byzerllm
import importlib
import pkgutil
from autocoder.common.search import Search,SearchEngine
from autocoder.rag.simple_rag import SimpleRAG


def is_likely_useful_file(file_path):
    """Determine if the file is likely to be useful by excluding certain directories and specific file types."""
    excluded_dirs = ["docs", "examples", "tests", "test", "__pycache__", "scripts", "benchmarks","build"]
    utility_or_config_files = ["hubconf.py", "setup.py"]
    github_workflow_or_docs = ["stale.py", "gen-card-", "write_model_card"]
    
    if any(part.startswith('.') for part in file_path.split('/')):
        return False
    if 'test' in file_path.lower():
        return False
    for excluded_dir in excluded_dirs:
        if f"/{excluded_dir}/" in file_path or file_path.startswith(excluded_dir + "/"):
            return False
    for file_name in utility_or_config_files:
        if file_name in file_path:
            return False
    for doc_file in github_workflow_or_docs:
        if doc_file in file_path:
            return False
    return True

def is_test_file(file_content):
    """Determine if the file content suggests it is a test file."""
    test_indicators = ["import unittest", "import pytest", "from unittest", "from pytest"]
    return any(indicator in file_content for indicator in test_indicators)

class Level1PyProject():
    
    def __init__(self,script_path,package_name):
        self.script_path = script_path
        self.package_name = package_name

    def get_imports_from_script(self,file_path):
        script = ""
        with open(file_path, "r") as file:
            script = file.read()
            tree = ast.parse(script, filename=file_path)
        
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        return imports,script

    def filter_imports(self,imports, package_name):
        filtered_imports = []
        for import_ in imports:
            if isinstance(import_, ast.Import):
                for alias in import_.names:
                    if alias.name.startswith(package_name):
                        filtered_imports.append(alias.name)
            elif isinstance(import_, ast.ImportFrom):
                if import_.module and import_.module.startswith(package_name):
                    filtered_imports.append(import_.module)
        return filtered_imports



    def fetch_source_code(self,import_name):
        spec = importlib.util.find_spec(import_name)
        if spec and spec.origin:
            with open(spec.origin, "r") as file:
                return file.read()
        return None
    
    @byzerllm.prompt(render="jinja")
    def auto_implement(self,instruction:str, sources:List[Dict[str,Any]])->str:
        '''        
        {% for source in sources %}
        #Module:{{ source.module_name }}
        {{ source.source_code }}
        {% endfor %}                   
        '''
        pass

    def run(self):
        imports,script = self.get_imports_from_script(self.script_path)
        filtered_imports = self.filter_imports(imports, self.package_name)
        sources = [] 


        for import_name in filtered_imports:
            source_code = self.fetch_source_code(import_name)
            if source_code:
                sources.append(SourceCode(module_name=import_name, source_code=source_code))            
            else:
                print(f"Could not fetch source code for {import_name}.")

        sources.append(SourceCode(module_name="script", source_code=script))

        sources = [source.dict() for source in sources]
        return self.auto_implement(instruction="", sources=sources)

class PyProject():
    
    def __init__(self,args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None):        
        self.args = args
        self.directory = args.source_dir
        self.git_url = args.git_url        
        self.target_file = args.target_file 
        self.sources = []   
        self.llm = llm   

    def output(self):
        return open(self.target_file, "r").read()                

    def is_python_file(self,file_path):
        return file_path.endswith(".py")

    def read_file_content(self,file_path):
        with open(file_path, "r") as file:
            return file.read()

    def convert_to_source_code(self,file_path):        
        if not is_likely_useful_file(file_path):
            return None
               
        module_name = file_path
        source_code = self.read_file_content(file_path)

        if not FileUtils.has_sufficient_content(source_code,min_line_count=1):
            return None
        
        if is_test_file(source_code):
            return None
        return SourceCode(module_name=module_name, source_code=source_code)
    
    def get_package_source_codes(self, package_name: str) -> Generator[SourceCode, None, None]:
        try:
            package = importlib.import_module(package_name)
            package_path = os.path.dirname(package.__file__)
            
            for _, name, _ in pkgutil.iter_modules([package_path]):
                module_name = f"{package_name}.{name}"
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    continue
                module_path = spec.origin
                source_code = self.convert_to_source_code(module_path)
                source_code.tag = "PACKAGE"
                if source_code is not None:
                    yield source_code
        except ModuleNotFoundError:
            print(f"Package {package_name} not found.") 

    def get_rest_source_codes(self) -> Generator[SourceCode, None, None]:
        if self.args.urls:
            http_doc = HttpDoc(args=self.args, llm=self.llm,urls=self.args.urls.split(","))
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

    def get_source_codes(self)->Generator[SourceCode,None,None]:        
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_python_file(file_path):
                    source_code = self.convert_to_source_code(file_path)
                    if source_code is not None:
                        yield source_code


    def run(self,packages:List[str]=[]):
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

            for package in packages:
                for code in self.get_package_source_codes(package):
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
                
                for package in packages:
                    for code in self.get_package_source_codes(package):
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
