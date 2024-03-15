import requests
from bs4 import BeautifulSoup
from typing import List
from autocoder.common import SourceCode
import byzerllm

class HttpDoc:
    def __init__(self, urls: List[str], llm: byzerllm.ByzerLLM):
        self.urls = urls
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

    def crawl_urls(self) -> List[SourceCode]:
        source_codes = []
        for url in self.urls:
            response = requests.get(url)
            
            if response.status_code == 200:
                html_content = response.text   
                if self.llm:                             
                    main_content = self._extract_main_content(url, html_content)
                else:                    
                    main_content = response.text   

                source_code = SourceCode(module_name=url, source_code=main_content)
                source_codes.append(source_code)
            else:
                print(f"Failed to crawl URL: {url}. Status code: {response.status_code}")

        return source_codes