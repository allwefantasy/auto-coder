
import os
import json
from PIL import Image
import traceback

try:
    from paddleocr import PaddleOCR
except ImportError:
    PaddleOCR = None

import byzerllm
from byzerllm.utils.client import code_utils
from autocoder.utils.llms import get_single_llm

def extract_text_from_image(image_path: str, llm, engine: str = "vl") -> str:
    """
    识别图片中的所有文本内容，包括表格（以markdown table格式）
    
    Args:
        image_path: 图片路径
        llm: LLM对象或字符串（模型名）
        engine: 选择使用的识别引擎
            - "vl": 使用视觉语言模型 (默认)
            - "paddle": 使用paddleocr
    """
    # 支持llm为字符串，自动转换为llm实例
    if isinstance(llm, str):
        llm = get_single_llm(llm)

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
        if PaddleOCR is None:
            print("paddleocr not installed")
            return ""

        try:
            ocr_engine = PaddleOCR(use_angle_cls=True, lang='ch')
            result = ocr_engine.ocr(image_path, cls=True)
            lines = []
            for line in result:
                if isinstance(line, list):
                    for word_info in line:
                        txt = word_info[1][0]
                        lines.append(txt)
            markdown_content = "\n".join(lines)
            return markdown_content
        except Exception:
            traceback.print_exc()
            return ""

    else:
        print(f"Unknown engine type: {engine}. Supported engines are 'vl' and 'paddle'.")
        return ""

def image_to_markdown(image_path: str, llm, engine: str = "vl") -> str:
    """
    识别图片内容，生成markdown文件

    Args:
        image_path: 图片路径
        llm: LLM对象
        engine: 选择识别引擎，"vl" 或 "paddle"，默认为"vl"
    """
    md_content = extract_text_from_image(image_path, llm, engine=engine)

    md_path = os.path.splitext(image_path)[0] + ".md"
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)
    except Exception:
        traceback.print_exc()

    return md_content
