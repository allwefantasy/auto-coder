
import os
from loguru import logger
from autocoder.common import AutoCoderArgs
from autocoder.helper.rag_doc_creator import create_sample_files
from autocoder.common.v2.agent.agentic_edit_tools.search_files_tool_resolver import SearchFilesToolResolver
from autocoder.common.v2.agent.agentic_edit_types import SearchFilesTool

def main():
    # 准备示例目录
    base_dir = "sample_code_search_demo"
    create_sample_files(base_dir)

    # 初始化参数
    args = AutoCoderArgs(
        source_dir=base_dir,
        rag_duckdb_vector_dim=None,
        rag_duckdb_query_similarity=0.1,
        rag_duckdb_query_top_k=20,
    )

    # 构造搜索工具请求
    search_tool = SearchFilesTool(
        path=".",
        regex=r"def\s+",
        file_pattern="*.py"
    )

    # 实例化解析器
    resolver = SearchFilesToolResolver(
        agent=None,
        tool=search_tool,
        args=args
    )

    # 执行搜索
    logger.info("开始执行SearchFilesToolResolver搜索...")
    result = resolver.resolve()

    if not result.success:
        logger.error(f"搜索失败: {result.message}")
        return

    logger.info(f"搜索完成，共找到 {len(result.content)} 处匹配。")
    for idx, match in enumerate(result.content[:10]):  # 只展示前10个匹配
        logger.info(f"匹配{idx + 1}: 文件 {match['path']} 行号 {match['line_number']}")
        logger.info(f"匹配行: {match['match_line']}")
        logger.info(f"上下文:\n{match['context']}")
        logger.info("-" * 40)

if __name__ == "__main__":
    main()
