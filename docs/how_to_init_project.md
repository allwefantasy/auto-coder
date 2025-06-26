
为了调用 auto-coder 库里的任何模块，比如测试或者写一个可执行脚本，
你需要按顺序准备做如下几件事

## 设置项目目录

你可以创建一个临时目录，然后将该临时目录设置为项目目录。

import os
os.chdir("/path/to/your/project")

##  设置运行模式为终端模式
from autocoder.run_context import get_run_context, RunMode
get_run_context().set_mode(RunMode.TERMINAL)

## 导入启动必要的模块 
import subprocess
from autocoder.auto_coder_runner import (
    load_tokenizer,
    initialize_system,
    InitializeSystemRequest,
    start as start_engine,
    stop as stop_engine,
    auto_command,
    configure,
    add_files,
    save_memory,
    get_memory,
    init_project_if_required
)

def setup_environment():
    """设置环境和初始化系统"""
    print("🚀 开始初始化 Auto-Coder 环境...")
    
    # 1. 加载 tokenizer
    print("📚 加载 tokenizer...")
    load_tokenizer()
    
    # 2. 启动引擎
    print("⚙️  启动引擎...")
    start_engine()
    
    # 3. 基本配置
    print("🔧 配置基本参数...")
    configure("product_mode:lite", skip_print=True)
    configure("skip_build_index:true", skip_print=True)
    configure("skip_confirm:true", skip_print=True)
    configure("silence:false", skip_print=True)  # 显示详细输出
    configure("auto_merge:editblock", skip_print=True)
    
    print("✅ 环境初始化完成！")


## 获取模型 get_llm

from autocoder.utils.llms import get_single_llm
llm = get_single_llm("模型名字", product_mode="lite")


