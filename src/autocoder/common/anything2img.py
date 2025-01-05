import os
from typing import List, Optional, Dict, Any, Tuple
from PIL import Image
import fitz  # PyMuPDF
import byzerllm
from autocoder.common import AutoCoderArgs
from loguru import logger
import pydantic
from docx import Document
from spire.doc import Document
from spire.doc import ImageType
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
class ImageInfo(pydantic.BaseModel):
    """
    图片信息
    """
    coordinates: List[float] = pydantic.Field(..., description="图片坐标 [x1,y1,x2,y2]")
    text: Optional[str] = pydantic.Field(None, description="图片描述")

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
        {{ image }}
        图片中一般包含文字，图片，图表。分析图片，返回该图片包含的文本内容以及图片位置信息。
        请遵循以下格式返回：

        ```json
        {
            "text": "页面的文本内容",
            "images": [
                {
                    "coordinates": [x1, y1, x2, y2],
                    "text": "对图片的描述"                    
                }
            ],
            "width": 页面宽度,
            "height": 页面高度
        }
        ```

        注意：
        1. 其中x1,y1是左上角坐标，x2,y2是右下角坐标，使用绝对坐标，也就是图片的像素坐标。
        2. 文本内容应保持原有的段落格式
        3. width和height是页面宽度，高度,要求整数类型
        4. 格局图片中文本和图片的位置关系，在文本中使用 <image_placeholder> 来表示图片。
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
                basename = os.path.basename(file_path).replace(" ", "_")
                image_path = os.path.join(self.output_dir, f"{basename}_page{page_num + 1}.png")
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
                imageStream = doc.SaveImageToStreams(i, ImageType.Bitmap)
                basename = os.path.basename(file_path).replace(" ", "_")
                image_path = os.path.join(self.output_dir, f"{basename}_page{i + 1}.png")
                with open(image_path, 'wb') as imageFile:
                    imageFile.write(imageStream.ToArray())
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

    def to_markdown(self, file_path: str, size: int = -1, max_workers: int = 10) -> str:
        """
        将文档转换为Markdown格式

        Args:
            file_path: 文件路径
            size: 转换的页数，-1表示全部
            max_workers: 并行度，控制同时分析图片的线程数
        """
        # 创建 _images 目录
        images_dir = os.path.join(self.output_dir, "_images")
        os.makedirs(images_dir, exist_ok=True)
        
        # 转换文档为图片
        if size == -1:
            image_paths = self.convert(file_path)
        else:
            image_paths = self.convert(file_path)[0:size]
        
        pages: List[Page] = []
        # 使用线程池并行分析图片
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.analyze_image.with_llm(self.vl_model).with_return_type(Page).run,
                    image_path
                ): image_path for image_path in image_paths
            }
            
            for future in as_completed(futures):
                image_path = futures[future]
                try:
                    result = future.result()
                    pages.append(result)
                    logger.info(f"Analyzed {image_path}")
                except Exception as e:
                    logger.error(f"Failed to analyze {image_path}: {str(e)}")
        
        # 生成Markdown内容
        markdown_content = []
        
        # 遍历每个页面和对应的图片路径
        for page, image_path in zip(pages, image_paths):
            # 处理页面中的每个图片
            for img in page.images:                                
                # 打开原始图片
                original_image = Image.open(image_path)                
                
                # 获得坐标
                x1 = img.coordinates[0]
                y1 = img.coordinates[1]
                x2 = img.coordinates[2]
                y2 = img.coordinates[3]
                
                # 截取图片
                cropped_image = original_image.crop((x1, y1, x2, y2))
                
                # 保存截取后的图片
                cropped_image_path = os.path.join(images_dir, f"cropped_{os.path.basename(image_path)}")
                cropped_image.save(cropped_image_path)
                
                # 将图片路径转换为Markdown格式
                image_markdown = f"![{img.text}]({cropped_image_path})"
                
                # 替换文本中的<image_placeholder>为实际的图片Markdown
                page.text = page.text.replace("<image_placeholder>", image_markdown, 1)
            
            # 将处理后的页面文本添加到Markdown内容中
            markdown_content.append(page.text)
        
        # 将所有页面内容合并为一个Markdown文档
        return '\n\n'.join(markdown_content)