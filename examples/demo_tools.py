from autocoder.auto_coder_runner import (
    get_final_config, load_memory, load_tokenizer, save_memory, get_memory, ask,
    coding,
    chat,
    design,
    summon,
    lib_command,
    mcp, manage_models, index_build, index_query, execute_shell_command, generate_shell_command, conf_export, conf_import, index_export, index_import, add_files,
    remove_files,
    list_files,
    revert,
    commit,
    help,
    exclude_dirs,
    exclude_files,configure)
from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm
load_tokenizer()
load_memory()
args = AutoCoderArgs(
    output="output.txt",
    index_filter_model="v3_chat",
    model="v3_chat",
    product_mode="lite",
    source_dir="/Users/allwefantasy/projects/auto-coder",
    project_type="py",
    enable_task_history=False
)

tools = AutoCommandTools(args=args,llm=get_single_llm(args.model,product_mode=args.product_mode))

print(tools.list_files("/Users/allwefantasy/projects/auto-coder"))


