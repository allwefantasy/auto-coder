from autocoder.common import SourceCode
from autocoder.rag.token_counter import count_tokens_worker, count_tokens
from autocoder.rag.loaders.pdf_loader import extract_text_from_pdf
from autocoder.rag.loaders.docx_loader import extract_text_from_docx
from autocoder.rag.loaders.excel_loader import extract_text_from_excel
from autocoder.rag.loaders.ppt_loader import extract_text_from_ppt
from typing import List, Tuple
import time
from loguru import logger
import traceback

def process_file_in_multi_process(
    file_info: Tuple[str, str, float]
) -> List[SourceCode]:
    start_time = time.time()
    file_path, relative_path, _, _ = file_info
    try:
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        if not os.access(file_path, os.R_OK):
            logger.error(f"Permission denied: {file_path}")
            return []

        # Process different file types
        if file_path.endswith(".pdf"):            
            try:
                content = extract_text_from_pdf(file_path)
                if not content:
                    logger.warning(f"Empty content extracted from PDF: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=file_path,
                        source_code=content,
                        tokens=count_tokens_worker(content),
                    )
                ]
            except Exception as e:
                logger.error(f"PDF processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        elif file_path.endswith(".docx"):            
            try:
                content = extract_text_from_docx(file_path)
                if not content:
                    logger.warning(f"Empty content extracted from DOCX: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}",
                        source_code=content,
                        tokens=count_tokens_worker(content),
                    )
                ]
            except Exception as e:
                logger.error(f"DOCX processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            try:
                sheets = extract_text_from_excel(file_path)
                if not sheets:
                    logger.warning(f"Empty content extracted from Excel: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}#{sheet[0]}",
                        source_code=sheet[1],
                        tokens=count_tokens_worker(sheet[1]),
                    )
                    for sheet in sheets
                ]
            except Exception as e:
                logger.error(f"Excel processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        elif file_path.endswith(".pptx"):
            try:
                slides = extract_text_from_ppt(file_path)
                if not slides:
                    logger.warning(f"Empty content extracted from PPT: {file_path}")
                    return []
                content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}",
                        source_code=content,
                        tokens=count_tokens_worker(content),
                    )
                ]
            except Exception as e:
                logger.error(f"PPT processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content:
                    logger.warning(f"Empty content read from file: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}",
                        source_code=content,
                        tokens=count_tokens_worker(content),
                    )
                ]
            except Exception as e:
                logger.error(f"Text file processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        logger.info(f"Successfully loaded file {file_path} in {time.time() - start_time:.2f}s")
        return v
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {str(e)}")
        traceback.print_exc()
        return []


def process_file_local(file_path: str) -> List[SourceCode]:
    start_time = time.time()
    try:
        # Check if file exists and is accessible
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return []
        if not os.access(file_path, os.R_OK):
            logger.error(f"Permission denied: {file_path}")
            return []

        # Process different file types
        if file_path.endswith(".pdf"):            
            try:
                content = extract_text_from_pdf(file_path)
                if not content:
                    logger.warning(f"Empty content extracted from PDF: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=file_path,
                        source_code=content,
                        tokens=count_tokens(content),
                    )
                ]
            except Exception as e:
                logger.error(f"PDF processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        elif file_path.endswith(".docx"):            
            try:
                content = extract_text_from_docx(file_path)
                if not content:
                    logger.warning(f"Empty content extracted from DOCX: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}",
                        source_code=content,
                        tokens=count_tokens(content),
                    )
                ]
            except Exception as e:
                logger.error(f"DOCX processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            try:
                sheets = extract_text_from_excel(file_path)
                if not sheets:
                    logger.warning(f"Empty content extracted from Excel: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}#{sheet[0]}",
                        source_code=sheet[1],
                        tokens=count_tokens(sheet[1]),
                    )
                    for sheet in sheets
                ]
            except Exception as e:
                logger.error(f"Excel processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        elif file_path.endswith(".pptx"):
            try:
                slides = extract_text_from_ppt(file_path)
                if not slides:
                    logger.warning(f"Empty content extracted from PPT: {file_path}")
                    return []
                content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}",
                        source_code=content,
                        tokens=count_tokens(content),
                    )
                ]
            except Exception as e:
                logger.error(f"PPT processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        else:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if not content:
                    logger.warning(f"Empty content read from file: {file_path}")
                    return []
                v = [
                    SourceCode(
                        module_name=f"##File: {file_path}",
                        source_code=content,
                        tokens=count_tokens(content),
                    )
                ]
            except Exception as e:
                logger.error(f"Text file processing error for {file_path}: {str(e)}")
                traceback.print_exc()
                return []

        logger.info(f"Successfully loaded file {file_path} in {time.time() - start_time:.2f}s")
        return v
    except Exception as e:
        logger.error(f"Unexpected error processing file {file_path}: {str(e)}")
        traceback.print_exc()
        return []