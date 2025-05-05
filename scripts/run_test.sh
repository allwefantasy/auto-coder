#!/bin/bash

# 确保脚本可以在任何目录下执行
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 设置环境变量
export autocoder_auto_init=${autocoder_auto_init:-false}
export auto_coder_log_stdout=${auto_coder_log_stdout:-true}

echo "环境变量设置:"
echo "  - autocoder_auto_init=${autocoder_auto_init}"
echo "  - auto_coder_log_stdout=${auto_coder_log_stdout}"

# 检查是否提供了参数
if [ $# -eq 0 ]; then
    echo "用法: $0 [测试路径] [pytest参数]"
    echo "例如: $0 src/autocoder/rag/ -v"
    echo "未提供参数，将运行所有测试"
    python -m pytest -s --log-cli-level=INFO tests/
else
    # 运行pytest命令并传递所有参数
    echo "正在运行测试: $@"
    python -m pytest -s --log-cli-level=INFO "$@"
fi 