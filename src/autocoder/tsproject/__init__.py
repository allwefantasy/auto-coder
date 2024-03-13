##File: /home/winubuntu/projects/ByzerRawCopilot/src/byzercopilot/tsproject/__init__.py
from byzercopilot.common import SourceCode
from byzercopilot import common as FileUtils  
import os
from typing import Optional,Generator,List,Dict,Any
from git import Repo

class TSProject():
    
    def __init__(self,source_dir,git_url:Optional[str]=None,target_file:Optional[str]=None):
        self.directory = source_dir
        self.git_url = git_url        
        self.target_file = target_file       

    def output(self):
        return open(self.target_file, "r").read()                

    def is_typescript_file(self,file_path):
        return file_path.endswith(".ts") or file_path.endswith(".tsx")

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
    

    def get_source_codes(self)->Generator[SourceCode,None,None]:
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_typescript_file(file_path):
                    source_code = self.convert_to_source_code(file_path)
                    if source_code is not None:
                        yield source_code


    def run(self):
        if self.git_url is not None:
            self.clone_repository()

        if self.target_file is None:                
            for code in self.get_source_codes():
                print(f"##File: {code.module_name}")
                print(code.source_code)                
        else:            
            with open(self.target_file, "w") as file:
                for code in self.get_source_codes():
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