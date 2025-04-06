import os
import sys
import time
from autocoder.auto_coder_runner import load_tokenizer, configure_logger
from autocoder.common import AutoCoderArgs, SourceCode, SourceCodeList, SourceCode
from autocoder.utils.llms import get_single_llm
from autocoder.common.v2.agent.agentic_edit import AgenticEdit, MemoryConfig
from autocoder.common.v2.agent.agentic_edit_types import AgenticEditRequest
from autocoder.common.v2.agent.agentic_edit_tools import (
    ExecuteCommandToolResolver, ReadFileToolResolver, WriteToFileToolResolver,
    ReplaceInFileToolResolver, SearchFilesToolResolver, ListFilesToolResolver,
    ListCodeDefinitionNamesToolResolver, AskFollowupQuestionToolResolver,
    AttemptCompletionToolResolver, PlanModeRespondToolResolver, UseMcpToolResolver
)
from autocoder.common.v2.agent.agentic_edit_types import (
    ExecuteCommandTool, ReadFileTool, WriteToFileTool,
    ReplaceInFileTool, SearchFilesTool, ListFilesTool,
    ListCodeDefinitionNamesTool, AskFollowupQuestionTool,
    AttemptCompletionTool, PlanModeRespondTool, UseMcpTool
)
from loguru import logger

configure_logger()
load_tokenizer()

# prepare a dummy project directory
project_dir = os.path.abspath("test_tools_project")
os.makedirs(project_dir, exist_ok=True)
dummy_file_path = os.path.join(project_dir, "dummy.txt")
dummy_file_content = "Hello World\nThis is a dummy file.\nLine 3.\n"
with open(dummy_file_path, "w", encoding="utf-8") as f:
    f.write(dummy_file_content)

args = AutoCoderArgs(
    source_dir=project_dir,
    model="quasar-alpha",
    product_mode="lite",
    target_file=os.path.join(project_dir, "output.txt"),
    file=os.path.join(project_dir, "actions", "placeholder_action.yml")
)

# Setup dummy llm and memory config
llm = get_single_llm(args.model, product_mode=args.product_mode)
def dummy_save_memory(memory: dict):
    pass
memory_config = MemoryConfig(memory={}, save_memory_func=dummy_save_memory)

agent = AgenticEdit(
    llm=llm,
    conversation_history=[],
    files=SourceCodeList(sources=[]),
    args=args,
    memory_config=memory_config,
)

print("\n--- Testing WriteToFileTool ---")
write_tool = WriteToFileTool(path="test_write.txt", content="Some content\nLine 2\nLine 3\n")
write_resolver = WriteToFileToolResolver(agent, write_tool, args)
write_result = write_resolver.resolve()
print(write_result)

print("\n--- Testing ReadFileTool ---")
read_tool = ReadFileTool(path="dummy.txt")
read_resolver = ReadFileToolResolver(agent, read_tool, args)
read_result = read_resolver.resolve()
print(read_result)

print("\n--- Testing ReplaceInFileTool ---")
replace_diff = '''<<<<<<< SEARCH
Hello World
This is a dummy file.
Hello Replaced
This is a dummy file.