
import os
import traceback
from PIL import Image

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

try:
    import paddlex as paddlex_module
except ImportError:
    paddlex_module = None

import byzerllm
from byzerllm.utils.client import code_utils
from autocoder.utils.llms import get_single_llm

def paddleocr_extract_text(
    file_path,
    lang='ch',
    use_angle_cls=True,
    page_num=10,
    slice_params=None,
    det_model_dir=None,
    rec_model_dir=None,
    **kwargs
):
    """
    使用 PaddleOCR 识别文本，支持图片、PDF、超大图像滑动窗口

    Args:
        file_path: 图片或PDF路径
        lang: 语言，默认中文
        use_angle_cls: 是否启用方向分类
        page_num: 识别PDF时的最大页数
        slice_params: 超大图像滑动窗口参数 dict
        det_model_dir: 自定义检测模型路径
        rec_model_dir: 自定义识别模型路径
        kwargs: 其他paddleocr参数
    Returns:
        识别出的纯文本字符串
    """
    if PaddleOCR is None:
        print("paddleocr not installed")
        return ""

    # 初始化 OCR
    try:
        ocr = PaddleOCR(
            use_angle_cls=use_angle_cls,
            lang=lang,
            page_num=page_num,
            det_model_dir=det_model_dir,
            rec_model_dir=rec_model_dir,
            **kwargs
        )
    except Exception:
        traceback.print_exc()
        return ""

    try:
        ext = os.path.splitext(file_path)[1].lower()

        # 处理PDF
        if ext == ".pdf":
            result = ocr.ocr(file_path, cls=True)
            lines = []
            for page in result:
                if isinstance(page, list):
                    for line in page:
                        if isinstance(line, list) or isinstance(line, tuple):
                            txt = line[1][0]
                            lines.append(txt)
            return "\n".join(lines)

        # 处理图片
        else:
            # 使用滑动窗口参数
            if slice_params is not None:
                result = ocr.ocr(file_path, cls=True, slice=slice_params)
            else:
                result = ocr.ocr(file_path, cls=True)

            lines = []
            # PaddleOCR >=2.6 结果为 [ [ (bbox, (text, conf)), ... ] ]
            for block in result:
                if isinstance(block, list):
                    for line in block:
                        if isinstance(line, list) or isinstance(line, tuple):
                            txt = line[1][0]
                            lines.append(txt)
            return "\n".join(lines)

    except Exception:
        traceback.print_exc()
        return ""

def paddlex_table_extract_markdown(image_path):
    """
    使用 PaddleX 表格识别pipeline，抽取表格并转换为markdown格式

    Args:
        image_path: 图片路径
    Returns:
        markdown格式的表格字符串
    """
    if paddlex_module is None:
        print("paddlex not installed")
        return ""

    try:
        # 创建 pipeline
        pipeline = paddlex_module.create_pipeline(pipeline='table_recognition')
        # 预测
        outputs = pipeline.predict([image_path])
        if not outputs:
            return ""

        md_results = []
        for res in outputs:
            # 获取HTML表格
            html = None
            try:
                html = res.to_html() if hasattr(res, "to_html") else None
            except Exception:
                html = None

            # 如果没有to_html方法，尝试res.print()内容中提取，或跳过
            if html is None:
                try:
                    from io import StringIO
                    import sys
                    buffer = StringIO()
                    sys_stdout = sys.stdout
                    sys.stdout = buffer
                    res.print()
                    sys.stdout = sys_stdout
                    html = buffer.getvalue()
                except Exception:
                    html = ""

            # 转markdown
            md = html_table_to_markdown(html)
            md_results.append(md)

        return "\n\n".join(md_results)
    except Exception:
        traceback.print_exc()
        return ""

def html_table_to_markdown(html):
    """
    简单将HTML table转换为markdown table
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("BeautifulSoup4 not installed, cannot convert HTML to markdown")
        return ""

    try:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            return ""

        rows = []
        for tr in table.find_all("tr"):
            cells = tr.find_all(["td", "th"])
            row = [cell.get_text(strip=True) for cell in cells]
            rows.append(row)

        if not rows:
            return ""

        # 生成markdown
        md_lines = []
        header = rows[0]
        md_lines.append("| " + " | ".join(header) + " |")
        md_lines.append("|" + "|".join(["---"] * len(header)) + "|")

        for row in rows[1:]:
            md_lines.append("| " + " | ".join(row) + " |")

        return "\n".join(md_lines)
    except Exception:
        traceback.print_exc()
        return ""

def extract_text_from_image(
    image_path: str,
    llm,
    engine: str = "vl",
    product_mode: str = "lite",
    paddle_kwargs: dict = None
) -> str:
    """
    识别图片或PDF中的所有文本内容，包括表格（以markdown table格式）

    Args:
        image_path: 图片或PDF路径
        llm: LLM对象或字符串（模型名）
        engine: 选择识别引擎
            - "vl": 视觉语言模型
            - "paddle": PaddleOCR
            - "paddle_table": PaddleX表格识别
        product_mode: get_single_llm的参数
        paddle_kwargs: dict，传递给PaddleOCR的参数
    Returns:
        markdown内容字符串
    """
    if isinstance(llm, str):
        llm = get_single_llm(llm, product_mode=product_mode)

    markdown_content = ""

    if engine == "vl":
        try:
            vl_model = llm.get_sub_client("vl_model") if llm.get_sub_client("vl_model") else llm

            @byzerllm.prompt()
            def analyze_image(image_path):
                """
                {{ image }}
                你是一名图像理解专家，请识别这张图片中的所有内容，优先识别文字和表格。
                对于普通文字，输出为段落文本。
                对于表格截图，转换成markdown table格式输出。
                请根据内容顺序，整合成一份markdown文档。
                只返回markdown内容，不要添加额外解释。
                """
                image = byzerllm.Image.load_image_from_path(image_path)
                return {"image": image}

            result = analyze_image.with_llm(vl_model).run(image_path)
            md_blocks = code_utils.extract_code(result, language="markdown")
            if md_blocks:
                markdown_content = md_blocks[-1][1]
            else:
                markdown_content = result.strip()
            if not markdown_content:
                raise ValueError("Empty markdown from vl_model")
            return markdown_content

        except Exception:
            traceback.print_exc()
            return ""

    elif engine == "paddle":
        if paddle_kwargs is None:
            paddle_kwargs = {}

        markdown_content = paddleocr_extract_text(image_path, **paddle_kwargs)
        return markdown_content

    elif engine == "paddle_table":
        markdown_content = paddlex_table_extract_markdown(image_path)
        return markdown_content

    else:
        print(f"Unknown engine type: {engine}. Supported engines are 'vl', 'paddle', and 'paddle_table'.")
        return ""

def image_to_markdown(
    image_path: str,
    llm,
    engine: str = "vl",
    product_mode: str = "lite",
    paddle_kwargs: dict = None
) -> str:
    """
    识别图片或PDF内容，生成markdown文件

    Args:
        image_path: 文件路径
        llm: LLM对象或字符串
        engine: 'vl'、'paddle'或'paddle_table'
        product_mode: LLM参数
        paddle_kwargs: dict，传递给PaddleOCR参数
    Returns:
        markdown内容字符串
    """
    md_content = extract_text_from_image(
        image_path,
        llm,
        engine=engine,
        product_mode=product_mode,
        paddle_kwargs=paddle_kwargs
    )

    md_path = os.path.splitext(image_path)[0] + ".md"
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception:
        traceback.print_exc()

    return md_content
