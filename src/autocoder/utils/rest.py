import requests
from bs4 import BeautifulSoup
from typing import List,Dict,Type,Optional
from autocoder.common import SourceCode
import byzerllm
from bs4 import BeautifulSoup
from loguru import logger
import os
from pathlib import Path


class HttpDoc:
    def __init__(self, args, llm: byzerllm.ByzerLLM,urls:Optional[List[str]]=None):
        self.args = args
        temp_urls = self.args.urls.split(",") if not urls else urls
        self.urls = [url.strip() for url in temp_urls if url.strip() != ""]
        self.llm = llm

    @byzerllm.prompt()
    def _extract_main_content(self, url: str, html: str) -> str:
        """    
        ## 任务 

        你的目标是把 HTML 格式的文本内容转换为 Markdown。保持最后生成文档的可阅读性，同时去除广告、导航、版权声明等无关内容,
        如果里面有 html 表格，请将其转换为 Markdown表格。
        
        返回的结果务必要保持完整,不需要给出提取步骤。             
        
        ## 链接
        
        {{ url }}
        
        ## HTML内容

        {{ html }}
        
        ## Markdown内容        
        """

    def is_binary_file(self,filepath):    
        try:
            with open(filepath, 'rb') as file:
                chunk = file.read(1024)  # Read first 1024 bytes
                if b'\x00' in chunk:  # Binary files often contain null bytes
                    return True
                # Attempt to decode as UTF-8 (or any encoding you expect your text files to be in)
                chunk.decode('utf-8')
                return False
        except UnicodeDecodeError:
            return True   

    def get_file_extractor(self):        
        try:
            from llama_index.core.readers.base import BaseReader
            from fsspec import AbstractFileSystem
            from llama_index.core.schema import Document
            from llama_index.core.readers.file.base import get_default_fs
            from llama_index.readers.file import (
                DocxReader,
                EpubReader,
                HWPReader,
                ImageReader,
                IPYNBReader,
                MarkdownReader,
                MboxReader,
                PandasCSVReader,
                PDFReader,
                PptxReader,
                VideoAudioReader,
            )  # pants: no-infer-dep                                
        except ImportError as e:
            raise ImportError(f"`llama-index-readers-file` package not found. {e}")

        default_file_reader_cls: Dict[str, BaseReader] = {
            ".hwp": HWPReader(),
            ".pdf": PDFReader(return_full_document=True),
            ".docx": DocxReader(),
            # ".pptx": PptxReader(),
            # ".ppt": PptxReader(),
            # ".pptm": PptxReader(),
            # ".jpg": ImageReader(),
            # ".png": ImageReader(),
            # ".jpeg": ImageReader(),
            # ".mp3": VideoAudioReader(),
            # ".mp4": VideoAudioReader(),
            # ".csv": PandasCSVReader(),
            ".epub": EpubReader(),            
            ".mbox": MboxReader(),
            ".ipynb": IPYNBReader(),            
        }
        return default_file_reader_cls

    def crawl_urls(self) -> List[SourceCode]:
        source_codes = []        
        for url in self.urls:
            if not url.startswith("http://") and not url.startswith("https://"):
                try:
                 from llama_index.core import SimpleDirectoryReader
                 exts = self.get_file_extractor()
                 documents = []   

                 def process_single_file(file_path: str): 
                    temp_documents = []
                    ext = os.path.splitext(file_path)[1].lower()                    
                    if self.is_binary_file(file_path):
                        logger.warning(f"Skipping binary file: {file_path}")
                        return temp_documents
                    
                    if ext not in exts.keys():                                                
                        main_content = open(file_path, "r").read()
                        source_code = SourceCode(module_name=file_path, source_code=main_content)
                        source_codes.append(source_code)                                   
                    else:
                        temp_documents = SimpleDirectoryReader(input_files=[url],file_extractor=exts).load_data()  
                    return temp_documents                                    

                 if os.path.isdir(url):
                    for root, dirs, files in os.walk(url):
                        dirs[:] = [d for d in dirs if d not in ['.git',"node_modules"]]  # Exclude .git directory
                        for file in files:
                            file_path = os.path.join(root, file)                            
                            documents.extend(process_single_file(file_path))
                    
                 else:
                    documents.extend(process_single_file(url))
                    
                 for document in documents:
                    source_code = SourceCode(module_name=document.metadata["file_path"], source_code=document.get_content())
                    source_codes.append(source_code)

                except ImportError as e:
                    logger.warning(f"Failed to import llama_index. Please install it using 'pip install llama_index' {e}")
                    main_content = open(url, "r").read()
                    source_code = SourceCode(module_name=url, source_code=main_content)
                    source_codes.append(source_code)                                                
            else:    
                response = requests.get(url)
                
                if response.status_code == 200:
                    html_content = self.clean_html_keep_text(response.text)
                    if self.args.urls_use_model and self.llm:  
                        try: 
                            extra_llm_config = {}        
                            if self.args.human_as_model:
                                extra_llm_config["human_as_model"] = True
                            prompt = self._extract_main_content(url, html_content)
                            
                            t = self.llm.chat_oai(conversations=[{
                                "role":"user",
                                "content":prompt
                            }],llm_config={**extra_llm_config})

                            main_content = t[0].output
                        except Exception as e:
                            logger.warning(f"Failed to extract main content from URL: {url}, we will skip this clean step, and use the raw html. Error: {e}")
                            main_content = html_content
                    else:                    
                        main_content = html_content   

                    source_code = SourceCode(module_name=url, source_code=main_content)
                    source_codes.append(source_code)
                else:
                    logger.warning(f"Failed to crawl URL: {url}. Status code: {response.status_code}")

        return source_codes
    
    def clean_html_keep_text(self,html_content: str) -> str:
        soup = BeautifulSoup(html_content, 'html.parser')
            
        tags_to_remove_completely = ['script', 'style']
            
        for tag in tags_to_remove_completely:
            for element in soup.find_all(tag):
                element.decompose()
            
        tags_to_remove_but_keep_text = ['nav', 'footer', 'aside']
        
        for tag in tags_to_remove_but_keep_text:
            for element in soup.find_all(tag):            
                element.replace_with(element.get_text(separator=" ", strip=True))
        
        return soup.get_text(separator=" ", strip=True)