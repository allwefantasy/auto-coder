from io import BytesIO
import docx2txt
from autocoder.utils._markitdown import MarkItDown
import traceback

def extract_text_from_docx_old(docx_path):
    with open(docx_path, "rb") as f:
        docx_content = f.read()
    docx_file = BytesIO(docx_content)
    text = docx2txt.process(docx_file)
    return text


def extract_text_from_docx(docx_path):
    try:
        md_converter = MarkItDown()
        result = md_converter.convert(docx_path)
        return result.text_content
    except (BaseException, Exception) as e:
        traceback.print_exc()
        return extract_text_from_docx_old(docx_path)
