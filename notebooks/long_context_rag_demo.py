#!/usr/bin/env python
# coding: utf-8

"""
LongContextRAG 使用示例

此脚本演示了如何使用LongContextRAG进行上下文增强的对话。
包括：
- 设置模拟源代码文件
- 初始化LLM模型
- 配置RAG参数
- 执行查询并处理结果
"""

import os
import sys
import tempfile
import time
import json
from typing import List, Dict, Any
from pathlib import Path

import byzerllm
from loguru import logger
from autocoder.rag.long_context_rag import LongContextRAG
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.rag.relevant_utils import FilterDoc, DocRelevance, TaskTiming

# 配置日志
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("long_context_rag_demo.log", rotation="100 MB", level="DEBUG")

def setup_mock_codebase(temp_dir: str) -> None:
    """创建模拟源代码文件用于测试"""
    # 创建一些模拟的源代码文件
    python_files = {
        "main.py": """
def main():
    \"\"\"主程序入口\"\"\"
    print("Hello, welcome to the LongContextRAG demo!")
    data = load_data()
    result = process_data(data)
    save_result(result)
    return result

def load_data():
    \"\"\"加载数据\"\"\"
    return {"name": "RAG Demo", "version": "1.0"}

if __name__ == "__main__":
    main()
""",
        "data_processor.py": """
def process_data(data):
    \"\"\"
    处理输入数据
    
    参数:
        data: 输入数据字典
    
    返回:
        processed_data: 处理后的数据
    \"\"\"
    if not data:
        raise ValueError("Input data cannot be empty")
    
    processed_data = data.copy()
    processed_data["processed"] = True
    processed_data["timestamp"] = "2023-05-30"
    
    return processed_data

def save_result(result):
    \"\"\"
    保存处理结果
    
    参数:
        result: 处理后的数据
    \"\"\"
    print(f"Saving result: {result}")
    # 实际应用中，这里可能会写入文件或数据库
    return True
""",
        "utils/helpers.py": """
import json
import os

def read_json_file(filepath):
    \"\"\"
    读取JSON文件
    
    参数:
        filepath: JSON文件路径
    
    返回:
        data: JSON数据
    \"\"\"
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return data

def write_json_file(data, filepath):
    \"\"\"
    写入JSON文件
    
    参数:
        data: 要写入的数据
        filepath: 目标文件路径
    \"\"\"
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return True
"""
    }

    # 创建文件夹结构
    os.makedirs(os.path.join(temp_dir, "utils"), exist_ok=True)
    
    # 写入文件
    for filepath, content in python_files.items():
        full_path = os.path.join(temp_dir, filepath)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    logger.info(f"创建了 {len(python_files)} 个模拟源码文件在 {temp_dir}")

def run_rag_demo(source_dir: str, model_name: str = "v3_chat", use_pro_mode: bool = False):
    """运行RAG演示"""
    logger.info("=== 开始 LongContextRAG 演示 ===")
    
    # 1. 设置参数
    args = AutoCoderArgs(
        product_mode="pro" if use_pro_mode else "lite",
        rag_type="simple",
        rag_doc_filter_relevance=2,
        rag_context_window_limit=16000,
        full_text_ratio=0.5,
        segment_ratio=0.3,
        index_filter_workers=3,
        enable_hybrid_index=False,
        disable_segment_reorder=False,
        required_exts=".py",
        monitor_mode=False,
        disable_inference_enhance=True
    )
    
    logger.info(f"使用模式: {args.product_mode}")
    logger.info(f"源代码目录: {source_dir}")
    
    # 2. 初始化LLM
    llm = None
    if args.product_mode == "pro":
        # Pro模式: 使用Ray集群
        logger.info("初始化Pro模式LLM...")
        byzerllm.connect_cluster()
        llm = byzerllm.ByzerLLM()
        llm.skip_nontext_check = True
        llm.setup_default_model_name(model_name)
    else:
        # Lite模式: 使用云端API
        logger.info("初始化Lite模式LLM...")
        from autocoder import models as models_module
        model_info = models_module.get_model_by_name(model_name)
        llm = byzerllm.SimpleByzerLLM(default_model_name=model_name)
        llm.deploy(
            model_path="",
            pretrained_model_type=model_info["model_type"],
            udf_name=model_name,
            infer_params={
                "saas.base_url": model_info["base_url"],
                "saas.api_key": model_info["api_key"],
                "saas.model": model_info["model_name"],
                "saas.is_reasoning": model_info["is_reasoning"]
            }
        )
    
    # 3. 创建辅助子模型
    if args.product_mode == "pro":
        # 在Pro模式下可以配置子模型
        recall_model = byzerllm.ByzerLLM()
        recall_model.setup_default_model_name(model_name)
        recall_model.skip_nontext_check = True
        llm.setup_sub_client("recall_model", recall_model)
        
        chunk_model = byzerllm.ByzerLLM()
        chunk_model.setup_default_model_name(model_name)
        llm.setup_sub_client("chunk_model", chunk_model)
    
    # 4. 查找tokenizer路径
    try:
        import pkg_resources
        tokenizer_path = pkg_resources.resource_filename("autocoder", "data/tokenizer.json")
        if not os.path.exists(tokenizer_path):
            logger.warning(f"Tokenizer文件不存在: {tokenizer_path}, 将使用默认tokenizer")
            tokenizer_path = None
    except Exception as e:
        logger.warning(f"获取tokenizer失败: {str(e)}, 将使用默认tokenizer")
        tokenizer_path = None
    
    # 5. 实例化LongContextRAG
    logger.info("初始化LongContextRAG...")
    rag = LongContextRAG(
        llm=llm,
        args=args,
        path=source_dir,
        tokenizer_path=tokenizer_path
    )
    
    # 6. 执行查询
    conversations = [
        {"role": "user", "content": "请解释data_processor.py中的process_data函数是做什么的?"}
    ]
    
    logger.info("执行RAG查询...")
    start_time = time.time()
    
    try:
        # 使用stream_chat_oai方法获取结果
        chunks_generator, context = rag.stream_chat_oai(
            conversations=conversations,
            model=model_name
        )
        
        # 处理流式结果
        full_response = ""
        logger.info("接收流式响应:")
        for chunk in chunks_generator:            
            print(chunk[0], end="", flush=True)
            full_response += chunk[0]
        print("\n")
        
        # 输出上下文信息
        logger.info(f"查询使用的上下文文件: {', '.join(context)}")
        
        # 记录查询时间
        query_time = time.time() - start_time
        logger.info(f"查询完成，耗时: {query_time:.2f}秒")
        
        return {
            "response": full_response,
            "context": context,
            "query_time": query_time
        }
    
    except Exception as e:
        logger.error(f"查询过程中出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    # 创建临时目录存放测试文件
    with tempfile.TemporaryDirectory() as temp_dir:
        # 设置模拟代码库
        setup_mock_codebase(temp_dir)
        
        # 选择模式
        use_pro_mode = False  # 默认使用Lite模式
        if len(sys.argv) > 1 and sys.argv[1].lower() == "pro":
            use_pro_mode = True
        
        # 选择模型
        model_name = "v3_chat"  # 默认模型
        if len(sys.argv) > 2:
            model_name = sys.argv[2]
        
        # 运行演示
        result = run_rag_demo(temp_dir, model_name, use_pro_mode)
        
        if result:
            logger.info("=== 演示完成 ===")
        else:
            logger.error("=== 演示失败 ===") 