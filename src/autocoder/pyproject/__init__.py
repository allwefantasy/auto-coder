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
        if not FileUtils.is_likely_useful_file(file_path):
            return None
               
        module_name = file_path
        source_code = self.read_file_content(file_path)

        if not FileUtils.has_sufficient_content(source_code,min_line_count=1):
            return None
        
        if FileUtils.is_test_file(source_code):
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
                if source_code is not None:
                    yield source_code
        except ModuleNotFoundError:
            print(f"Package {package_name} not found.") 

    def get_rest_source_codes(self) -> Generator[SourceCode, None, None]:
        if self.args.urls:
            http_doc = HttpDoc(urls=self.args.urls.split(","), llm=self.llm)
            sources = http_doc.crawl_urls()         
            return sources
        return []  

    def get_search_source_codes(self):
        if self.args.search_engine and self.args.search_engine_token:
            if self.args.search_engine == "bing":
                search_engine = SearchEngine.BING
            else:
                search_engine = SearchEngine.GOOGLE

            searcher=Search(llm=self.llm,search_engine=search_engine,subscription_key=self.args.search_engine_token)
            search_context = searcher.answer_with_the_most_related_context(self.args.query)  
            return [SourceCode(module_name="SEARCH_ENGINE", source_code=search_context)]
        return []    

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
