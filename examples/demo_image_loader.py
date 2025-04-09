
import os
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.utils.llms import get_single_llm
from autocoder.rag.loaders.image_loader import ImageLoader

def test_format_table_in_content_basic(ocr_text):
    """
    测试 ImageLoader.format_table_in_content 是否能正确识别并转换OCR表格文本为Markdown格式
    """    
    # 注意：该方法依赖llm模型，测试时传None可能导致无法转换。
    # 实际测试中应mock llm对象，或集成测试。
    # 这里作为示例，传入None，主要验证调用流程
    result = ImageLoader.format_table_in_content(ocr_text, llm=get_single_llm("quasar-alpha", product_mode="lite"))        
        
    return result

def main():
    # 初始化tokenizer
    load_tokenizer()

    # 获取LLM对象
    llm = get_single_llm("gemini-2.5-pro-exp-03-25", product_mode="lite")

    # 需要识别的图片路径，请替换为你自己的图片文件
    image_path = "/Users/allwefantasy/projects/brags/_images/年卡大促活动开卡率分析（知识库测试）.pdf/image_9.bmp"  # TODO: 替换为真实图片路径

    # 选择识别引擎: "vl" 或 "paddle" 或者 "paddle_table"
    engine = "paddle"  # 或 "paddle_table"

    # 方法1：直接获取Markdown文本
    markdown_text = ImageLoader.extract_text_from_image(image_path, llm, engine=engine)
    print("=== Extracted Markdown Content ===")
    print(markdown_text)

    # 方法2：保存为同名md文件并返回内容
    markdown_text2 = ImageLoader.image_to_markdown(image_path, llm, engine=engine)
    print("=== Saved Markdown Content ===")
    print(markdown_text2)

    # 测试format_table_in_content
    v = test_format_table_in_content_basic(markdown_text)
    print(v)



if __name__ == "__main__":
    main()
