import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Generator, List, Tuple
from autocoder.common import SourceCode
from autocoder.rag.loaders import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_excel,
    extract_text_from_ppt,
)
from loguru import logger

def retrieve_documents(path: str, ignore_spec, required_exts: list) -> Generator[SourceCode, None, None]:
    def get_all_files() -> List[Tuple[str, str]]:
        all_files = []
        for root, dirs, files in os.walk(path):
            # 过滤掉隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            # 应用 .serveignore 或 .gitignore 规则
            if ignore_spec:
                relative_root = os.path.relpath(root, path)
                dirs[:] = [
                    d
                    for d in dirs
                    if not ignore_spec.match_file(os.path.join(relative_root, d))
                ]
                files = [
                    f
                    for f in files
                    if not ignore_spec.match_file(os.path.join(relative_root, f))
                ]

            for file in files:
                if required_exts and not any(file.endswith(ext) for ext in required_exts):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)
                all_files.append((file_path, relative_path))

        return all_files

    def process_file(file_info: Tuple[str, str]) -> List[SourceCode]:
        file_path, relative_path = file_info
        try:
            if file_path.endswith(".pdf"):
                with open(file_path, "rb") as f:
                    content = extract_text_from_pdf(f.read())
                return [SourceCode(module_name=file_path, source_code=content)]
            elif file_path.endswith(".docx"):
                with open(file_path, "rb") as f:
                    content = extract_text_from_docx(f.read())
                return [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
            elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                sheets = extract_text_from_excel(file_path)
                return [SourceCode(module_name=f"##File: {file_path}#{sheet[0]}", source_code=sheet[1]) for sheet in sheets]
            elif file_path.endswith(".pptx"):
                slides = extract_text_from_ppt(file_path)
                content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
                return [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return []

    all_files = get_all_files()
    num_threads = min(32, os.cpu_count() * 2)

    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        future_to_file = {executor.submit(process_file, file_info): file_info for file_info in all_files}
        for future in as_completed(future_to_file):
            file_info = future_to_file[future]
            try:
                results = future.result()
                for result in results:
                    yield result
            except Exception as e:
                logger.error(f"Error processing file {file_info[0]}: {str(e)}")