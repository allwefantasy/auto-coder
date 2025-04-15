import os
import time
from loguru import logger
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm
from autocoder.rag.cache.simple_cache import AutoCoderRAGAsyncUpdateQueue
from autocoder.rag.variable_holder import VariableHolder
from tokenizers import Tokenizer
import pkg_resources

def main():
    # 指定测试目录，替换为你自己的包含PDF的目录路径
    pdf_dir = "sample_pdf_dir"
    
    # 检查目录是否存在
    if not os.path.isdir(pdf_dir):
        logger.warning(f"测试目录 {pdf_dir} 不存在，请将包含PDF文件的目录放在当前目录，并命名为 {pdf_dir}")
        return

    # 初始化参数和llm
    args = AutoCoderArgs(
        source_dir=pdf_dir,
        conversation_prune_safe_zone_tokens=4000,
        rag_duckdb_vector_dim=None,
        rag_duckdb_query_similarity=0.1,
        rag_duckdb_query_top_k=20,
        hybrid_index_max_output_tokens=10000,
    )

    # 初始化tokenizer
    try:
        tokenizer_path = pkg_resources.resource_filename(
            "autocoder", "data/tokenizer.json"
        )
        VariableHolder.TOKENIZER_PATH = tokenizer_path
        VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
    except FileNotFoundError:
        logger.error("Tokenizer文件未找到，请确保autocoder正确安装")
        tokenizer_path = None

    # 初始化一个llm
    llm = get_single_llm("quasar-alpha", product_mode="lite")

    logger.info("初始化SimpleCache缓存管理器...")
    cache_manager = AutoCoderRAGAsyncUpdateQueue(
        path=pdf_dir,
        ignore_spec=None,
        required_exts=[".pdf"],
        args=args,
        llm=llm
    )

    logger.info("开始构建缓存...")
    cache_manager.load_first()

    # 等待缓存线程完成
    time.sleep(5)

    logger.info("开始查询缓存内容...")
    cache = cache_manager.get_cache()
    logger.info(f"缓存中文件数: {len(cache)}")
    for file_path, file_info in cache.items():
        logger.info(f"文件: {file_path}")
        contents = file_info.get('content', [])
        for content in contents:
            preview = content.get('source_code', '')[:500]
            logger.info(f"内容预览: {preview}")

    logger.info("PDF目录解析完成。")

if __name__ == "__main__":
    main()