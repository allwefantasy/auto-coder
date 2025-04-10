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
Hello Replaced
This is a dummy file.
=======
Hello Replaced
This is a dummy file.
>>>>>>> REPLACE
'''
replace_tool = ReplaceInFileTool(path="dummy.txt", diff=replace_diff)
replace_resolver = ReplaceInFileToolResolver(agent, replace_tool, args)
replace_result = replace_resolver.resolve()

print(replace_result)

print("\n--- Testing ExecuteCommandTool ---")
exec_tool = ExecuteCommandTool(command="echo Hello Tool", requires_approval=False)
exec_resolver = ExecuteCommandToolResolver(agent, exec_tool, args)
exec_result = exec_resolver.resolve()
print(exec_result)

print("\n--- Testing SearchFilesTool ---")
search_tool = SearchFilesTool(path=".", regex="dummy", file_pattern="*.txt")
search_resolver = SearchFilesToolResolver(agent, search_tool, args)
search_result = search_resolver.resolve()
print(search_result)

print("\n--- Testing ListFilesTool ---")
list_tool = ListFilesTool(path=".", recursive=True)
list_resolver = ListFilesToolResolver(agent, list_tool, args)
list_result = list_resolver.resolve()
print(list_result)

print("\n--- Testing ListCodeDefinitionNamesTool ---")
list_defs_tool = ListCodeDefinitionNamesTool(path=dummy_file_path)
list_defs_resolver = ListCodeDefinitionNamesToolResolver(agent, list_defs_tool, args)
list_defs_result = list_defs_resolver.resolve()
print(list_defs_result)

print("\n--- Testing AskFollowupQuestionTool ---")
ask_tool = AskFollowupQuestionTool(question="Is this okay?", options=["Yes", "No"])
ask_resolver = AskFollowupQuestionToolResolver(agent, ask_tool, args)
ask_result = ask_resolver.resolve()
print(ask_result)

print("\n--- Testing AttemptCompletionTool ---")
attempt_tool = AttemptCompletionTool(result="All tasks complete.", command="echo Done")
attempt_resolver = AttemptCompletionToolResolver(agent, attempt_tool, args)
attempt_result = attempt_resolver.resolve()
print(attempt_result)

print("\n--- Testing PlanModeRespondTool ---")
plan_tool = PlanModeRespondTool(response="Here is the plan.", options=["Proceed", "Revise"])
plan_resolver = PlanModeRespondToolResolver(agent, plan_tool, args)
plan_result = plan_resolver.resolve()
print(plan_result)

print("\n--- Testing UseMcpTool ---")
use_mcp_tool = UseMcpTool(server_name="dummy_server", tool_name="dummy_tool", arguments={"param1": "value1"})
use_mcp_resolver = UseMcpToolResolver(agent, use_mcp_tool, args)
use_mcp_result = use_mcp_resolver.resolve()
print(use_mcp_result)