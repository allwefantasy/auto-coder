import os
from autocoder.utils._markitdown import MarkItDown
from autocoder.rag.loaders.pdf_loader import extract_text_from_pdf
from autocoder.utils.llms import get_single_llm
from autocoder.common import AutoCoderArgs
from loguru import logger

def main():
    # 指定PDF文件路径，建议替换为你自己的PDF文件路径
    pdf_path = "test_with_images.pdf"
    
    # 如果不存在测试PDF，提示用户
    if not os.path.exists(pdf_path):
        logger.warning(f"测试PDF文件 {pdf_path} 不存在，请将包含图片的PDF放在当前目录，并命名为 {pdf_path}")
        return

    # 初始化参数和llm
    args = AutoCoderArgs(
        source_dir=".",
        conversation_prune_safe_zone_tokens=4000,
        rag_duckdb_vector_dim=None,
        rag_duckdb_query_similarity=0.1,
        rag_duckdb_query_top_k=20,
        hybrid_index_max_output_tokens=10000,
    )

    # 初始化一个llm
    llm = get_single_llm("quasar-alpha", product_mode="lite")

    logger.info("开始处理PDF文件，提取文本和图片内容...")

    # 使用extract_text_from_pdf提取内容
    markdown_content = extract_text_from_pdf(pdf_path, llm=llm, product_mode="lite")

    # 打印部分内容预览
    logger.info("PDF转换为Markdown内容预览（前500字符）：")
    print(markdown_content[:500])

    # 保存为md文件
    md_path = os.path.splitext(pdf_path)[0] + ".md"
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        logger.info(f"已将Markdown内容保存至 {md_path}")
    except Exception as e:
        logger.error(f"保存Markdown文件失败: {e}")

if __name__ == "__main__":
    main()