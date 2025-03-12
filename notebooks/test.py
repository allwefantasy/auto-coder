from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm

llm = get_single_llm("v3_chat",product_mode="lite")
args = AutoCoderArgs(model="v3_chat")
tools = AutoCommandTools(args, llm)

test_path = "/Users/allwefantasy/projects/auto-coder/src/autocoder/common/mcp_server.py"
v = tools.read_files(paths=test_path, line_ranges="1-200")
print(v)
v = tools.read_files(paths=test_path,line_ranges="201-400")
print("-"*100)
print(v)