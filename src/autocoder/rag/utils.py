from autocoder.common import SourceCode
from autocoder.rag.token_counter import count_tokens_worker, count_tokens
from autocoder.rag.loaders.pdf_loader import extract_text_from_pdf
from autocoder.rag.loaders.docx_loader import extract_text_from_docx
from autocoder.rag.loaders.excel_loader import extract_text_from_excel 
from autocoder.rag.loaders.ppt_loader import extract_text_from_ppt
from autocoder.rag.loaders.image_loader import ImageLoader
from typing import List, Tuple, Optional, Union
import time
from loguru import logger
import traceback
from byzerllm import SimpleByzerLLM, ByzerLLM
from autocoder.utils.llms import get_single_llm


def process_file_in_multi_process(
    file_info: Tuple[str, str, float, str],
    llm: Optional[Union[ByzerLLM, SimpleByzerLLM, str]] = None,
    product_mode="lite",
) -> List[SourceCode]:
    if llm and isinstance(llm, str):
        llm = get_single_llm(llm,product_mode)

    start_time = time.time()
    file_path, relative_path, _, _ = file_info    
    try:
        if file_path.endswith(".pdf"):
            content = extract_text_from_pdf(file_path, llm, product_mode)
            v = [
                SourceCode(
                    module_name=file_path,
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        elif file_path.endswith(".docx"):
            content = extract_text_from_docx(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            sheets = extract_text_from_excel(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}#{sheet[0]}",
                    source_code=sheet[1],
                    tokens=count_tokens_worker(sheet[1]),
                )
                for sheet in sheets
            ]
        elif file_path.endswith(".pptx"):
            slides = extract_text_from_ppt(file_path)
            content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            content = ImageLoader.image_to_markdown(file_path, llm=llm, product_mode=product_mode)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        logger.info(f"Load file {file_path} in {time.time() - start_time}")
        return v
    except (BaseException, Exception) as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return []


def process_file_local(
    file_path: str,
    llm: Optional[Union[ByzerLLM, SimpleByzerLLM, str]] = None,
    product_mode="lite",
) -> List[SourceCode]:
    start_time = time.time()
    if llm and isinstance(llm, str):
        llm = get_single_llm(llm,product_mode)
    try:
        if file_path.endswith(".pdf"):
            content = extract_text_from_pdf(file_path, llm, product_mode)
            v = [
                SourceCode(
                    module_name=file_path,
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        elif file_path.endswith(".docx"):
            content = extract_text_from_docx(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            sheets = extract_text_from_excel(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}#{sheet[0]}",
                    source_code=sheet[1],
                    tokens=count_tokens(sheet[1]),
                )
                for sheet in sheets
            ]
        elif file_path.endswith(".pptx"):
            slides = extract_text_from_ppt(file_path)
            content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        elif file_path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif")):
            content = ImageLoader.image_to_markdown(file_path, llm=llm, product_mode=product_mode)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        logger.info(f"Load file {file_path} in {time.time() - start_time}")
        return v
    except (BaseException, Exception) as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return []
