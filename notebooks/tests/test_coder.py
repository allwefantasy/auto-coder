import os
from autocoder.agent.coder import Coder
import byzerllm
import asyncio

# 初始化 LLM
llm = byzerllm.ByzerLLM.from_default_model(model="deepseek_chat")

# 创建 Coder 实例
coder = Coder(llm)

# 定义测试项目路径
test_project_path = os.path.join(os.getcwd(), "test_react_project")


# 定义测试任务
test_task = """
创建一个使用 React + TypeScript + Tailwind CSS 的项目
"""


asyncio.run(coder.start_task(test_task))
