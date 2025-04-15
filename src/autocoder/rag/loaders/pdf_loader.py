from io import BytesIO
from pypdf import PdfReader
import traceback


def extract_text_from_pdf_old(file_path):
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    pdf_file = BytesIO(pdf_content)
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_pdf(file_path, llm=None, product_mode="lite"):
    try:        
        from autocoder.utils._markitdown import MarkItDown
        md_converter = MarkItDown(llm=llm, product_mode=product_mode)
        result = md_converter.convert(file_path)
        return result.text_content
    except (BaseException, Exception) as e:
        traceback.print_exc()
        return extract_text_from_pdf_old(file_path)
