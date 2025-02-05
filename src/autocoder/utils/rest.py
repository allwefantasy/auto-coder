import requests
from bs4 import BeautifulSoup
from typing import List,Dict,Union,Optional
from autocoder.common import SourceCode
import byzerllm
from loguru import logger
import os
from pathlib import Path
from autocoder.common import files as FileUtils
import traceback
from autocoder.rag.loaders import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_ppt,
    extract_text_from_excel
)

class HttpDoc:
    def __init__(self, args, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],urls:Optional[List[str]]=None):
        self.args = args
        urls_from_args = self.args.urls
        if urls_from_args:
            if isinstance(urls_from_args, str):
                _urls = urls_from_args.split(",")
            else:
                _urls = urls_from_args
        temp_urls = _urls if not urls else urls
        self.urls = [url.strip() for url in temp_urls if url.strip() != ""]
        self.llm = llm

    @byzerllm.prompt()
    def _extract_main_content(self, url: str, html: str) -> str:
        """    
        ## 任务 

        你的目标是把 HTML 格式的文本内容转换为 Markdown。保持最后生成文档的可阅读性，同时去除广告、导航、版权声明等非主体内容内容,
        如果里面有 html 表格，请将其转换为 Markdown表格。
        
        返回的结果务必要保持完整,不需要给出提取步骤。             
        
        ## 链接
        
        {{ url }}
        
        ## HTML内容

        {{ html }}
                
        输出的内容请以 "<MARKER></MARKER> 标签对包裹。
        """    

    def _process_local_file(self, file_path: str) -> List[SourceCode]:
        """统一处理本地文件，返回标准化的 SourceCode 列表"""
        results = []
        try:
            ext = os.path.splitext(file_path)[1].lower()
                        
            # 分发到不同 loader
            if ext == '.pdf':
                content = extract_text_from_pdf(file_path)
                results.append(SourceCode(module_name=file_path, source_code=content))
            elif ext == '.docx':
                content = extract_text_from_docx(file_path)
                results.append(SourceCode(module_name=file_path, source_code=content))
            elif ext in ('.pptx', '.ppt'):
                for slide_id, slide_content in extract_text_from_ppt(file_path):
                    results.append(SourceCode(module_name=f"{file_path}#{slide_id}", source_code=slide_content))
            elif ext in ('.xlsx', '.xls'):
                for sheet_name, sheet_content in extract_text_from_excel(file_path):
                    results.append(SourceCode(module_name=f"{file_path}#{sheet_name}", source_code=sheet_content))
            else:
                content = FileUtils.read_file(file_path)
                results.append(SourceCode(module_name=file_path, source_code=content))

        except Exception as e:
            logger.error(f"Failed to process {file_path}: {str(e)}")
            traceback.print_exc()
        
        return results

    def crawl_urls(self) -> List[SourceCode]:
        source_codes = []
        for url in self.urls:
            if not url.startswith(("http://", "https://")):
                try:
                    if os.path.isdir(url):
                        for root, _, files in os.walk(url, followlinks=True):
                            for file in files:
                                source_codes.extend(self._process_local_file(os.path.join(root, file)))
                    else:
                        source_codes.extend(self._process_local_file(url))
                except Exception as e:
                    logger.error(f"Error accessing path {url}: {str(e)}")
            else:
                if self.args.urls_use_model:
                    from autocoder.common.screenshots import gen_screenshots
                    from autocoder.common.anything2images import Anything2Images

                    if not self.llm:
                        raise ValueError("Please provide a valid model instance to use for URL content extraction.")
                    
                    if not self.llm.get_sub_client("vl_model"):
                        raise ValueError("Please provide a valid vl_model to use for URL content extraction.")
                    
                    image_path = gen_screenshots(url=url,image_dir="screenshots")                    
                    htmler = Anything2Images(self.llm,self.args)
                    html = htmler.to_html_from_images(images=[image_path])
                    try:
                        main_content = self._extract_main_content.with_llm(self.llm).with_response_markers(["<MARKER>", "</MARKER>"]).run(url=url,html=html)
                    except Exception as e:
                        logger.warning(f"Failed to extract main content from URL: {url}. {e}")                        
                        main_content = html 
                    source_code = SourceCode(module_name=url, source_code=main_content)
                    source_codes.append(source_code)    
                else:    
                    response = requests.get(url)                    
                    if response.status_code == 200:
                        html_content = self.clean_html_keep_text(response.text)                        
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