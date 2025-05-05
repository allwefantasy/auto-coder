import os
import shutil
import time
from loguru import logger
import sys
import json



# 导入需要的模块
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm
from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules

def create_sample_files(base_dir):
    """创建演示用的样本文件"""
    file_structure = {
        "docs/guide.md": "# RAG使用指南\n\nRAG（检索增强生成）是一种结合文档检索与生成式AI的技术。\n\n## 原理\n\nRAG通过以下步骤工作：\n1. 检索相关文档\n2. 提取关键信息\n3. 结合知识生成答案\n\n## 优势\n\n- 减少幻觉\n- 提供最新信息\n- 支持大规模知识库",
        
        "docs/api.md": "# LongContextRAG API\n\n## 初始化\n\n```python\nrag = LongContextRAG(llm, args, path)\n```\n\n## 主要方法\n\n- `search(query)`: 搜索相关文档\n- `stream_chat_oai(conversations)`: 流式问答交互",
        
        "src/example.py": "# 加法和减法演示\n\ndef add(a, b):\n    \"\"\"计算两个数的和\"\"\"\n    return a + b\n\ndef subtract(a, b):\n    \"\"\"计算两个数的差\"\"\"\n    return a - b\n\n# 演示\nprint(f\"5 + 3 = {add(5, 3)}\")\nprint(f\"5 - 3 = {subtract(5, 3)}\")",
        
        "src/utils/math_helpers.py": "# 数学辅助函数\n\ndef multiply(a, b):\n    \"\"\"计算两个数的乘积\"\"\"\n    return a * b\n\ndef divide(a, b):\n    \"\"\"计算两个数的商\"\"\"\n    if b == 0:\n        raise ValueError(\"除数不能为零\")\n    return a / b\n\ndef is_even(n):\n    \"\"\"判断一个数是否为偶数\"\"\"\n    return n % 2 == 0",
        
        "README.md": "# 演示项目\n\n这是一个用于演示LongContextRAG功能的示例项目。\n\n## 目录结构\n\n- `docs/`: 文档目录\n- `src/`: 源代码目录\n\n## 使用方法\n\n查看docs目录下的文档了解更多信息。"
    }
    
    for file_path, content in file_structure.items():
        full_path = os.path.join(base_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    logger.info(f"示例文件创建完成，位置: {base_dir}")

def main():
    # 检查当前运行目录是否为examples目录
    current_dir = os.path.basename(os.getcwd())
    if current_dir != "examples":
        logger.error("错误：当前脚本必须在examples目录下运行")
        logger.error("请切换到examples目录并执行: python demo_long_context_rag.py")
        sys.exit(1)
        
    logger.info("--- 开始演示 LongContextRAG ---")
    
    # 1. 准备演示环境
    base_dir = "sample_rag_demo"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(base_dir)
    create_sample_files(base_dir)

    os.chdir(base_dir)
    
    # 2. 初始化配置参数
    args = AutoCoderArgs(
        source_dir=os.getcwd(),        
        rag_context_window_limit=8000,  # 上下文窗口限制
        rag_doc_filter_relevance=3,     # 相关性过滤阈值
        full_text_ratio=0.7,            # 全文比例
        segment_ratio=0.2,              # 分段比例
        index_filter_workers=1,         # 过滤工作线程数
        required_exts=".py,.md",        # 需要处理的文件扩展名
        monitor_mode=False,             # 监控模式
        enable_hybrid_index=False       # 混合索引
    )
    logger.info(f"配置参数: {args}")
    
    try:
        # Use singleton pattern to get/create monitor instance
        # FileMonitor ensures only one instance runs per root_dir
        monitor = FileMonitor(args.source_dir)
        if not monitor.is_running():
            # TODO: Register specific callbacks here if needed in the future
            # Example: monitor.register(os.path.join(args.source_dir, "specific_file.py"), my_callback)
            monitor.start()
            logger.info(f"File monitor started for directory: {args.source_dir}")
        else:
            # Log if monitor was already running (e.g., started by another part of the app)
            # Check if the existing monitor's root matches the current request
            if monitor.root_dir == os.path.abspath(args.source_dir):
                    logger.info(f"File monitor already running for directory: {monitor.root_dir}")
            else:
                    logger.warning(f"File monitor is running for a different directory ({monitor.root_dir}), cannot start a new one for {args.source_dir}.")
        
        logger.info(f"Getting rules for {args.source_dir}")
        _ = get_rules(args.source_dir) 
    except Exception as e:
        logger.error(f"Error initializing file monitor: {e}")

    # 初始化token计数器,注意，这个要放在 fileMonitor 初始化之后因为auto_coder_runner会触发 FileMonitor的初始化
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()    
    
    # 3. 获取LLM实例
    logger.info("正在初始化LLM...")
    llm = get_single_llm("v3_chat", product_mode="lite")
    logger.info(f"LLM初始化完成: {llm.default_model_name}")
    
    # 4. 实例化LongContextRAG
    logger.info("正在初始化LongContextRAG...")
    from autocoder.rag.long_context_rag import LongContextRAG
    rag = LongContextRAG(
        llm=llm,
        args=args,
        path=base_dir,
        tokenizer_path=None  # 使用默认tokenizer
    )
    logger.info("LongContextRAG初始化完成")
    
    # 5. 执行搜索演示
    logger.info("\n--- 搜索演示 ---")
    query = "如何进行加法和减法运算?"
    logger.info(f"搜索查询: '{query}'")
    
    start_time = time.time()
    results = rag.search(query)
    search_time = time.time() - start_time
    
    logger.info(f"搜索耗时: {search_time:.2f}秒")
    logger.info(f"找到结果数量: {len(results)}")
    
    for i, result in enumerate(results):
        logger.info(f"\n结果 {i+1}:")
        logger.info(f"来源: {result.module_name}")
        logger.info(f"内容摘要: {result.source_code[:100]}...")
    
    # 6. 执行聊天演示
    logger.info("\n--- 聊天演示 ---")
    conversations = [
        {"role": "user", "content": "请解释RAG技术的基本原理和优势"}
    ]
    logger.info(f"聊天输入: {conversations[-1]['content']}")
    
    start_time = time.time()
    generator, context = rag.stream_chat_oai(conversations)
    
    logger.info("生成回答中...")
    answer = []
    for chunk, meta in generator:
        answer.append(chunk)
        # 打印进度信息
        if meta and meta.reasoning_content:
            logger.info(f"思考: {meta.reasoning_content}")
    
    chat_time = time.time() - start_time
    logger.info(f"聊天耗时: {chat_time:.2f}秒")
    
    if context:
        logger.info(f"使用的上下文文档: {', '.join(context)}")
    
    logger.info("\n最终回答:")
    logger.info("".join(answer))
    
    # 7. 执行多轮对话演示
    logger.info("\n--- 多轮对话演示 ---")
    conversations.append({"role": "assistant", "content": "".join(answer)})
    conversations.append({"role": "user", "content": "在这个项目中我可以找到哪些数学运算的例子?"})
    
    logger.info(f"多轮对话输入: {conversations[-1]['content']}")
    
    start_time = time.time()
    generator, context = rag.stream_chat_oai(conversations)
    
    logger.info("生成回答中...")
    answer = []
    for chunk, meta in generator:
        answer.append(chunk)
        if meta and meta.reasoning_content:
            logger.info(f"思考: {meta.reasoning_content}")
    
    chat_time = time.time() - start_time
    logger.info(f"多轮对话耗时: {chat_time:.2f}秒")
    
    if context:
        logger.info(f"使用的上下文文档: {', '.join(context)}")
    
    logger.info("\n最终回答:")
    logger.info("".join(answer))
    
    # 8. 清理演示环境
    logger.info("\n清理演示环境...")
    shutil.rmtree(base_dir)
    logger.info(f"已删除目录: {base_dir}")
    
    logger.info("--- LongContextRAG 演示结束 ---")

if __name__ == "__main__":
    main() 