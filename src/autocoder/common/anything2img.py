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
import json
from byzerllm.utils.client import code_utils

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
        if llm.get_sub_client("vl_model"):
            self.vl_model = llm.get_sub_client("vl_model")
        else:
            self.vl_model = self.llm
        self.args = args
        self.output_dir = args.output
        os.makedirs(self.output_dir, exist_ok=True)
        self.keep_conversion = keep_conversion            

    @byzerllm.prompt()
    def analyze_image(self, image_path: str) -> str:
        """
        {{ image }}
        图片中一般可能包含文字，图片，图表三种元素,给出每种元素的bounding box坐标。
        bouding box 使用 (xmin, ymin, xmax, ymax) 来表示，其中xmin, ymin： 表示矩形左上角的坐标
        xmax, ymax： 表示矩形右下角的坐标

        最后按如下格式返回：
        ```json
        {
            "objects": [
                {
                    "type": "image",
                    "bounding_box": [xmin, ymin, xmax, ymax],
                    "text": "图片描述"
                },
                {
                    "type": "text",
                    "bounding_box": [xmin, ymin, xmax, ymax],
                    "text": "文本内容"
                }
                ,
                {
                    "type": "table",
                    "bounding_box": [xmin, ymin, xmax, ymax],
                    "text": "表格的markdown格式"
                }
                ...
            ]
        }
        ```
        """
        image = byzerllm.Image.load_image_from_path(image_path)
        return {"image": image}

    @byzerllm.prompt()
    def detect_objects(self, image_path: str) -> str:
        """
        {{ image }}
        请分析这张图片，识别图片中图片，并给出每个图片的bounding box坐标。
        bouding box 使用 (xmin, ymin, xmax, ymax) 来表示，其中xmin, ymin： 表示矩形左上角的坐标
        xmax, ymax： 表示矩形右下角的坐标

        最后按如下格式返回：
        ```json
        {
            "objects": [
                {
                    "bounding_box": [xmin, ymin, xmax, ymax],
                    "text": "图片描述"
                },
                ...
            ]
        }
        ```
        
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
        
        pages_results = []
        # 使用线程池并行分析图片
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self.analyze_image.with_llm(self.vl_model).run,
                    image_path
                ): image_path for image_path in image_paths
            }
            
            for future in as_completed(futures):
                image_path = futures[future]
                try:
                    result = future.result()
                    # 解析JSON结果
                    result_json = code_utils.extract_code(result)[-1][1]
                    result_dict = json.loads(result_json)
                    # 存储结果和对应的图像路径
                    pages_results.append((result_dict, image_path))
                    logger.info(f"Analyzed {image_path}")
                except Exception as e:
                    logger.error(f"Failed to analyze {image_path}: {str(e)}")
        
        # 生成Markdown内容
        markdown_content = []
        
        # 遍历每个页面的分析结果
        for page_result, image_path in pages_results:
            page_markdown = []
            
            # 按照对象类型分别处理文本、图片和表格
            text_objects = []
            image_objects = []
            table_objects = []
            
            for obj in page_result.get("objects", []):
                obj_type = obj.get("type", "")
                if obj_type == "text":
                    text_objects.append(obj)
                elif obj_type == "image":
                    image_objects.append(obj)
                elif obj_type == "table":
                    table_objects.append(obj)
            
            # 按照垂直位置排序所有对象
            all_objects = text_objects + image_objects + table_objects
            all_objects.sort(key=lambda x: x.get("bounding_box", [0, 0, 0, 0])[1])  # 按y坐标排序
            
            # 处理所有对象并生成markdown
            for obj in all_objects:
                obj_type = obj.get("type", "")
                bbox = obj.get("bounding_box", [0, 0, 0, 0])
                content = obj.get("text", "")
                
                if obj_type == "text":
                    # 直接添加文本内容
                    page_markdown.append(content)
                
                elif obj_type == "image":
                    # 处理图片
                    original_image = Image.open(image_path)
                    
                    # 提取图片区域
                    x1, y1, x2, y2 = [int(coord) for coord in bbox]
                    cropped_image = original_image.crop((x1, y1, x2, y2))
                    
                    # 生成唯一文件名
                    image_filename = f"img_{os.path.basename(image_path)}_{x1}_{y1}_{x2}_{y2}.png"
                    cropped_image_path = os.path.join(images_dir, image_filename)
                    cropped_image.save(cropped_image_path)
                    
                    # 添加图片的markdown
                    image_markdown = f"![{content}]({cropped_image_path})"
                    page_markdown.append(image_markdown)
                
                elif obj_type == "table":
                    # 对表格内容进行处理，它已经是markdown格式
                    page_markdown.append(content)
            
            # 将页面内容合并为字符串
            page_content = "\n\n".join(page_markdown)
            markdown_content.append(page_content)
        
        # 将所有页面内容合并为一个Markdown文档
        return '\n\n---\n\n'.join(markdown_content)
    