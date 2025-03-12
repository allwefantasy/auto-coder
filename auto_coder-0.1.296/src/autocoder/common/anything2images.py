import os
from typing import List, Callable, Optional,Tuple
import pdf2image
from PIL import Image
import byzerllm
from autocoder.common import AutoCoderArgs
from loguru import logger
import platform

from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

from PIL import Image, ImageDraw, ImageFont
import os
import base64
import json
from byzerllm.utils.client import code_utils
from byzerllm.apps.utils import TagExtractor

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
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
        keep_conversion: bool = False,
        continue_prompt: str = "接着前面的内容继续",
        max_steps: int = 20,
    ):
        self.llm = llm
        self.vl_model = llm.get_sub_client("vl_model")
        self.args = args
        self.output_dir = args.output
        os.makedirs(self.output_dir, exist_ok=True)
        self.keep_conversion = keep_conversion
        self.continue_prompt = continue_prompt
        self.max_steps = max_steps

    def convert(self, file_path: str) -> List[str]:
        file_path = os.path.abspath(file_path)
        if file_path.lower().endswith(".pdf"):
            return self.convert_pdf(file_path)
        elif file_path.lower().endswith(".docx"):
            return self.convert_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    @byzerllm.prompt()
    def single_file_html_prompt(self) -> str:
        """
        将图片里的内容以 HTML 格式进行输出。确保信息完整，并且请只返回以<html></html>为标签的内容，
        不要在开头或结尾包含markdown "```" 或 "```html"。
        """

    @byzerllm.prompt()
    def html_prompt(self) -> str:
        """
        回顾前面所有图片，将图片里的内容以 HTML 格式进行输出。确保信息完整，并且请只返回以<html></html>为标签的内容，
        不要在开头或结尾包含markdown "```" 或 "```html"。
        """

    def merge_table_html_prompt(self, html: str) -> str:
        """
        下面是一个 HTML 内容:

        {{ html }}


        里面有一些信息诸如表格等因为分页等原因被分割开了，请将被分割的信息做适当的合并，重新
        生成一份完整的的HTML内容。请只返回以<html></html>为标签的内容，不要在开头或结尾包含markdown "```" 或 "```html"。
        请确保HTML的完整性，而不要只生成修改部分。
        """

    def _save_conversation(self, conversations):
        if self.keep_conversion:
            with open(
                os.path.join(self.output_dir, "conversations.json"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write((json.dumps(conversations, ensure_ascii=False, indent=4)))

    def to_html_from_images(self, images: List[str]) -> str:
        conversations = []
        if not self.args.single_file:
            for i, image in enumerate(images):
                img_path = image
                image_path_ext = os.path.splitext(img_path)[1][1:]
                with open(img_path, "rb") as image_file:
                    image = base64.b64encode(image_file.read()).decode("utf-8")
                    image = f"data:image/{image_path_ext};base64,{image}"

                conversations.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            [
                                {
                                    "image": image,
                                    "detail": "high",
                                    "text": f"当你看到这张图片的时候，请回复'收到'",
                                }
                            ],
                            ensure_ascii=False,
                        ),
                    }
                )
                # t = self.vl_model.chat_oai(conversations=conversations)
                conversations.append(
                    {
                        "role": "assistant",
                        "content": json.dumps([{"text": "收到"}], ensure_ascii=False),
                    }
                )
                logger.info(f"Collected {i}:{img_path}")

            logger.info("All images are collected. Now start to generate html.")
            conversations.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        [{"text": self.html_prompt.prompt()}], ensure_ascii=False
                    ),
                }
            )
            t = self.vl_model.chat_oai(conversations=conversations)
            conversations.append(
                {
                    "role": "assistant",
                    "content": json.dumps([{"text": t[0].output}], ensure_ascii=False),
                }
            )
            html = t[0].output
        else:
            img_path = images[0]
            image_path_ext = os.path.splitext(img_path)[1][1:]
            with open(img_path, "rb") as image_file:
                image = base64.b64encode(image_file.read()).decode("utf-8")
                image = f"data:image/{image_path_ext};base64,{image}"
            conversations.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        [
                            {
                                "image": image,
                                "detail": "high",
                                "text": self.single_file_html_prompt.prompt(),
                            }
                        ],
                        ensure_ascii=False,
                    ),
                }
            )
            t = self.vl_model.chat_oai(conversations=conversations)
            html = t[0].output

        counter = self.max_steps

        def not_end(_html):
            _not_end = False
            if "```html" in _html:
                _not_end = not "</html>" in _html
            else:
                _not_end = not _html.strip().endswith("</html>")
            return _not_end

        while not_end(html) and counter > 0:
            counter -= 1
            conversations.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        [{"text": self.continue_prompt}], ensure_ascii=False
                    ),
                }
            )
            t = self.vl_model.chat_oai(conversations=conversations)
            logger.info(
                f"The output is not finished yet. Continue to get more output. {counter}th time."
            )
            conversations.append(
                {
                    "role": "assistant",
                    "content": json.dumps([{"text": t[0].output}], ensure_ascii=False),
                }
            )
            self._save_conversation(conversations)
            html += t[0].output

        if "```html" in html:
            for lang, code in code_utils.extract_code(html):
                if lang == "html":
                    html = code
                    break
        logger.info(f"Get the final output: {html[:100]}...{html[-100:]}")
        self._save_conversation(conversations)
        return html

    @byzerllm.prompt()
    def pdf_generation_prompt(
        self, html: str, target_file_path: str, code_prefix: str
    ) -> str:
        """
        根据提供的图片和HTML内容，生成使用reportlab创建PDF的Python代码。

        HTML内容：
        {{ html }}

        你生成的PDF路径需要为： {{ target_file_path }}

        请分析图片布局和HTML内容，然后生成使用reportlab创建PDF的Python代码：

        1. 代码应该包含必要的导入语句，并使用reportlab的组件（如Canvas, Paragraph, Table等）来创建与原始文档布局相似的PDF。
        2. 请确保代码是完整的、可执行的，并包含适当的注释。
        3. 使用最新 reportlab 版本的 API
        4. 生成的代码使用 ```python ``` 包裹
        5. 生成的代码里内容确保不要遗漏任何 HTML 里的文字信息。

        reportlab 使用时需要注意：
        1. 不要使用 Link ,可以直接使用Paragraph,比如 link_text = Paragraph('<a href="http://www.example.com">Click here</a>', style)
        2. 如果使用 styles = getSampleStyleSheet()，那么不要再使用styles.add(ParagraphStyle(name='Heading1', fontSize=18, leading=22, spaceAfter=12)) 之类的，而是修改styles，比如styles['Heading1'].fontSize = 18

        下面是我们给你提供的字体，我们会将这段代码放到你生成的代码的最前面，你可以直接使用这些字体：

        ```python
        {{ code_prefix }}
        ```
        """

    @byzerllm.prompt()
    def error_retry_prompt(self, code: str, error: str, context: str) -> str:
        """

        当执行下列代码时：

        ```python
        {{ code }}
        ```

        代码执行失败，错误如下：

        ```text
        {{ error }}
        ```

        下面是原始代码原来的的需求：

        ```text
        {{ context }}
        ```

        现在根据错误修改代码，然后输出完整的修改后代码,注意，新输出的代码是需要可以直接执行而无需再次修改的。
        输出的代码使用 ```python ``` 包裹。
        """

    def run_python_code(self, code: str, context: str, retries: int = 3):
        from autocoder.common.JupyterClient import JupyterNotebook

        def run_code(code: str) -> str:
            jupyter_client = JupyterNotebook()
            try:
                return jupyter_client.add_and_run(code)
            finally:
                jupyter_client.close()

        result, error = run_code(code)
        print(result)
        print(error)
        while error and retries > 0:
            retries -= 1
            prompt = self.error_retry_prompt.prompt(
                code=code, error=error, context=context
            )
            print(prompt)
            t = self.vl_model.chat_oai(
                conversations=[{"role": "user", "content": prompt}]
            )
            code = code_utils.extract_code(t[0].output)[0][1]
            result, error = run_code(code)
            print(result)
            print(error)

    def anything_to_pdf(
        self,
        origin_file_path: str,
        target_file_path: str,
        prompt_function: Optional[Callable[[str], str]] = None,
        extractor: Optional[Callable[[str], str]] = None,
    ) -> str:
        from rich.console import Console
        from rich.panel import Panel
        from rich.syntax import Syntax

        console = Console()

        images = self.convert(origin_file_path)

        html = self.to_html_from_images(images)
        with open(
            os.path.join(self.output_dir, "output.html"), "w", encoding="utf-8"
        ) as f:
            f.write(html)

        if prompt_function:
            logger.info("processing html with prompt function")
            html = (
                prompt_function.with_llm(self.vl_model)
                .with_extractor(extractor)
                .run(html)
            )
            with open(
                os.path.join(self.output_dir, "output_prompted.html"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(html)

        @byzerllm.prompt()
        def generate_prefix_code(fonts: List[Tuple[str, str]]) -> str:
            """
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            try:
            {{ fonts}}
            except Exception as e:
                print(f"fail to load font")
            """
            fonts_str = (
                "\n".join(
                    [
                        f"    pdfmetrics.registerFont(TTFont('{font[0]}', '{font[1]}'))"
                        for font in fonts
                    ]
                )
                if fonts
                else "    pass"
            )
            return {"fonts": fonts_str}

        ttf_files = [f for f in os.listdir(self.output_dir) if f.endswith(".ttf")]
        fonts = [
            (os.path.splitext(f)[0], os.path.join(self.output_dir, f))
            for f in ttf_files
        ]
        prefix = generate_prefix_code.prompt(fonts=fonts)

        # 使用大模型生成PDF生成代码
        generate_code_prompt = self.pdf_generation_prompt.prompt(
            html=html, target_file_path=target_file_path, code_prefix=prefix
        )

        conversations = []
        if not self.args.single_file:
            for i, image in enumerate(images):
                img_path = image
                image_path_ext = os.path.splitext(img_path)[1][1:]
                with open(img_path, "rb") as image_file:
                    image = base64.b64encode(image_file.read()).decode("utf-8")
                    image = f"data:image/{image_path_ext};base64,{image}"

                conversations.append(
                    {
                        "role": "user",
                        "content": json.dumps(
                            [
                                {
                                    "image": image,
                                    "detail": "high",
                                    "text": f"当你看到这张图片的时候，请回复'收到'",
                                }
                            ],
                            ensure_ascii=False,
                        ),
                    }
                )
                conversations.append(
                    {
                        "role": "assistant",
                        "content": json.dumps([{"text": "收到"}], ensure_ascii=False),
                    }
                )
                logger.info(f"Collected {i}:{img_path}")

            logger.info("All images are collected. Now start to generate code.")
            conversations.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        [{"text": generate_code_prompt}], ensure_ascii=False
                    ),
                }
            )
            t = self.vl_model.chat_oai(conversations=conversations)
            conversations.append(
                {
                    "role": "assistant",
                    "content": json.dumps([{"text": t[0].output}], ensure_ascii=False),
                }
            )
            code = t[0].output
        else:
            img_path = images[0]
            image_path_ext = os.path.splitext(img_path)[1][1:]
            with open(img_path, "rb") as image_file:
                image = base64.b64encode(image_file.read()).decode("utf-8")
                image = f"data:image/{image_path_ext};base64,{image}"
            conversations.append(
                {
                    "role": "user",
                    "content": json.dumps(
                        [
                            {
                                "image": image,
                                "detail": "high",
                                "text": generate_code_prompt,
                            }
                        ],
                        ensure_ascii=False,
                    ),
                }
            )
            t = self.vl_model.chat_oai(conversations=conversations)
            code = t[0].output

        ## 字体下载
        self.download_font(
            "https://github.com/StellarCN/scp_zh/raw/master/fonts/SimSun.ttf",
            "SimSun.ttf",
        )
        self.download_font(
            "https://github.com/hyoshiok/ttf-ipafont/raw/master/ipag.ttf", "ipag.ttf"
        )

        codes = code_utils.extract_code(code)
        pdf_generation_code = codes[0][1]
        pdf_generation_code = prefix + "\n\n" + pdf_generation_code
        # root_tag = TagExtractor(code).extract()
        # pdf_generation_code = root_tag.content[0].content

        # if not isinstance(pdf_generation_code, str):
        #     pdf_generation_code = pdf_generation_code[0]

        # 使用Rich打印生成的代码
        syntax = Syntax(
            pdf_generation_code, "python", theme="monokai", line_numbers=True
        )
        console.print(
            Panel(syntax, title="Generated PDF Generation Code", expand=False)
        )

        self.run_python_code(pdf_generation_code, context=generate_code_prompt)
        return target_file_path

    def download_font(self, font_url: str, font_name: str):
        font_path = os.path.join(self.output_dir, font_name)
        if not os.path.exists(font_path):
            import requests

            print(f"Downloading {font_name} from {font_url}")
            response = requests.get(font_url)
            if response.status_code == 200:
                with open(font_path, "wb") as f:
                    f.write(response.content)
                print(f"SimSun.ttf downloaded successfully to {font_path}")
            else:
                print(
                    f"Failed to download SimSun.ttf. Status code: {response.status_code}"
                )

    def to_html(self, file_path: str) -> str:
        images = self.convert(file_path)
        return self.to_html_from_images(images)

    def convert_pdf(self, file_path: str) -> List[str]:
        images = pdf2image.convert_from_path(file_path)
        image_paths = []

        if self.args.single_file:
            # 合并所有图片为一张图片
            total_width = max(image.width for image in images)
            total_height = sum(image.height for image in images)
            merged_image = Image.new("RGB", (total_width, total_height))
            y_offset = 0
            for image in images:
                merged_image.paste(image, (0, y_offset))
                y_offset += image.height

            merged_image_path = os.path.join(
                self.output_dir, f"{os.path.basename(file_path)}_merged.png"
            )
            merged_image.save(merged_image_path, "PNG")
            image_paths.append(merged_image_path)
        else:
            for i, image in enumerate(images, start=1):
                image_path = os.path.join(
                    self.output_dir, f"{os.path.basename(file_path)}_page{i}.png"
                )
                image.save(image_path, "PNG")
                image_paths.append(image_path)

        return image_paths

    def get_default_chinese_font(self):

        system = platform.system()
        if system == "Windows":
            return "SimSun"  # Windows 默认中文字体
        elif system == "Darwin":  # macOS
            return "STXihei"  # macOS 默认中文字体
        elif system == "Linux":
            return "WenQuanYi Zen Hei"  # Linux 默认中文字体
        else:
            raise ValueError(f"Unsupported operating system: {system}")

    def convert_word_to_pdf_v2(self, word_file, pdf_file):
        # Load the Word document
        doc = Document(word_file)

        # Create a new PDF document
        pdf_doc = SimpleDocTemplate(pdf_file, pagesize=letter)

        # Extract the content from the Word document
        content = []
        for element in doc.body.elements:
            if isinstance(element, Document):
                # Extract paragraphs from the document
                for paragraph in element.paragraphs:
                    text = paragraph.text
                    pdf_paragraph = Paragraph(text, getSampleStyleSheet()["Normal"])
                    content.append(pdf_paragraph)
            elif isinstance(element, Document.table):
                # Extract tables from the document
                table_data = []
                for row in element.rows:
                    row_data = []
                    for cell in row.cells:
                        row_data.append(cell.text)
                    table_data.append(row_data)

                # Create a Table object with the extracted data
                pdf_table = Table(table_data)

                # Apply table styles (optional)
                table_style = TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 14),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("TEXTCOLOR", (0, 1), (-1, -1), colors.black),
                        ("ALIGN", (0, 1), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (-1, -1), 12),
                        ("TOPPADDING", (0, 1), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                    ]
                )
                pdf_table.setStyle(table_style)

                # Append the Table object to the content list
                content.append(pdf_table)

        # Build the PDF document
        pdf_doc.build(content)

        print("Word document converted to PDF successfully!")

    def convert_docx(self, file_path: str) -> List[str]:
        if uno:
            pdf_path = self.convert_docx_linux(file_path)
            logger(f"Converted {file_path} to {pdf_path} using LibreOffice")

        elif docx2pdf:
            pdf_path = os.path.join(
                self.output_dir, f"{os.path.basename(file_path)}.pdf"
            )
            try:
                docx2pdf.convert(file_path, pdf_path)
            except:
                logger.info("docx2pdf failed. Trying to convert using pypandoc.")

            if not os.path.exists(pdf_path):
                if pypandoc:
                    logger.info(
                        "docx2pdf failed. Trying to convert using pypandoc. Downloading pandoc..."
                    )
                    pypandoc.download_pandoc()
                    pypandoc.convert_file(
                        file_path,
                        "pdf",
                        outputfile=pdf_path,
                        extra_args=[
                            "--pdf-engine=xelatex",
                            "--variable",
                            f'mainfont="{self.get_default_chinese_font()}"',
                        ],
                    )
                    logger.info(f"Converted {file_path} to {pdf_path} using pypandoc")
                else:
                    raise ImportError(
                        "Neither docx2pdf nor pypandoc are available for DOCX conversion."
                    )

        else:
            raise ImportError(
                "Neither docx2pdf nor uno are available for DOCX conversion."
            )

        if not os.path.exists(pdf_path):
            raise RuntimeError("Failed to convert DOCX to PDF")

        image_paths = self.convert_pdf(pdf_path)
        os.remove(pdf_path)
        return image_paths

    def convert_docx_linux(self, file_path: str) -> str:
        output_pdf = os.path.join(self.output_dir, f"{os.path.basename(file_path)}.pdf")
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )
        try:
            ctx = resolver.resolve(
                "uno:pipe,name=officepipe;urp;StarOffice.ComponentContext"
            )
        except NoConnectException:
            raise RuntimeError(
                "LibreOffice is not running. Start it with 'libreoffice --headless --accept=\"socket,host=localhost,port=2002;urp;StarOffice.ServiceManager\"'"
            )
        desktop = ctx.ServiceManager.createInstanceWithContext(
            "com.sun.star.frame.Desktop", ctx
        )
        convert_props = (PropertyValue("FilterName", 0, "writer_pdf_Export", 0),)
        url = uno.systemPathToFileUrl(file_path)
        out_url = uno.systemPathToFileUrl(output_pdf)
        doc = desktop.loadComponentFromURL(url, "_blank", 0, ())
        doc.storeToURL(out_url, convert_props)
        doc.close(True)
        return output_pdf
