import os
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.utils.llms import get_single_llm
from autocoder.rag.loaders.image_loader import ImageLoader, ReplaceInFileTool
import re


def test_format_table_in_content_basic(ocr_text):
    """
    测试 ImageLoader.format_table_in_content 是否能正确识别并转换OCR表格文本为Markdown格式
    """
    print("[DEBUG] 调用 format_table_in_content() 开始")
    # 注意：该方法依赖llm模型，测试时传None可能导致无法转换。
    # 实际测试中应mock llm对象，或集成测试。
    # 这里作为示例，传入None，主要验证调用流程
    llm_obj = get_single_llm("quasar-alpha", product_mode="lite")
    print(f"[DEBUG] 获取到llm对象: {llm_obj}")
    result = ImageLoader.format_table_in_content(ocr_text, llm=llm_obj)
    print("[DEBUG] format_table_in_content() 返回结果如下:\n", result)

    # 关键判断，是否转换成功
    if "| " in result:
        print("[INFO] 表格格式化成功，检测到Markdown表格")
    else:
        print("[WARN] 表格格式化失败，未检测到Markdown格式，原始或未格式化内容返回")

    return result


def test_extract():
    t = '''