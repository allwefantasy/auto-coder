from autocoder.common import SourceCode
from autocoder import common as FileUtils  
import os
from typing import Optional, Generator, List, Dict, Any, Callable
from git import Repo

class SuffixProject():
    
    def __init__(self, source_dir, 
                 project_type: str,
                 git_url: Optional[str] = None,
                 target_file: Optional[str] = None,
                 file_filter: Optional[Callable[[str], bool]] = None):
        self.directory = source_dir
        self.git_url = git_url        
        self.target_file = target_file  
        self.project_type = project_type
        self.suffixs = [f".{suffix}" if not suffix.startswith('.') else suffix for suffix in self.project_type.split(",") if suffix.strip() != ""]
        self.file_filter = file_filter

    def output(self):
        return open(self.target_file, "r").read()                

    def is_suffix_file(self, file_path):
        return any([file_path.endswith(suffix) for suffix in self.suffixs])

    def read_file_content(self, file_path):
        with open(file_path, "r") as file:
            return file.read()

    def convert_to_source_code(self, file_path):                               
        module_name = file_path
        source_code = self.read_file_content(file_path)            
        return SourceCode(module_name=module_name, source_code=source_code)
    
    def get_source_codes(self) -> Generator[SourceCode, None, None]:
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                file_path = os.path.join(root, file)
                
                if self.is_suffix_file(file_path):
                
                    if self.file_filter is None or self.file_filter(file_path,self.suffixs):
                        print(f"====Processing {file_path}",flush=True)
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