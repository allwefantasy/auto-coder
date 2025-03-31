from autocoder.common import SourceCode, AutoCoderArgs
from autocoder import common as FileUtils
from autocoder.utils.rest import HttpDoc
import os
from typing import Optional, Generator, List, Dict, Any
from git import Repo
import ast
import importlib
import byzerllm
import importlib
import pkgutil
from autocoder.common.search import Search, SearchEngine

from loguru import logger
import re
from pydantic import BaseModel, Field
from rich.console import Console
import json
from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
from autocoder.common import files as FileUtils

class RegPattern(BaseModel):
    pattern: str = Field(
        ...,
        title="Pattern",
        description="The regex pattern can be used by `re.search` in python.",
    )


class Level1PyProject:

    def __init__(self, script_path, package_name):
        self.script_path = script_path
        self.package_name = package_name

    def get_imports_from_script(self, file_path):
        script = ""
        script = FileUtils.read_file(file_path)
        tree = ast.parse(script, filename=file_path)

        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        return imports, script

    def filter_imports(self, imports, package_name):
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

    def fetch_source_code(self, import_name):
        spec = importlib.util.find_spec(import_name)
        if spec and spec.origin:
            return FileUtils.read_file(spec.origin)
        return None

    @byzerllm.prompt(render="jinja")
    def auto_implement(self, instruction: str, sources: List[Dict[str, Any]]) -> str:
        """
        {% for source in sources %}
        #Module:{{ source.module_name }}
        {{ source.source_code }}
        {% endfor %}
        """
        pass

    def run(self):
        imports, script = self.get_imports_from_script(self.script_path)
        filtered_imports = self.filter_imports(imports, self.package_name)
        sources = []

        for import_name in filtered_imports:
            source_code = self.fetch_source_code(import_name)
            if source_code:
                sources.append(
                    SourceCode(module_name=import_name, source_code=source_code)
                )
            else:
                print(f"Could not fetch source code for {import_name}.")

        sources.append(SourceCode(module_name="script", source_code=script))

        sources = [source.dict() for source in sources]
        return self.auto_implement(instruction="", sources=sources)


