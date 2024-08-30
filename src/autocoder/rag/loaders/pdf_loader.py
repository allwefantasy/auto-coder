from io import BytesIO
from pypdf import PdfReader

def extract_text_from_pdf(pdf_content):
    pdf_file = BytesIO(pdf_content)
    pdf_reader = PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text