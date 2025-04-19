import os
import traceback
import re
from PIL import Image

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

try:
    import paddlex as paddlex_module
except ImportError:
    paddlex_module = None

import byzerllm
from byzerllm.utils.client import code_utils
from autocoder.utils.llms import get_single_llm
from loguru import logger
from typing import List, Tuple, Optional
from autocoder.common.text import TextSimilarity
from pydantic import BaseModel


class ReplaceInFileTool(BaseModel):
    path: str
    diff: str


class ImageLoader:
    """
    A class for loading and processing images, extracting text and tables from them,
    and converting the content to markdown format.
    """
    
    # 存储不同参数组合的PaddleOCR实例
    _ocr_instances = {}
    
    @staticmethod
    def parse_diff(diff_content: str) -> List[Tuple[str, str]]:
        """
        Parses the diff content into a list of (search_block, replace_block) tuples.
        """
        blocks = []
        lines = diff_content.splitlines(keepends=True)
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            if line.strip() == "<<<<<<< SEARCH":
                i += 1
                search_lines = []
                # Accumulate search block
                while i < n and lines[i].strip() != "=======":
                    search_lines.append(lines[i])
                    i += 1
                if i >= n:
                    logger.warning("Unterminated SEARCH block found in diff content.")
                    break
                i += 1  # skip '======='
                replace_lines = []
                # Accumulate replace block
                while i < n and lines[i].strip() != ">>>>>>> REPLACE":
                    replace_lines.append(lines[i])
                    i += 1
                if i >= n:
                    logger.warning("Unterminated REPLACE block found in diff content.")
                    break
                i += 1  # skip '>>>>>>> REPLACE'

                search_block = ''.join(search_lines)
                replace_block = ''.join(replace_lines)
                blocks.append((search_block, replace_block))
            else:
                i += 1

        if not blocks and diff_content.strip():
            logger.warning(f"Could not parse any SEARCH/REPLACE blocks from diff: {diff_content}")
        return blocks
    
    @staticmethod
    def paddleocr_extract_text(
        file_path,
        lang='ch',
        use_angle_cls=True,
        page_num=10,
        slice_params=None,
        det_model_dir=None,
        rec_model_dir=None,
        **kwargs
    ):
        """
        使用 PaddleOCR 识别文本，支持图片、PDF、超大图像滑动窗口

        Args:
            file_path: 图片或PDF路径
            lang: 语言，默认中文
            use_angle_cls: 是否启用方向分类
            page_num: 识别PDF时的最大页数
            slice_params: 超大图像滑动窗口参数 dict
            det_model_dir: 自定义检测模型路径
            rec_model_dir: 自定义识别模型路径
            kwargs: 其他paddleocr参数
        Returns:
            识别出的纯文本字符串
        """
        if PaddleOCR is None:
            print("paddleocr not installed")
            return ""

        # 创建一个参数的哈希键，用于在缓存中存储OCR实例
        param_key = f"{lang}_{use_angle_cls}_{page_num}_{det_model_dir}_{rec_model_dir}_{hash(frozenset(kwargs.items()) if kwargs else 0)}"
        
        # 检查是否已经有对应参数的OCR实例
        if param_key not in ImageLoader._ocr_instances:
            try:
                # 初始化OCR并缓存
                ImageLoader._ocr_instances[param_key] = PaddleOCR(
                    use_angle_cls=use_angle_cls,
                    lang=lang,
                    page_num=page_num,
                    det_model_dir=det_model_dir,
                    rec_model_dir=rec_model_dir,
                    **kwargs
                )
                logger.info(f"初始化新的PaddleOCR实例，参数：{param_key}")
            except Exception:
                traceback.print_exc()
                return ""
        
        # 使用缓存的OCR实例
        ocr = ImageLoader._ocr_instances[param_key]

        try:
            ext = os.path.splitext(file_path)[1].lower()

            # 处理PDF
            if ext == ".pdf":
                result = ocr.ocr(file_path, cls=True) # result is list of pages, each page is list of lines
                lines = []
                if result and isinstance(result, list):
                    for page in result:
                        if page and isinstance(page, list):
                            for line_info in page: # line_info is [points, (text, confidence)]
                                try:
                                    # Check structure: [points, (text, confidence)]
                                    if isinstance(line_info, (list, tuple)) and len(line_info) == 2 and \
                                       isinstance(line_info[1], (list, tuple)) and len(line_info[1]) >= 1:
                                        txt = line_info[1][0]
                                        if isinstance(txt, str):
                                            lines.append(txt)
                                        else:
                                            logger.warning(f"Extracted text is not a string in PDF: {txt} (type: {type(txt)}). Skipping.")
                                    else:
                                        logger.warning(f"Unexpected line_info structure in PDF: {line_info}. Skipping.")
                                except Exception as e:
                                    logger.warning(f"Error processing line_info in PDF: {line_info}. Error: {e}")
                return "\n".join(lines)

            # 处理图片
            else: # Image processing
                if slice_params is not None:
                    result = ocr.ocr(file_path, cls=True, slice=slice_params)
                else:
                    result = ocr.ocr(file_path, cls=True) # result is [[[points, (text, confidence)], ...]] for single image

                lines = []
                # Standardize handling: PaddleOCR often returns a list containing one item for single images.
                # result = [page_result] where page_result = [[line1_info], [line2_info], ...]
                if result and isinstance(result, list):
                     # Heuristic: Treat 'result' as the list of pages directly.
                     # This handles both single image wrapped in list and multi-page PDFs consistently.
                     page_list = result

                     for page in page_list:
                        if page and isinstance(page, list):
                            for line_info in page: # line_info is [points, (text, confidence)]
                                try:
                                    # Check structure: [points, (text, confidence)]
                                    if isinstance(line_info, (list, tuple)) and len(line_info) == 2 and \
                                       isinstance(line_info[1], (list, tuple)) and len(line_info[1]) >= 1:
                                        txt = line_info[1][0]
                                        if isinstance(txt, str):
                                            lines.append(txt)
                                        else:
                                            # Handle potential nested lists in text: join them? Or log?
                                            if isinstance(txt, list):
                                                processed_txt = " ".join(map(str, txt))
                                                logger.warning(f"Extracted text is a list in Image: {txt}. Joined as: '{processed_txt}'.")
                                                lines.append(processed_txt) # Attempt to join if it's a list of strings/convertibles
                                            else:
                                                logger.warning(f"Extracted text is not a string in Image: {txt} (type: {type(txt)}). Skipping.")
                                    else:
                                        logger.warning(f"Unexpected line_info structure in Image: {line_info}. Skipping.")
                                except Exception as e:
                                    logger.warning(f"Error processing line_info in Image: {line_info}. Error: {e}")
                return "\n".join(lines)
        except Exception:
            traceback.print_exc()
            return ""
    
    @staticmethod
    def paddlex_table_extract_markdown(image_path):
        """
        使用 PaddleX 表格识别pipeline，抽取表格并转换为markdown格式

        Args:
            image_path: 图片路径
        Returns:
            markdown格式的表格字符串
        """
        if paddlex_module is None:
            print("paddlex not installed")
            return ""

        try:
            # 创建 pipeline
            pipeline = paddlex_module.create_pipeline(pipeline='table_recognition')
            # 预测
            outputs = pipeline.predict([image_path])
            if not outputs:
                return ""

            md_results = []
            for res in outputs:
                # 获取HTML表格
                html = None
                try:
                    html = res.to_html() if hasattr(res, "to_html") else None
                except Exception:
                    html = None

                # 如果没有to_html方法，尝试res.print()内容中提取，或跳过
                if html is None:
                    try:
                        from io import StringIO
                        import sys
                        buffer = StringIO()
                        sys_stdout = sys.stdout
                        sys.stdout = buffer
                        res.print()
                        sys.stdout = sys_stdout
                        html = buffer.getvalue()
                    except Exception:
                        html = ""

                # 转markdown
                md = ImageLoader.html_table_to_markdown(html)
                md_results.append(md)

            return "\n\n".join(md_results)
        except Exception:
            traceback.print_exc()
            return ""
    
    @staticmethod
    def html_table_to_markdown(html):
        """
        简单将HTML table转换为markdown table
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            print("BeautifulSoup4 not installed, cannot convert HTML to markdown")
            return ""

        try:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table")
            if table is None:
                return ""

            rows = []
            for tr in table.find_all("tr"):
                cells = tr.find_all(["td", "th"])
                row = [cell.get_text(strip=True) for cell in cells]
                rows.append(row)

            if not rows:
                return ""

            # 生成markdown
            md_lines = []
            header = rows[0]
            md_lines.append("| " + " | ".join(header) + " |")
            md_lines.append("|" + "|".join(["---"] * len(header)) + "|")

            for row in rows[1:]:
                md_lines.append("| " + " | ".join(row) + " |")

            return "\n".join(md_lines)
        except Exception:
            traceback.print_exc()
            return ""

    @staticmethod
    def extract_replace_in_file_tools(response)->List[ReplaceInFileTool]:
        tools = []
        # Pattern to match replace_in_file tool blocks
        pattern = r'<replace_in_file>\s*<path>(.*?)</path>\s*<diff>(.*?)</diff>\s*</replace_in_file>'
        matches = re.finditer(pattern, response, re.DOTALL)
        
        for match in matches:
            path = match.group(1).strip()
            diff = match.group(2).strip()
            tools.append(ReplaceInFileTool(path=path, diff=diff))
        
        return tools        
    
    @staticmethod
    def format_table_in_content(content: str, llm=None) -> str:
        """Format table content from OCR results into markdown format.
        
        Args:
            content: The OCR text content that may contain tables
            llm: The language model to use for formatting
            
        Returns:
            Formatted content with tables converted to markdown
        """    
            
        @byzerllm.prompt()
        def _format_table(content: str)->str:
            '''
            # 表格格式化任务
            
            你是一个专业的OCR后处理专家，擅长将OCR识别出的表格数据转换为规范的Markdown表格。
            
            ## 输入内容分析
            
            OCR识别的表格通常会有以下特点：
            1. 每个单元格可能被识别为单独的一行
            2. 表格的行列结构可能不明显
            3. 可能包含非表格的文本内容
            4. 可能存在多个表格
            
            ## 你的任务
            
            1. 识别内容中的表格数据
            2. 将表格数据转换为标准Markdown格式
            3. 保留非表格的文本内容
            4. 使用replace_in_file工具格式输出结果
            
            ## 输出格式
            
            必须使用以下格式输出结果：
            
            ```
            <replace_in_file>
            <path>content</path>
            <diff>
            <<<<<<< SEARCH
            [原始表格文本，精确匹配]
            =======
            [转换后的Markdown表格]
            >>>>>>> REPLACE
            </diff>
            </replace_in_file>
            ```
            
            ## 示例
            
            原始OCR文本：
            ```
            下面是库存情况：
            产品名称 
            价格 
            库存
            苹果手机 
            8999 352
            华为平板 
            4599 
            128
            小米电视 
            3299 
            89
            可以看到在，整体库存和价格是健康的。
            ```
            
            转换后的输出：
            ```
            <replace_in_file>
            <path>content</path>
            <diff>
            <<<<<<< SEARCH
            产品名称 
            价格 
            库存
            苹果手机 
            8999 352
            华为平板 
            4599 
            128
            小米电视 
            3299 
            89
            =======
            | 产品名称 | 价格 | 库存 |
            |---------|------|------|
            | 苹果手机 | 8999 | 352 |
            | 华为平板 | 4599 | 128 |
            | 小米电视 | 3299 | 89  |
            >>>>>>> REPLACE
            </diff>
            </replace_in_file>
            ```
            
            ## 处理规则
            
            1. 表格识别：
               - 分析行列结构，识别表头和数据行
               - 如果一行中有多个值，可能是一行表格数据
               - 连续的短行可能是表格的单元格
            
            2. Markdown格式：
               - 表头行使用`|`分隔各列
               - 在表头下方添加分隔行`|---|---|---|`
               - 对齐各列数据
               - 保持原始数据的完整性
            
            3. 多表格处理：
               - 为每个表格创建单独的replace_in_file块
               - 保持表格在原文中的相对位置
            
            4. 非表格内容：
               - 保留原始格式
               - 不要修改非表格文本
            
            ## 处理以下内容
            
            {{content}}
            '''
        
        # Run the prompt with the provided content
        tool_response = _format_table.with_llm(llm).run(content)                    
        
        # Extract tools from the response
        tools = ImageLoader.extract_replace_in_file_tools(tool_response)    
        
        # Process each tool to apply the replacements
        formatted_content = content
        for tool in tools:
            # For in-memory content replacement (not actual file modification)            
            # Parse the diff to get search/replace blocks
            blocks = ImageLoader.parse_diff(tool.diff)
            # Apply each replacement to the content                
            for search_block, replace_block in blocks:
                # Check if the search_block exists in the content
                if search_block in formatted_content:
                    # Replace and verify the replacement occurred
                    new_content = formatted_content.replace(search_block, replace_block)
                    if new_content == formatted_content:
                        logger.warning(f"Replacement failed despite search block found. Search block length: {len(search_block)}")
                        print(f"\n=== FAILED SEARCH BLOCK ===\n{search_block}\n=== END FAILED SEARCH BLOCK ===\n")
                    formatted_content = new_content
                else:
                    # Fallback to similarity matching when exact match fails
                    logger.warning(f"Search block not found in content. Trying similarity matching. Search block length: {len(search_block)}")
                    print(f"\n=== NOT FOUND SEARCH BLOCK (trying similarity) ===\n{search_block}\n=== END NOT FOUND SEARCH BLOCK ===\n")
                    
                    # Use TextSimilarity to find the best matching window
                    similarity, best_window = TextSimilarity(search_block, formatted_content).get_best_matching_window()
                    similarity_threshold = 0.8  # Can be adjusted based on needs
                    
                    if similarity > similarity_threshold:
                        logger.info(f"Found similar block with similarity {similarity:.2f}")
                        print(f"\n=== SIMILAR BLOCK FOUND (similarity: {similarity:.2f}) ===\n{best_window}\n=== END SIMILAR BLOCK ===\n")
                        formatted_content = formatted_content.replace(best_window, replace_block, 1)
                    else:
                        logger.warning(f"No similar block found. Best similarity: {similarity:.2f}")
        
        return formatted_content
    
    @staticmethod
    def extract_text_from_image(
        image_path: str,
        llm,
        engine: str = "vl",
        product_mode: str = "lite",
        paddle_kwargs: dict = None
    ) -> str:
        """
        识别图片或PDF中的所有文本内容，包括表格（以markdown table格式）

        Args:
            image_path: 图片或PDF路径
            llm: LLM对象或字符串（模型名）
            engine: 选择识别引擎
                - "vl": 视觉语言模型
                - "paddle": PaddleOCR
                - "paddle_table": PaddleX表格识别
            product_mode: get_single_llm的参数
            paddle_kwargs: dict，传递给PaddleOCR的参数
        Returns:
            markdown内容字符串
        """
        if isinstance(llm, str):
            llm = get_single_llm(llm, product_mode=product_mode)

        markdown_content = ""

        if engine == "vl":
            try:
                vl_model = llm.get_sub_client("vl_model") if llm.get_sub_client("vl_model") else llm

                @byzerllm.prompt()
                def analyze_image(image_path):
                    """
                    {{ image }}
                    你是一名图像理解专家，请识别这张图片中的所有内容，优先识别文字和表格。
                    对于普通文字，输出为段落文本。
                    对于表格截图，转换成markdown table格式输出。
                    请根据内容顺序，整合成一份markdown文档。
                    只返回markdown内容，不要添加额外解释。
                    """
                    image = byzerllm.Image.load_image_from_path(image_path)
                    return {"image": image}

                result = analyze_image.with_llm(vl_model).run(image_path)
                md_blocks = code_utils.extract_code(result, language="markdown")
                if md_blocks:
                    markdown_content = md_blocks[-1][1]
                else:
                    markdown_content = result.strip()
                if not markdown_content:
                    raise ValueError("Empty markdown from vl_model")
                return markdown_content

            except Exception:
                traceback.print_exc()
                return ""

        elif engine == "paddle":
            if paddle_kwargs is None:
                paddle_kwargs = {}

            markdown_content = ImageLoader.paddleocr_extract_text(image_path, **paddle_kwargs)
            return markdown_content

        elif engine == "paddle_table":
            markdown_content = ImageLoader.paddlex_table_extract_markdown(image_path)
            return markdown_content

        else:
            print(f"Unknown engine type: {engine}. Supported engines are 'vl', 'paddle', and 'paddle_table'.")
            return ""
    
    @staticmethod
    def image_to_markdown(
        image_path: str,
        llm,
        engine: str = "paddle",
        product_mode: str = "lite",
        paddle_kwargs: dict = None
    ) -> str:
        """
        识别图片或PDF内容，生成markdown文件

        Args:
            image_path: 文件路径
            llm: LLM对象或字符串
            engine: 'vl'、'paddle'或'paddle_table'
            product_mode: LLM参数
            paddle_kwargs: dict，传递给PaddleOCR参数
        Returns:
            markdown内容字符串
        """
        logger.info(f"image_path: {image_path} engine: {engine} product_mode: {product_mode} paddle_kwargs: {paddle_kwargs}")        

        # 新增：如果 engine 为 paddle 且 PaddleOCR 为 None，直接返回空字符串
        if engine == "paddle" and PaddleOCR is None:
            logger.warning("PaddleOCR 未安装，无法识别图片内容，直接返回空字符串。")
            return ""

        md_content = ImageLoader.extract_text_from_image(
            image_path,
            llm,
            engine=engine,
            product_mode=product_mode,
            paddle_kwargs=paddle_kwargs
        )
            
        # Get directory and filename separately
        dir_name = os.path.dirname(image_path)
        file_name = os.path.basename(image_path)
        base_name = os.path.splitext(file_name)[0]
        # Create new path with dot before filename
        md_path = os.path.join(dir_name, f".{base_name}.md")
        try:
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(md_content)
        except Exception:
            traceback.print_exc()

        return md_content

