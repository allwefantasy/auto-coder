import os
from typing import List, Optional, Dict, Any, Tuple
import fitz  # PyMuPDF
import byzerllm
from autocoder.common import AutoCoderArgs
from loguru import logger
import pydantic
from docx import Document
from spire.doc import Document
from spire.doc.common import ImageType
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

class Anything2Img:
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,        
        keep_conversion: bool = False,                
    ):
        self.llm = llm
        self.vl_model = llm.get_sub_client("vl_model")
        self.args = args
        self.output_dir = args.output
        os.makedirs(self.output_dir, exist_ok=True)
        self.keep_conversion = keep_conversion            

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
        try:
            # 分别保存每一页
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                pix = page.get_pixmap()
                image_path = os.path.join(self.output_dir, f"{os.path.basename(file_path)}_page{page_num + 1}.png")
                pix.save(image_path)
                image_paths.append(image_path)
        finally:
            # 确保PDF文档关闭
            pdf_document.close()
        return image_paths

    def convert_docx(self, file_path: str) -> List[str]:
        """使用 Spire.Doc 将 Word 文档直接转换为图片"""
       

        # 创建 Spire.Doc 文档对象
        doc = Document()
        doc.LoadFromFile(file_path)

        # 设置图片保存选项
        image_paths = []        
        try:
            # 将每一页保存为图片
            for i in range(doc.GetPageCount()):
                image_path = os.path.join(
                    self.output_dir, 
                    f"{os.path.basename(file_path)}_page{i+1}.png"
                )
                doc.SaveToImages(i, ImageType.Bitmap, image_path)
                image_paths.append(image_path)
        finally:
            # 确保文档关闭
            doc.Close()

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