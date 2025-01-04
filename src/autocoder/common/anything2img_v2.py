import os
from typing import List, Optional, Dict, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image
import byzerllm
from autocoder.common import AutoCoderArgs
from loguru import logger
import platform
import pydantic
from docx import Document
import base64
import json
from byzerllm.utils.client import code_utils
import tempfile

class ImageInfo(pydantic.BaseModel):
    """
    图片信息
    """
    coordinates: List[float] = pydantic.Field(..., description="图片坐标 [x1,y1,x2,y2]")
    text: Optional[str] = pydantic.Field(None, description="图片描述")
    width: int = pydantic.Field(..., description="图片宽度")
    height: int = pydantic.Field(..., description="图片高度")

class Page(pydantic.BaseModel):
    """
    页面信息，包含文本和图片
    """
    text: str = pydantic.Field(..., description="页面文本内容")
    images: List[ImageInfo] = pydantic.Field(default_factory=list, description="页面中的图片信息")
    width: int = pydantic.Field(..., description="页面宽度")
    height: int = pydantic.Field(..., description="页面高度")

class Anything2ImagesV2:
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

    @byzerllm.prompt()
    def analyze_image(self, image_path: str) -> str:
        """
        分析下面的图片，返回该图片包含的文本内容以及图片位置信息（如果有）。请遵循以下格式返回：

        ```json
        {
            "text": "页面的文本内容",
            "images": [
                {
                    "coordinates": [x1, y1, x2, y2],
                    "text": "对图片的描述",
                    "width": 图片宽度,
                    "height": 图片高度
                }
            ],
            "width": 页面宽度,
            "height": 页面高度
        }
        ```

        注意：
        1. 图片坐标使用相对位置，即x和y都除以页面宽度和高度得到0-1之间的值
        2. 文本内容应保持原有的段落格式
        """
        image = byzerllm.Image.load_image_from_path(image_path)
        return {"image": image}

    def convert_pdf(self, file_path: str) -> List[str]:
        """转换PDF文件为图片列表"""
        pdf_document = fitz.open(file_path)
        image_paths = []
        
        if self.args.single_file:
            # 合并所有页面为一张大图
            total_height = sum(page.rect.height for page in pdf_document)
            max_width = max(page.rect.width for page in pdf_document)
            
            # 创建一个新的PIL图像
            merged_image = Image.new('RGB', (int(max_width), int(total_height)), 'white')
            y_offset = 0
            
            for page in pdf_document:
                pix = page.get_pixmap()
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                merged_image.paste(img, (0, y_offset))
                y_offset += pix.height
            
            # 保存合并后的图片
            merged_image_path = os.path.join(self.output_dir, f"{os.path.basename(file_path)}_merged.png")
            merged_image.save(merged_image_path)
            image_paths.append(merged_image_path)
        else:
            # 分别保存每一页
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                pix = page.get_pixmap()
                image_path = os.path.join(self.output_dir, f"{os.path.basename(file_path)}_page{page_num + 1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
        
        pdf_document.close()
        return image_paths

    def convert_docx(self, file_path: str) -> List[str]:
        """转换Word文档为PDF后再转为图片"""
        # 首先转换为PDF
        pdf_path = os.path.join(tempfile.gettempdir(), f"{os.path.basename(file_path)}.pdf")
        doc = Document(file_path)
        
        # 使用已有的转换逻辑
        from autocoder.common.anything2images import Anything2Images
        converter = Anything2Images(self.llm, self.args)
        converter.convert_word_to_pdf_v2(file_path, pdf_path)
        
        # 转换PDF为图片
        image_paths = self.convert_pdf(pdf_path)
        
        # 清理临时PDF文件
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        return image_paths

    def convert(self, file_path: str) -> List[str]:
        """根据文件类型选择合适的转换方法"""
        file_path = os.path.abspath(file_path)
        if file_path.lower().endswith('.pdf'):
            return self.convert_pdf(file_path)
        elif file_path.lower().endswith('.docx'):
            return self.convert_docx(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path}")

    def to_markdown(self, file_path: str) -> str:
        """
        将文档转换为Markdown格式
        """
        # 转换文档为图片
        image_paths = self.convert(file_path)
        
        pages: List[Page] = []
        # 分析每个图片
        for image_path in image_paths:
            result = self.analyze_image.with_llm(self.vl_model).with_return_type(Page).run(image_path)
            pages.append(result)
            logger.info(f"Analyzed {image_path}")
        
        # 生成Markdown内容
        markdown_content = []
        for page in pages:
            # 添加文本内容
            text_lines = page.text.split('\n')
            current_position = 0
            
            # 处理图片和文本的混合
            for line in text_lines:
                # 检查是否需要在这个位置插入图片
                for img in page.images:
                    relative_position = img.coordinates[1]  # 使用y1坐标作为相对位置
                    if (current_position/len(text_lines)) >= relative_position:
                        # 计算图片在markdown中的显示位置
                        image_placeholder = f"![{img.text}]({img.coordinates})"
                        markdown_content.append(image_placeholder)
                        # 移除已处理的图片
                        page.images = [i for i in page.images if i != img]
                
                markdown_content.append(line)
                current_position += 1
            
            # 添加剩余未插入的图片
            for img in page.images:
                image_placeholder = f"![{img.text}]({img.coordinates})"
                markdown_content.append(image_placeholder)
        
        return '\n'.join(markdown_content)