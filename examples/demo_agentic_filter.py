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
from autocoder.agent.agentic_filter import AgenticFilterRequest, AgenticFilter, CommandConfig, MemoryConfig
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

# 准备请求参数
request = AgenticFilterRequest(
    user_input="我想优化索引构建的代码"
)

# 初始化调优器
llm = get_single_llm(
    args.index_filter_model or args.model, product_mode=args.product_mode)
    
tuner = AgenticFilter(llm,
                      args=args,
                      conversation_history=[],
                      memory_config=MemoryConfig(
                          memory=get_memory(), save_memory_func=save_memory),
                      command_config=CommandConfig(
                          add_files=add_files,
                          remove_files=remove_files,
                          list_files=list_files,
                          conf=configure,
                          revert=revert,
                          commit=commit,
                          help=help,
                          exclude_dirs=exclude_dirs,
                          exclude_files=exclude_files,
                          ask=ask,
                          chat=chat,
                          coding=coding,
                          design=design,
                          summon=summon,
                          lib=lib_command,
                          mcp=mcp,
                          models=manage_models,
                          index_build=index_build,
                          index_query=index_query,
                          execute_shell_command=execute_shell_command,
                          generate_shell_command=generate_shell_command,
                          conf_export=conf_export,
                          conf_import=conf_import,
                          index_export=index_export,
                          index_import=index_import
                      ))

# 生成建议
response = tuner.analyze(request)
print(response)
