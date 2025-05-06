"""
演示BaseAgent类和byzerllm.prompt装饰器的基本用法
展示如何创建一个简单的代理，并使用prompt装饰器实现动态模板渲染
"""
import os
import argparse
import shutil
from loguru import logger
import byzerllm
from typing import Dict, Any, List, Union, Optional
from autocoder.agent.base_agentic.base_agent import BaseAgent
from autocoder.agent.base_agentic.types import BaseTool, AgentRequest, ToolResult
from autocoder.agent.base_agentic.tool_registry import ToolRegistry
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ToolDescription, ToolExample
from autocoder.common import AutoCoderArgs
from autocoder.common import SourceCodeList, SourceCode
from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="演示BaseAgent和byzerllm.prompt装饰器的用法")    
    parser.add_argument("--model", type=str, default="v3_chat",
                        help="使用的LLM模型")
    parser.add_argument("--product_mode", type=str, default="lite",
                        help="产品模式")
    parser.add_argument("--event_file", type=str, default="",
                        help="事件文件路径")
    return parser.parse_args()

# 准备演示环境
def prepare_demo_environment():    
    base_dir = os.path.join(os.getcwd(), "demo_agent_workspace")  
    # 创建示例源代码文件
    os.makedirs(os.path.join(base_dir, "src"), exist_ok=True)
    with open(os.path.join(base_dir, "src", "example.py"), "w") as f:
        f.write("""
def hello_world():    
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
    source_dir = prepare_demo_environment()
    os.chdir(source_dir)    
    
    logger.info(f"已准备演示环境: {source_dir}")    
    
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
    
    # 2. 加载规则文件
    try:        
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
    
    agent_args = AutoCoderArgs(
        source_dir=source_dir,
        model=args.model,
        product_mode=args.product_mode,
        event_file=args.event_file or os.path.join(source_dir, "events.json"),
        file="",        
        enable_active_context_in_generate=True,
        ignore_clean_shadows=True,
    )
    
    # 准备源代码列表
    files = SourceCodeList(sources=[SourceCode(
        module_name="src/example.py",
        source_code=open(os.path.join(source_dir, "src", "example.py")).read()
    ), SourceCode(
        module_name="docs/guide.md",
        source_code=open(os.path.join(source_dir, "docs", "guide.md")).read()
    )])
    
    # 6. 创建一个自定义Agent来展示byzerllm.prompt装饰器的用法    
    
    # 定义Echo工具类 - 继承自BaseTool
    class EchoTool(BaseTool):
        message: str  # 要回显的消息

    # 创建Echo工具解析器 - 继承自BaseToolResolver
    class EchoToolResolver(BaseToolResolver):
        def __init__(self, agent, tool, args):
            super().__init__(agent, tool, args)
            self.tool: EchoTool = tool  # 提供类型提示
        
        def resolve(self) -> ToolResult:
            """实现Echo工具的解析逻辑"""
            try:
                # 简单地返回消息
                message = self.tool.message
                return ToolResult(success=True, message="Echo工具执行成功", content=message)
            except Exception as e:
                return ToolResult(success=False, message=f"Echo工具执行失败: {str(e)}")

    # 注册Echo工具
    def register_echo_tool():
        # 准备工具描述
        description = ToolDescription(
            description="回显输入的消息",
            parameters="message: 要回显的消息内容",
            usage="用于简单地回显用户输入的消息"
        )
        
        # 准备工具示例
        example = ToolExample(
            title="Echo工具使用示例",
            body="""<echo>
<message>这是一条测试消息</message>
</echo>"""
        )
        
        # 注册工具
        ToolRegistry.register_tool(
            tool_tag="echo",  # XML标签名
            tool_cls=EchoTool,  # 工具类
            resolver_cls=EchoToolResolver,  # 解析器类
            description=description,  # 工具描述
            example=example,  # 工具示例
            use_guideline="此工具用于简单地回显用户输入的消息，适用于测试和调试场景。"  # 使用指南
        )

    class DemoAgent(BaseAgent):
        """
        演示用的Agent，展示byzerllm.prompt装饰器的用法
        """
        def __init__(self, name: str, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], files: SourceCodeList, args: AutoCoderArgs, conversation_history: Optional[List[Dict[str, Any]]] = None):
            super().__init__(name, llm, files, args, conversation_history)
            # 注册Echo工具
            register_echo_tool()
            
    # 7. 创建Agent实例
    demo_agent = DemoAgent(
        name="DemoAgent",
        llm=llm,
        files=files,
        args=agent_args,
        conversation_history=[]
    )
    
    # 8. 展示prompt装饰器的使用
    logger.info("开始演示byzerllm.prompt装饰器的用法...")    
    
    # 9. 演示使用Agent的analyze方法（简单演示）
    logger.info("开始演示Agent的analyze方法...")
    
    user_input = "请分析src/example.py文件的功能"
    request = AgentRequest(user_input=user_input)
    
    logger.info(f"用户输入: {user_input}")
    logger.info("运行Agent...")
    demo_agent.run_in_terminal(request)
    
    # 由于Agent的实现较为复杂，这里只模拟一下运行过程
    logger.info("模拟Agent运行过程 (实际使用时请使用run_with_events或run_in_terminal方法)")
    
    # 10. 添加Echo工具演示
    user_input = "请用echo工具输出：你好"
    request = AgentRequest(user_input=user_input)
    
    logger.info(f"用户输入: {user_input}")
    logger.info("运行Agent...")
    demo_agent.run_in_terminal(request)
    
    # 11. 清理环境
    logger.info(f"演示完成，保留演示环境以供检查: {source_dir}")
    logger.info("如需清理环境，请手动删除该目录")

if __name__ == "__main__":
    main() 