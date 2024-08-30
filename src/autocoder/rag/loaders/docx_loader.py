from io import BytesIO
import docx2txt

def extract_text_from_docx(docx_content):
    docx_file = BytesIO(docx_content)
    text = docx2txt.process(docx_file)
    return text