
import time
from autocoder.utils.llms import get_single_llm
from autocoder.common import AutoCoderArgs
from autocoder.rag.cache.local_byzer_storage_cache import LocalByzerStorageCache

if __name__ == "__main__":
    # 初始化LLM
    llm = get_single_llm("v3_chat", product_mode="lite")
    emb_llm = get_single_llm("emb2", product_mode="lite")

    # 配置参数
    args = AutoCoderArgs(
        source_dir="your_code_dir",   # 替换为你的代码目录
        rag_build_name="demo_index",
        hybrid_index_max_output_tokens=10000,
        rag_index_build_workers=4
    )

    # 初始化缓存管理器
    cache_manager = LocalByzerStorageCache(
        path=args.source_dir,
        ignore_spec=None,
        required_exts=[".py", ".js"],
        extra_params=args,
        emb_llm=emb_llm,
        host="127.0.0.1",
        port=33333
    )

    # 构建缓存
    print("Building cache...")
    cache_manager.build_cache()
    print("Cache build completed.")

    # 测试单查询
    query = "如何计算平均值"
    print(f"Query: {query}")
    results = cache_manager.get_cache({
        "queries": [query],
        "enable_vector_search": True,
        "enable_text_search": True
    })
    print("Single query results:")
    for file_path, info in results.items():
        print(f"File: {file_path}")
        for doc in info['content']:
            print(f"Snippet: {doc.get('source_code', '')[:100]}...\n")

    # 测试多查询合并
    queries = ["计算平均值", "字符串处理"]
    print(f"Multi queries: {queries}")
    results = cache_manager.get_cache({
        "queries": queries,
        "merge_strategy": "WEIGHTED_RANK",
        "max_results": 5
    })
    print("Multi-query merged results:")
    for file_path, info in results.items():
        print(f"File: {file_path}")
        for doc in info['content']:
            print(f"Snippet: {doc.get('source_code', '')[:100]}...\n")

    # 模拟文件更新检测与缓存刷新
    print("Triggering update check...")
    cache_manager.trigger_update()
    time.sleep(2)
    print("Update check completed.")
