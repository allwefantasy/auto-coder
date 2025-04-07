from autocoder.common import SourceCode, AutoCoderArgs
from autocoder import common as FileUtils
from autocoder.utils.rest import HttpDoc
import os
from typing import Optional, Generator, List, Dict, Any, Callable
from git import Repo
import byzerllm
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


class SuffixProject:

    def __init__(
        self,
        args: AutoCoderArgs,
        llm: Optional[byzerllm.ByzerLLM] = None,
        file_filter=None,
    ):
        self.args = args
        self.directory = args.source_dir
        self.git_url = args.git_url
        self.target_file = args.target_file
        self.project_type = args.project_type
        self.suffixs = [
            suffix.strip() if suffix.startswith(".") else f".{suffix.strip()}"
            for suffix in self.project_type.split(",") if suffix.strip()
        ]
        self.file_filter = file_filter
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
            ".vscode",
            "actions",
            ".idea",
            "venv",
            ".next"
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

    def is_suffix_file(self, file_path):
        return any([file_path.endswith(suffix) for suffix in self.suffixs])

    def read_file_content(self, file_path):
        return FileUtils.read_file(file_path)

    def convert_to_source_code(self, file_path):
        module_name = file_path
        try:
            source_code = self.read_file_content(file_path)
        except Exception as e:
            logger.warning(f"Failed to read file: {file_path}. Error: {str(e)}")
            return None
        return SourceCode(module_name=module_name, source_code=source_code)

    def get_source_codes(self) -> Generator[SourceCode, None, None]:
        for root, dirs, files in os.walk(self.directory,followlinks=True):
            dirs[:] = [d for d in dirs if d not in self.default_exclude_dirs]
            for file in files:
                file_path = os.path.join(root, file)
                if self.is_suffix_file(file_path):
                    if self.should_exclude(file_path):
                        continue
                    if self.file_filter is None or self.file_filter(
                        file_path, self.suffixs
                    ):
                        source_code = self.convert_to_source_code(file_path)
                        if source_code is not None:
                            yield source_code

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
                
        console = Console()
        console.print(f"\n[bold blue]Starting RAG search for:[/bold blue] {self.args.query}")
            
        from autocoder.rag.rag_entry import RAGFactory
        rag = RAGFactory.get_rag(self.llm, self.args, "")
        docs = rag.search(self.args.query)
        for doc in docs:
            doc.tag = "RAG"
 
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

    def run(self):
        if self.git_url is not None:
            self.clone_repository()

        if self.target_file:
            with open(self.target_file, "w",encoding="utf-8") as file:
                for code in self.get_source_codes():
                    self.sources.append(code)
                    file.write(f"##File: {code.module_name}\n")
                    file.write(f"{code.source_code}\n\n")

                for code in self.get_rest_source_codes():
                    self.sources.append(code)
                    file.write(f"##File: {code.module_name}\n")
                    file.write(f"{code.source_code}\n\n")

                for code in self.get_search_source_codes():
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
