"""
演示BaseAgent类和byzerllm.prompt装饰器的基本用法
展示如何创建一个简单的代理，并使用prompt装饰器实现动态模板渲染
"""
import os
import argparse
import shutil
from loguru import logger
import byzerllm
from typing import Dict, Any, List

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="演示BaseAgent和byzerllm.prompt装饰器的用法")
    parser.add_argument("--source_dir", type=str, default="demo_agent_workspace",
                        help="工作目录路径，将在此目录下创建示例文件")
    parser.add_argument("--model", type=str, default="v3_chat",
                        help="使用的LLM模型")
    parser.add_argument("--product_mode", type=str, default="lite",
                        help="产品模式")
    parser.add_argument("--event_file", type=str, default="",
                        help="事件文件路径")
    return parser.parse_args()

# 准备演示环境
def prepare_demo_environment(base_dir):
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    
    # 创建示例源代码文件
    os.makedirs(os.path.join(base_dir, "src"), exist_ok=True)
    with open(os.path.join(base_dir, "src", "example.py"), "w") as f:
        f.write("""
def hello_world():
    """Demo function for testing"""
    print("Hello, World!")
    return "Hello, World!"
""")
    
    # 创建示例文档文件
    os.makedirs(os.path.join(base_dir, "docs"), exist_ok=True)
    with open(os.path.join(base_dir, "docs", "guide.md"), "w") as f:
        f.write("""
# 使用指南

这是一个演示文档，用于测试BaseAgent的功能。

## 功能列表

1. 解析文件
2. 生成代码
3. 回答问题
""")
    
    logger.info(f"创建演示环境于: {base_dir}")
    return base_dir

def main():
    # 解析参数
    args = parse_args()
    
    # 准备演示环境
    source_dir = prepare_demo_environment(args.source_dir)
    logger.info(f"已准备演示环境: {source_dir}")
    
    # 1. 初始化FileMonitor（必须最先进行）
    try:
        from autocoder.common.file_monitor.monitor import FileMonitor
        monitor = FileMonitor(source_dir)
        if not monitor.is_running():
            monitor.start()
            logger.info(f"文件监控已启动: {source_dir}")
        else:
            logger.info(f"文件监控已在运行中: {monitor.root_dir}")
    except Exception as e:
        logger.error(f"初始化文件监控出错: {e}")
    
    # 2. 加载规则文件
    try:
        from autocoder.common.rulefiles.autocoderrules_utils import get_rules
        rules = get_rules(source_dir)
        logger.info(f"已加载规则: {len(rules)} 条")
    except Exception as e:
        logger.error(f"加载规则出错: {e}")
    
    # 3. 加载tokenizer (必须在前两步之后)
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()
    logger.info("Tokenizer加载完成")
    
    # 4. 初始化LLM
    from autocoder.utils.llms import get_single_llm
    llm = get_single_llm(args.model, product_mode=args.product_mode)
    logger.info(f"LLM初始化完成: {llm.default_model_name}")
    
    # 5. 配置AutoCoderArgs
    from autocoder.common import AutoCoderArgs
    from autocoder.common import SourceCodeList, SourceCode
    
    agent_args = AutoCoderArgs(
        source_dir=source_dir,
        model=args.model,
        product_mode=args.product_mode,
        event_file=args.event_file or os.path.join(source_dir, "events.json"),
        file="",
        conversation_prune_safe_zone_tokens=100,
        enable_active_context_in_generate=True,
        ignore_clean_shadows=True,
    )
    
    # 准备源代码列表
    files = SourceCodeList()
    files.add_source(SourceCode(
        module_name="src/example.py",
        content=open(os.path.join(source_dir, "src", "example.py")).read()
    ))
    files.add_source(SourceCode(
        module_name="docs/guide.md",
        content=open(os.path.join(source_dir, "docs", "guide.md")).read()
    ))
    
    # 6. 创建一个自定义Agent来展示byzerllm.prompt装饰器的用法
    from autocoder.agent.base_agentic import BaseAgent
    from autocoder.agent.base_agentic.types import BaseTool, AgentRequest
    
    class DemoAgent(BaseAgent):
        """
        演示用的Agent，展示byzerllm.prompt装饰器的用法
        """
        
        @byzerllm.prompt()
        def generate_summary(self, task_name: str, files: List[str], user_query: str) -> Dict[str, Any]:
            """
            为{{ task_name }}任务生成项目文件摘要
            
            项目包含以下文件:
            {% for file in files %}
            - {{ file }}
            {% endfor %}
            
            用户查询: {{ user_query }}
            
            现在我将为您分析这些文件，请稍等...
            """
            # 准备模板上下文
            context = {
                "task_name": task_name,
                "files": files,
                "user_query": user_query
            }
            return context
        
        def get_tool_display_message(self, tool: BaseTool) -> str:
            """
            实现基类的抽象方法，获取工具在终端中的显示消息
            """
            return f"执行工具: {type(tool).__name__}"
        
        def apply_changes(self):
            """
            实现基类的方法，应用变更
            """
            logger.info("应用变更...")
            
    # 7. 创建Agent实例
    demo_agent = DemoAgent(
        llm=llm,
        files=files,
        args=agent_args,
        conversation_history=[]
    )
    
    # 8. 展示prompt装饰器的使用
    logger.info("开始演示byzerllm.prompt装饰器的用法...")
    
    # 8.1 使用generate_summary方法，直接获取渲染后的prompt
    task = "代码分析"
    file_list = ["src/example.py", "docs/guide.md"]
    query = "这个项目有哪些功能？"
    
    # 获取渲染后的prompt
    rendered_prompt = demo_agent.generate_summary.prompt(
        task_name=task,
        files=file_list,
        user_query=query
    )
    
    logger.info("渲染后的prompt内容:")
    logger.info("-" * 40)
    logger.info(rendered_prompt)
    logger.info("-" * 40)
    
    # 8.2 使用LLM和渲染后的prompt生成回答
    logger.info("使用LLM和渲染后的prompt生成回答...")
    
    response = llm.chat_oai([
        {"role": "system", "content": "你是一个助手，负责分析项目文件并回答问题。"},
        {"role": "user", "content": rendered_prompt}
    ])
    
    logger.info("LLM回答:")
    logger.info("-" * 40)
    logger.info(response[0]["content"])
    logger.info("-" * 40)
    
    # 9. 演示使用Agent的analyze方法（简单演示）
    logger.info("开始演示Agent的analyze方法...")
    
    user_input = "请分析src/example.py文件的功能"
    request = AgentRequest(user_input=user_input)
    
    logger.info(f"用户输入: {user_input}")
    logger.info("运行Agent...")
    
    # 由于Agent的实现较为复杂，这里只模拟一下运行过程
    logger.info("模拟Agent运行过程 (实际使用时请使用run_with_events或run_in_terminal方法)")
    
    # 10. 清理环境
    logger.info(f"演示完成，保留演示环境以供检查: {source_dir}")
    logger.info("如需清理环境，请手动删除该目录")

if __name__ == "__main__":
    main() 