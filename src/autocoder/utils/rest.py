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
    def __init__(self, urls: List[str], llm: byzerllm.ByzerLLM):
        self.urls = [url.strip() for url in urls if url.strip() != ""]
        self.llm = llm

    @byzerllm.prompt(lambda self:self.llm, render="jinja2")
    def _extract_main_content(self, url: str, html: str) -> str:
        """
        链接：{{ url }}
        
        HTML内容：
        {{ html }}
        
        请从上面的HTML内容中提取正文内容,去除广告、导航、版权声明等无关内容,如果是html表格之类的，则可以转化markdown表格或者List格式。
        返回提取的结果即可,不需要给出提取步骤。
        """

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
            
            class TextFileReader(BaseReader):
                """TextFile parser."""

                def __init__(self) -> None:
                    pass

                def load_data(
                    self,
                    file: Path,
                    extra_info: Optional[Dict] = None,
                    fs: Optional[AbstractFileSystem] = None,
                ) -> List[Document]:
                    """Parse file."""                    
                    fs = fs or get_default_fs()                    
                    with fs.open(file, "r") as fp:
                        metadata = {"file_name": fp.name, "file_path": fp.name}                        
                        return [Document(text=fp.read(), metadata=metadata)]
        
        except ImportError as e:
            raise ImportError(f"`llama-index-readers-file` package not found. {e}")

        default_file_reader_cls: Dict[str, BaseReader] = {
            ".hwp": HWPReader(),
            ".pdf": PDFReader(return_full_document=True),
            ".docx": DocxReader(),
            # ".pptx": PptxReader(),
            # ".ppt": PptxReader(),
            # ".pptm": PptxReader(),
            ".jpg": ImageReader(),
            ".png": ImageReader(),
            ".jpeg": ImageReader(),
            # ".mp3": VideoAudioReader(),
            # ".mp4": VideoAudioReader(),
            ".csv": PandasCSVReader(),
            ".epub": EpubReader(),
            ".md": MarkdownReader(),
            ".mbox": MboxReader(),
            ".ipynb": IPYNBReader(),
            ".py": TextFileReader(),
            ".java": TextFileReader(),
            ".scala": TextFileReader(),
            ".go": TextFileReader(),
            ".rs": TextFileReader(),
            ".ts": TextFileReader(),
            ".js": TextFileReader(),
            ".vue": TextFileReader(),
            ".jsx": TextFileReader(),
            ".txt": TextFileReader(),
            ".css": TextFileReader(),
        }
        return default_file_reader_cls

    def crawl_urls(self) -> List[SourceCode]:
        source_codes = []
        for url in self.urls:
            if not url.startswith("http://") or not url.startswith("https://"):
                try:
                 from llama_index.core import SimpleDirectoryReader
                 if os.path.isdir(url):
                    documents = SimpleDirectoryReader(input_dir=url,file_extractor=self.get_file_extractor()).load_data()                    
                 else:
                    documents = SimpleDirectoryReader(input_files=[url],file_extractor=self.get_file_extractor()).load_data()                    
                    
                 for document in documents:
                    source_code = SourceCode(module_name=document.metadata["file_name"], source_code=document.get_content())
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
                    if self.llm:  
                        try:
                            main_content = self._extract_main_content(url, html_content)
                        except Exception as e:
                            logger.warning(f"Failed to extract main content from URL: {url}. Error: {e}")
                            main_content = html_content
                    else:                    
                        main_content = response.text   

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