import os
from typing import List
import pdf2image
from PIL import Image
import byzerllm
from autocoder.common import AutoCoderArgs

# Importing required libraries for docx conversion
try:
    import docx2pdf
except ImportError:
    docx2pdf = None

# Importing required libraries for Linux conversion
try:
    import uno
    from com.sun.star.beans import PropertyValue
    from com.sun.star.connection import NoConnectException
    from com.sun.star.task import ErrorCodeIOException
    from com.sun.star.uno import Exception as UnoException
    from com.sun.star.uno import RuntimeException
except ImportError:
    uno = None

# Importing required library for docx to pdf conversion using pypandoc
try:
    import pypandoc
except ImportError:
    pypandoc = None

class Anything2Images:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.output_dir = args.output
        os.makedirs(self.output_dir, exist_ok=True)

    def convert(self, file_path: str) -> List[str]:
        file_path = os.path.abspath(file_path)
        if file_path.lower().endswith('.pdf'):
            return self.convert_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            return self.convert_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    def convert_pdf(self, file_path: str) -> List[str]:
        images = pdf2image.convert_from_path(file_path)
        image_paths = []
        for i, image in enumerate(images, start=1):
            image_path = os.path.join(self.output_dir, f"{os.path.basename(file_path)}_page{i}.png")
            image.save(image_path, 'PNG')
            image_paths.append(image_path)
        return image_paths

    def convert_docx(self, file_path: str) -> List[str]:
        if docx2pdf:
            pdf_path = os.path.join(self.output_dir, f"{os.path.basename(file_path)}.pdf")
            docx2pdf.convert(file_path, pdf_path)
            if not os.path.exists(pdf_path):
                if pypandoc:
                    pypandoc.convert_file(file_path, 'pdf', outputfile=pdf_path)
                    print(f"Converted {file_path} to {pdf_path} using pypandoc")
                else:
                    raise ImportError("Neither docx2pdf nor pypandoc are available for DOCX conversion.")
        elif uno:
            pdf_path = self.convert_docx_linux(file_path)
            print(f"Converted {file_path} to {pdf_path} using LibreOffice")
        else:
            raise ImportError("Neither docx2pdf nor uno are available for DOCX conversion.")
        
        if not os.path.exists(pdf_path):
            raise RuntimeError("Failed to convert DOCX to PDF")
        
        image_paths = self.convert_pdf(pdf_path)
        os.remove(pdf_path)
        return image_paths

    def convert_docx_linux(self, file_path: str) -> str:
        output_pdf = os.path.join(self.output_dir, f"{os.path.basename(file_path)}.pdf")
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context)
        try:
            ctx = resolver.resolve(
                "uno:pipe,name=officepipe;urp;StarOffice.ComponentContext")
        except NoConnectException:
            raise RuntimeError("LibreOffice is not running. Start it with 'libreoffice --headless --accept=\"socket,host=localhost,port=2002;urp;StarOffice.ServiceManager\"'")
        desktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx)
        convert_props = (
            PropertyValue("FilterName", 0, "writer_pdf_Export", 0),
        )
        url = uno.systemPathToFileUrl(file_path)
        out_url = uno.systemPathToFileUrl(output_pdf)
        doc = desktop.loadComponentFromURL(url, "_blank", 0, ())
        doc.storeToURL(out_url, convert_props)
        doc.close(True)
        return output_pdf

    def merge_table_images(self, image_paths: List[str], table_start_page: int, table_end_page: int) -> List[str]:
        if table_start_page < 1 or table_end_page > len(image_paths) or table_start_page > table_end_page:
            raise ValueError(f"Invalid table page range: {table_start_page} - {table_end_page}")

        merged_image_path = os.path.join(self.output_dir, f"merged_table_{table_start_page}_{table_end_page}.png")
        table_images = [Image.open(image_path) for image_path in image_paths[table_start_page - 1 : table_end_page]]
        widths, heights = zip(*(i.size for i in table_images))
        max_width = max(widths)
        total_height = sum(heights)

        merged_image = Image.new('RGB', (max_width, total_height))
        y_offset = 0
        for image in table_images:
            merged_image.paste(image, (0, y_offset))
            y_offset += image.size[1]
        
        merged_image.save(merged_image_path)
        return image_paths[:table_start_page - 1] + [merged_image_path] + image_paths[table_end_page:]