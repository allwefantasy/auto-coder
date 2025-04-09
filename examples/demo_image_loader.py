
import os
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.utils.llms import get_single_llm
from autocoder.rag.loaders.image_loader import extract_text_from_image, image_to_markdown

def main():
    # 初始化tokenizer
    load_tokenizer()

    # 获取LLM对象
    llm = get_single_llm("v3_chat", product_mode="lite")

    # 需要识别的图片路径，请替换为你自己的图片文件
    image_path = "your_image_path.png"  # TODO: 替换为真实图片路径

    # 选择识别引擎: "vl" 或 "paddle"
    engine = "vl"  # 或 "paddle"

    # 方法1：直接获取Markdown文本
    markdown_text = extract_text_from_image(image_path, llm, engine=engine)
    print("=== Extracted Markdown Content ===")
    print(markdown_text)

    # 方法2：保存为同名md文件并返回内容
    markdown_text2 = image_to_markdown(image_path, llm, engine=engine)
    print("=== Saved Markdown Content ===")
    print(markdown_text2)

if __name__ == "__main__":
    main()