class PyProject:

    def __init__(self, args: AutoCoderArgs, llm: Optional[byzerllm.ByzerLLM] = None):
        self.args = args
        self.directory = args.source_dir
        self.git_url = args.git_url
        self.target_file = args.target_file
        self.sources = []
        self.llm = llm
        self.exclude_files = args.exclude_files
        self.exclude_patterns = self.parse_exclude_files(self.exclude_files)
        self.default_exclude_dirs = [
            ".git",
            ".svn",
            ".hg",
            "build",
            "dist",
            "__pycache__",
            "node_modules",
            ".auto-coder",
            "actions",
            ".vscode",
            ".idea",
            "venv",
        ]

    @byzerllm.prompt()
    def generate_regex_pattern(self, desc: str) -> str:
        """
        根据下面的描述生成一个正则表达式，要符合python re.compile 库的要求。

        {{ desc }}

        最后生成的正则表达式要在<REGEX></REGEX>标签对里。
        """

    def extract_regex_pattern(self, regex_block: str) -> str:
        pattern = re.search(r"<REGEX>(.*)</REGEX>", regex_block, re.DOTALL)
        if pattern is None:
            logger.warning(
                "No regex pattern found in the generated block:\n {regex_block}"
            )
            raise None
        return pattern.group(1)

    def parse_exclude_files(self, exclude_files):
        if not exclude_files:
            return []

        if isinstance(exclude_files, str):
            exclude_files = [exclude_files]

        exclude_patterns = []
        for pattern in exclude_files:
            if pattern.startswith("regex://"):
                pattern = pattern[8:]
                exclude_patterns.append(re.compile(pattern))
            elif pattern.startswith("human://"):
                pattern = pattern[8:]
                v = (
                    self.generate_regex_pattern.with_llm(self.llm)
                    .with_extractor(self.extract_regex_pattern)
                    .run(desc=pattern)
                )
                if not v:
                    raise ValueError("Fail to generate regex pattern, try again.")
                logger.info(f"Generated regex pattern: {v}")
                exclude_patterns.append(re.compile(v))
            else:
                raise ValueError(
                    "Invalid exclude_files format. Expected 'regex://<pattern>' or 'human://<description>' "
                )
        return exclude_patterns

    def should_exclude(self, file_path):
        for pattern in self.exclude_patterns:
            if pattern.search(file_path):                
                return True
        return False

    def output(self):
        with open(self.target_file, "r",encoding="utf-8") as file:
            return file.read()

    def is_python_file(self, file_path):
        return file_path.endswith(".py")

    def read_file_content(self, file_path):
        if self.args.auto_merge == "strict_diff":
            result = []
            for line_number, line in FileUtils.read_file_with_line_numbers(file_path,line_number_start=1):
                result.append(f"{line_number}:{line}")
            return "\n".join(result)

        return FileUtils.read_file(file_path)

    def convert_to_source_code(self, file_path):
        module_name = file_path
        try:
            source_code = self.read_file_content(file_path)
        except Exception as e:
            logger.warning(f"Failed to read file: {file_path}. Error: {str(e)}")
            return None
        return SourceCode(module_name=module_name, source_code=source_code)

    def get_package_source_codes(
        self, package_name: str
    ) -> Generator[SourceCode, None, None]:
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
                    source_code.tag = "PACKAGE"
                    yield source_code
        except ModuleNotFoundError:
            print(f"Package {package_name} not found.")

    def get_rest_source_codes(self) -> Generator[SourceCode, None, None]:
        if self.args.urls:
            urls = self.args.urls
            if isinstance(self.args.urls, str):
                urls = self.args.urls.split(",")
            http_doc = HttpDoc(args=self.args, llm=self.llm, urls=urls)
            sources = http_doc.crawl_urls()
            for source in sources:
                source.tag = "REST"
            return sources
        return []

    def get_rag_source_codes(self):
        if not self.args.enable_rag_search and not self.args.enable_rag_context:
            return []
                    
        else:
            console = Console()
            console.print(f"\n[bold blue]Starting RAG search for:[/bold blue] {self.args.query}")
            
        from autocoder.rag.rag_entry import RAGFactory
        rag = RAGFactory.get_rag(self.llm, self.args, "")
        docs = rag.search(self.args.query)
        for doc in docs:
            doc.tag = "RAG"                    
        else:
            console = Console()
            console.print(f"[bold green]Found {len(docs)} relevant documents[/bold green]")
            
        return docs

    def get_search_source_codes(self):
        temp = self.get_rag_source_codes()
        if self.args.search_engine and self.args.search_engine_token:
            if self.args.search_engine == "bing":
                search_engine = SearchEngine.BING
            else:
                search_engine = SearchEngine.GOOGLE

            searcher = Search(
                args=self.args,
                llm=self.llm,
                search_engine=search_engine,
                subscription_key=self.args.search_engine_token,
            )
            search_query = self.args.search or self.args.query
            search_context = searcher.answer_with_the_most_related_context(search_query)
            return temp + [
                SourceCode(
                    module_name="SEARCH_ENGINE",
                    source_code=search_context,
                    tag="SEARCH",
                )
            ]
        return temp + []

    def get_source_codes(self) -> Generator[SourceCode, None, None]:
        for root, dirs, files in os.walk(self.directory,followlinks=True):
            dirs[:] = [d for d in dirs if d not in self.default_exclude_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                if self.should_exclude(file_path):
                    continue
                if self.is_python_file(file_path):
                    source_code = self.convert_to_source_code(file_path)
                    if source_code is not None:
                        yield source_code

    @byzerllm.prompt()
    def get_simple_directory_structure(self) -> str:
        """
        当前项目目录结构：
        1. 项目根目录： {{ directory }}
        2. 项目子目录/文件列表：
        {{ structure }}
        """
        structure = []
        for source_code in self.get_source_codes():
            relative_path = os.path.relpath(source_code.module_name, self.directory)
            structure.append(relative_path)

        subs = "\n".join(sorted(structure))
        return {"directory": self.directory, "structure": subs}

    @byzerllm.prompt()
    def get_tree_like_directory_structure(self) -> str:
        """
        当前项目目录结构：
        1. 项目根目录： {{ directory }}
        2. 项目子目录/文件列表(类似tree 命令输出)：
        {{ structure }}
        """
        structure_dict = {}
        for source_code in self.get_source_codes():
            relative_path = os.path.relpath(source_code.module_name, self.directory)
            parts = relative_path.split(os.sep)
            current_level = structure_dict
            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

        def generate_tree(d, indent=""):
            tree = []
            for k, v in d.items():
                if v:
                    tree.append(f"{indent}{k}/")
                    tree.extend(generate_tree(v, indent + "    "))
                else:
                    tree.append(f"{indent}{k}")
            return tree

        return {
            "structure": "\n".join(generate_tree(structure_dict)),
            "directory": self.directory,
        }

    def run(self, packages: List[str] = []):
        if self.git_url is not None:
            self.clone_repository()

        if self.target_file:
            with open(self.target_file, "w",encoding="utf-8") as file:

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
