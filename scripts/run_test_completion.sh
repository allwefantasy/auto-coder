#!/bin/bash

# 为 run_test.sh 脚本提供 Bash 路径自动补全功能
_run_test_completion() {
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # 获取项目根目录
    local script_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    local project_root="$(dirname "$script_dir")"
    
    # 确保当前在项目根目录下进行补全
    cd "$project_root"
    
    # 如果是第一个参数（测试路径）
    if [[ ${COMP_CWORD} -eq 1 ]]; then
        # 如果当前输入为空或只是部分路径名
        if [[ -z "${cur}" || ! "${cur}" =~ "/" ]]; then
            # 查找所有包含test_开头文件的目录
            local dirs=()
            local temp_dirs=()
            
            # 首先添加常用测试目录
            dirs+=("tests/")
            
            # 使用find命令递归查找所有包含test_*.py文件的目录
            # 兼容MacOS和Linux的find命令
            while IFS= read -r dir; do
                # 排除常见的不需要的目录
                if [[ ! "$dir" =~ (\.git|\.venv|venv|__pycache__|\.pytest_cache|node_modules) ]]; then
                    # 获取目录的相对路径
                    local rel_dir="${dir#./}"
                    if [[ ! " ${dirs[@]} " =~ " ${rel_dir} " ]]; then
                        dirs+=("${rel_dir}")
                    fi
                fi
            done < <(find . -type f -name "test_*.py" -not -path "*/\.*" | xargs -n1 dirname | sort | uniq)
            
            # 如果有部分匹配的输入，过滤目录列表
            if [[ -n "${cur}" ]]; then
                for dir in "${dirs[@]}"; do
                    # 如果目录名包含当前输入
                    if [[ "${dir}" =~ .*${cur}.* ]]; then
                        # 如果是精确匹配目录的一部分
                        local parts=(${dir//\// })
                        for part in "${parts[@]}"; do
                            if [[ "${part}" == *"${cur}"* ]]; then
                                temp_dirs+=("${dir}")
                                break
                            fi
                        done
                    fi
                done
                COMPREPLY=( "${temp_dirs[@]}" )
            else
                COMPREPLY=( "${dirs[@]}" )
            fi
        else
            # 如果已经开始输入路径，提供该路径下的子目录和文件补全
            # 获取目录前缀
            local dir_prefix="${cur%/*}/"
            local file_prefix="${cur##*/}"
            
            # 首先查找子目录
            while IFS= read -r subdir; do
                COMPREPLY+=("${dir_prefix}${subdir}/")
            done < <(find "${dir_prefix}" -maxdepth 1 -type d -name "${file_prefix}*" -not -path "*/\.*" | xargs -n1 basename 2>/dev/null)
            
            # 然后查找测试文件
            while IFS= read -r file; do
                COMPREPLY+=("${dir_prefix}${file}")
            done < <(find "${dir_prefix}" -maxdepth 1 -type f -name "test_${file_prefix}*.py" | xargs -n1 basename 2>/dev/null)
        fi
        return 0
    elif [[ ${COMP_CWORD} -gt 1 ]]; then
        # 如果是第二个或更多参数，提供常用的pytest选项
        local pytest_options=("-v" "--verbose" "-xvs" "-s" "--log-cli-level=INFO" "--log-cli-level=DEBUG")
        COMPREPLY=( $(compgen -W "${pytest_options[*]}" -- "${cur}") )
        return 0
    fi
}

# 注册补全函数
complete -F _run_test_completion scripts/run_test.sh
complete -F _run_test_completion ./scripts/run_test.sh

# 只有在交互式执行脚本时才输出消息
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "已加载 run_test.sh 补全功能"
    echo "使用方法: 在 .bashrc 或 .zshrc 中添加以下行："
    echo "source $(pwd)/scripts/run_test_completion.sh"
fi 