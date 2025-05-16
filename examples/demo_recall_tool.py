"""
专门用于测试 RecallTool 的演示文件
"""
import os
import argparse
from loguru import logger
import byzerllm
from typing import Dict, Any, List, Union, Optional
import json

from autocoder.agent.base_agentic.base_agent import BaseAgent
from autocoder.agent.base_agentic.types import AgentRequest
from autocoder.common import AutoCoderArgs
from autocoder.common import SourceCodeList
from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.rag.tools import register_recall_tool
from autocoder.rag.long_context_rag import LongContextRAG

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="测试 RecallTool 的演示")    
    parser.add_argument("--model", type=str, default="v3_chat",
                        help="使用的LLM模型")
    parser.add_argument("--product_mode", type=str, default="lite",
                        help="产品模式")
    parser.add_argument("--event_file", type=str, default="",
                        help="事件文件路径")
    parser.add_argument("--source_dir", type=str, default="",
                        help="源代码目录，如果为空则使用当前目录")
    parser.add_argument("--query", type=str, default="如何实现文件监控功能",
                        help="搜索查询")
    parser.add_argument("--max_tokens", type=int, default=4000,
                        help="最大返回令牌数")
    return parser.parse_args()

# 创建测试用的 Agent
class RecallToolTestAgent(BaseAgent):
    """
    专门用于测试 RecallTool 的 Agent
    """
    def __init__(self, name: str, 
                 llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], 
                 args: AutoCoderArgs, 
                 conversation_history: Optional[List[Dict[str, Any]]] = None):
        super().__init__(name, llm, SourceCodeList(sources=[]), args, conversation_history)
        self.rag = LongContextRAG(llm=llm, args=args, path=args.source_dir)
        # 只注册 RecallTool
        register_recall_tool()

def main():
    # 解析参数
    args = parse_args()
    
    # 设置源代码目录
    source_dir = args.source_dir or os.getcwd()
    os.chdir(source_dir)
    
    logger.info(f"使用源代码目录: {source_dir}")
    
    # 1. 初始化FileMonitor（必须最先进行）
    try:        
        monitor = FileMonitor(source_dir)
        if not monitor.is_running():
            monitor.start()
            logger.info(f"文件监控已启动: {source_dir}")
        else:
            logger.info(f"文件监控已在运行中: {monitor.root_dir}")
    except Exception as e:
        logger.error(f"初始化文件监控出错: {e}")
    
    # 2. 加载tokenizer (必须在FileMonitor之后)
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()
    logger.info("Tokenizer加载完成")
    
    # 3. 初始化LLM
    from autocoder.utils.llms import get_single_llm
    llm = get_single_llm(args.model, product_mode=args.product_mode)
    logger.info(f"LLM初始化完成: {llm.default_model_name}")
    
    # 4. 配置AutoCoderArgs
    agent_args = AutoCoderArgs(
        source_dir=source_dir,
        model=args.model,
        product_mode=args.product_mode,
        event_file=args.event_file or os.path.join(source_dir, "events.json"),
        doc_dir=source_dir  # 设置文档目录，供RAG工具使用
    )
    
    # 5. 创建Agent实例
    test_agent = RecallToolTestAgent(
        name="RecallToolTestAgent",
        llm=llm,
        args=agent_args,
        conversation_history=[]
    )
    
    # 6. 构建测试请求
    query = args.query
    max_tokens = args.max_tokens
    
    logger.info(f"测试查询: {query}")
    logger.info(f"最大令牌数: {max_tokens}")
    
    test_request = AgentRequest(user_input=f"""
请使用召回工具获取与以下查询相关的代码内容：

<recall>
<query>{query}</query>
<max_tokens>{max_tokens}</max_tokens>
</recall>
""")
    
    # 7. 运行测试
    logger.info("开始测试RecallTool...")
    test_agent.run_in_terminal(test_request)
    
    # 8. 输出结果
    logger.info("测试完成")

if __name__ == "__main__":
    main()
