from io import BytesIO
from pypdf import PdfReader
from autocoder.utils._markitdown import MarkItDown


def extract_text_from_pdf_old(file_path):
    with open(file_path, "rb") as f:
        pdf_content = f.read()
    pdf_file = BytesIO(pdf_content)
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def extract_text_from_pdf(file_path):
    try:        
        md_converter = MarkItDown()
        result = md_converter.convert(file_path)
        return result.text_content
    except Exception as e:        
        return extract_text_from_pdf_old(file_path)
