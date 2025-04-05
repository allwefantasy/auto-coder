import os
import sys
from typing import Iterator, Union, Generator
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.common import AutoCoderArgs, SourceCodeList
from autocoder.utils.llms import get_single_llm
from autocoder.agent.agentic_edit import (
    AgenticEdit,
    MemoryConfig,
    BaseTool,
    PlainTextOutput,
    ExecuteCommandTool,
    ReadFileTool,
    WriteToFileTool
)
from autocoder.common import AutoCoderArgs, SourceCode, SourceCodeList
from autocoder.agent.agentic_edit_types import AgenticEditRequest
from loguru import logger
from autocoder.rag.token_counter import count_tokens
from autocoder.helper.project_creator import ProjectCreator, FileCreatorFactory

def file_to_source_code(file_path: str) -> SourceCode:
    """将文件转换为 SourceCode 对象"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return SourceCode(module_name=file_path, source_code=content, tokens=count_tokens(content))


def get_source_code_list(project_dir: str) -> SourceCodeList:
    """获取项目中所有 Python 文件的 SourceCode 列表"""
    source_codes = []
    
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                source_codes.append(file_to_source_code(file_path))
    
    return SourceCodeList(sources=source_codes)

# 1. Load tokenizer (Important for token counting if needed)
load_tokenizer()
 # 创建示例项目
creator = ProjectCreator(
    project_name="test_project",
    project_type="python",  # 可以切换为 "react" 创建 React 项目
    query="给计算器添加乘法和除法功能，并为所有方法添加类型提示"
)
project_dir = creator.create_project()
print(f"创建了示例项目: {project_dir}")

# 获取项目中的源代码
source_code_list = get_source_code_list(project_dir)
print(f"获取到 {len(source_code_list.sources)} 个源代码文件")

## 切换工作目录到 project_dir
os.chdir(project_dir)

# 获取 LLM 实例
llm = get_single_llm("v3_chat", product_mode="lite")
print("初始化 LLM 完成")

args = AutoCoderArgs(
    source_dir=project_dir,        
    model="v3_chat",
    product_mode="lite",
    target_file= os.path.join(project_dir, "output.txt"),
    file=os.path.join(project_dir, "actions", "000000000001_chat_action.yml")
)

# 3. Get LLM instance
llm = get_single_llm(args.model, product_mode=args.product_mode)

#    - MemoryConfig (dummy for this example)
def dummy_save_memory(memory: dict):
    logger.info("Dummy save memory called.")
memory_config = MemoryConfig(memory={}, save_memory_func=dummy_save_memory)
#    - Conversation history (empty for this example)
conversation_history = []

# 5. Instantiate AgenticEdit
agentic_editor = AgenticEdit(
    llm=llm,
    conversation_history=conversation_history,
    files=source_code_list,
    args=args,
    memory_config=memory_config,
    # command_config is optional and not needed for this specific demo
)


agentic_editor.analyze(AgenticEditRequest(user_input="优化下代码"))