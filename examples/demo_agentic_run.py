#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
from typing import Dict, Any, List, Optional
from loguru import logger
from autocoder.agent.base_agentic.base_agent import BaseAgent
from autocoder.common import AutoCoderArgs, git_utils, SourceCodeList, SourceCode

# 定义一个简单的BaseAgent子类
class SimpleAgent(BaseAgent):
    def __init__(self, name: str, llm, 
                 files: SourceCodeList, 
                 args: AutoCoderArgs, 
                 conversation_history: Optional[List[Dict[str, Any]]] = None):
        super().__init__(name, llm, files, args, conversation_history)

def main():
    parser = argparse.ArgumentParser(description="演示BaseAgent的agentic_run方法")
    parser.add_argument("--source_dir", type=str, default=".", help="项目根目录")
    parser.add_argument("--query", type=str, default="请告诉我这个项目的结构", help="用户查询")
    parser.add_argument("--event_file", type=str, default=".auto-coder/events-demo.jsonl", help="事件文件")
    parser.add_argument("--model", type=str, default="v3_chat", help="使用的大模型")
    parser.add_argument("--product_mode", type=str, default="lite", help="产品模式")
    args = parser.parse_args()
    
    # 确保事件文件目录存在
    os.makedirs(os.path.dirname(os.path.join(args.source_dir, args.event_file)), exist_ok=True)
    
    # 1. 初始化FileMonitor（必须最先进行）
    try:
        from autocoder.common.file_monitor.monitor import FileMonitor
        monitor = FileMonitor(args.source_dir)
        if not monitor.is_running():
            monitor.start()
            logger.info(f"文件监控已启动: {args.source_dir}")
        else:
            logger.info(f"文件监控已在运行中: {monitor.root_dir}")
            
        # 2. 加载规则文件
        from autocoder.common.rulefiles.autocoderrules_utils import get_rules
        _ = get_rules(args.source_dir)
        logger.info(f"已加载规则")
    except Exception as e:
        logger.error(f"初始化文件监控出错: {e}")
    
    # 3. 加载tokenizer (必须在前两步之后)
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()
    logger.info("Tokenizer加载完成")
    
    # 4. 初始化LLM
    from autocoder.utils.llms import get_single_llm
    llm = get_single_llm(args.model, product_mode=args.product_mode)
    logger.info(f"LLM初始化完成: {llm.default_model_name}")
    
    # 5. 准备其他必要组件
    from autocoder.common import AutoCoderArgs, SourceCodeList
    from autocoder.agent.base_agentic.types import AgentRequest, BaseTool
    
    # 转换命令行参数为AutoCoderArgs
    auto_coder_args = AutoCoderArgs(
        source_dir=args.source_dir,
        event_file=args.event_file,
        model=args.model,
        product_mode=args.product_mode,
        conversation_prune_safe_zone_tokens=400,
    )
    
    # 创建源代码列表
    files = SourceCodeList(sources=[])
        
    agent = SimpleAgent(
        name="DemoAgent",
        llm=llm, 
        files=files, 
        args=auto_coder_args
    )
    
    # 创建用户请求
    request = AgentRequest(
        user_input=args.query,
        environment="development",
        mode="ACT",
    )
    
    # 运行agentic_run并处理输出
    logger.info(f"开始执行agentic_run，用户查询: {args.query}")
    
    # 方式1: 使用run_in_terminal方法在控制台中展示交互过程
    agent.run_in_terminal(request)        
    
    logger.info("agentic_run执行完成")

if __name__ == "__main__":
    main() 