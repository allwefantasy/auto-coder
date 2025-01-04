import os
import fitz  # PyMuPDF
from spire.doc import Document
from spire.doc import ImageType
from typing import List, Tuple, Optional
import base64
import json
from loguru import logger
import byzerllm
from autocoder.common import AutoCoderArgs

class Anything2ImgV2:
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
        """Convert file to images"""
        file_path = os.path.abspath(file_path)
        if file_path.lower().endswith(".pdf"):
            return self.convert_pdf(file_path)
        elif file_path.lower().endswith(".docx"):
            return self.convert_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    def convert_pdf(self, file_path: str) -> List[str]:
        """Convert PDF to images using PyMuPDF"""
        pdf_document = fitz.open(file_path)
        image_paths = []

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            pix = page.get_pixmap()
            image_path = os.path.join(
                self.output_dir, f"{os.path.basename(file_path)}_page{page_num+1}.png"
            )
            pix.save(image_path)
            image_paths.append(image_path)

        pdf_document.close()
        return image_paths

    def convert_docx(self, file_path: str) -> List[str]:
        """Convert Word document to images using Spire.Doc"""
        document = Document()
        document.LoadFromFile(file_path)
        image_paths = []

        for i in range(document.GetPageCount()):
            image_stream = document.SaveImageToStreams(i, ImageType.Bitmap)
            image_path = os.path.join(
                self.output_dir, f"{os.path.basename(file_path)}_page{i+1}.png"
            )
            with open(image_path, "wb") as image_file:
                image_file.write(image_stream.ToArray())
            image_paths.append(image_path)

        document.Close()
        return image_paths

    @byzerllm.prompt()
    def extract_content_prompt(self) -> str:
        """
        请分析图片内容并提取以下信息：
        1. 所有文字内容，转换为Markdown格式
        2. 如果图片中有嵌入的图片，请返回其坐标位置，使用 ![](x1,y1,x2,y2) 表示
        3. 将提取的图片位置信息插入到文字内容的合适位置
        4. 确保Markdown格式正确
        5. 只返回Markdown内容，不要包含其他说明
        """

    def to_markdown(self, images: List[str]) -> str:
        """Convert images to markdown using visual model"""
        conversations = []
        markdown_content = ""

        for i, image in enumerate(images):
            with open(image, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode("utf-8")
                image_data = f"data:image/png;base64,{image_data}"

            conversations.append({
                "role": "user",
                "content": json.dumps([{
                    "image": image_data,
                    "detail": "high",
                    "text": self.extract_content_prompt.prompt()
                }], ensure_ascii=False)
            })

            response = self.vl_model.chat_oai(conversations=conversations)
            if response and response[0].output:
                markdown_content += response[0].output + "\n\n"
                logger.info(f"Processed image {i+1}/{len(images)}")

            time.sleep(self.args.anti_quota_limit)

        return markdown_content

    def save_markdown(self, content: str, output_path: str):
        """Save markdown content to file"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.info(f"Markdown saved to {output_path}")

    def process_file(self, file_path: str, output_md_path: str):
        """Process file and save as markdown"""
        try:
            # Convert to images
            images = self.convert(file_path)
            logger.info(f"Converted {file_path} to {len(images)} images")

            # Extract content to markdown
            markdown_content = self.to_markdown(images)
            
            # Save markdown
            self.save_markdown(markdown_content, output_md_path)
            
            # Clean up images if not keeping conversion
            if not self.keep_conversion:
                for image in images:
                    os.remove(image)
                logger.info("Cleaned up temporary images")

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise