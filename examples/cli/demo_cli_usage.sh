#!/bin/bash

# Auto-Coder CLI 使用演示脚本
# 该脚本展示如何使用 auto-coder.run 命令行工具进行代码编写

set -e  # 遇到错误时退出

# 脚本配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="simple_project"
PROJECT_DIR="${SCRIPT_DIR}/${PROJECT_NAME}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    # 检查 auto-coder.run 命令是否可用
    if ! command -v auto-coder.run &> /dev/null; then
        print_error "auto-coder.run 命令未找到。请确保已正确安装 auto-coder。"
        print_info "安装方法: pip install -e ."
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 清理旧项目
cleanup_old_project() {
    if [ -d "$PROJECT_DIR" ]; then
        print_warning "发现已存在的项目目录: $PROJECT_DIR"
        read -p "是否删除并重新创建? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "删除旧项目目录..."
            rm -rf "$PROJECT_DIR"
            print_success "旧项目目录已删除"
        else
            print_error "用户取消操作"
            exit 1
        fi
    fi
}

# 创建项目目录
create_project() {
    print_info "创建项目目录: $PROJECT_DIR"
    mkdir -p "$PROJECT_DIR"
    cd "$PROJECT_DIR"
    print_success "项目目录创建完成"
}

# 演示基本的代码生成功能
demo_basic_code_generation() {
    print_info "=== 演示1: 基本代码生成 ==="
    print_info "使用 auto-coder.run 生成一个简单的 Python 计算器模块"
    
    local prompt="创建一个简单的 Python 计算器模块，包含加减乘除四个基本运算函数，每个函数都要有文档字符串和类型提示。文件名为 calculator.py"
    
    print_info "执行命令: auto-coder.run -p \"$prompt\" --model gpt-4"
    
    # 使用 auto-coder.run 生成代码，指定模型
    auto-coder.run -p "$prompt" --output-format text --permission-mode acceptEdits --verbose --model gpt-4
    
    # 检查生成的文件
    if [ -f "calculator.py" ]; then
        print_success "calculator.py 文件生成成功"
        print_info "生成的文件内容预览:"
        echo "----------------------------------------"
        head -20 calculator.py
        echo "----------------------------------------"
    else
        print_warning "calculator.py 文件未生成，可能需要手动确认操作"
    fi
}

# 演示代码优化功能
demo_code_optimization() {
    print_info "=== 演示2: 代码优化 ==="
    print_info "为计算器模块添加错误处理和单元测试"
    
    local prompt="为现有的 calculator.py 模块添加完善的错误处理（如除零检查），并创建一个对应的单元测试文件 test_calculator.py，使用 pytest 框架"
    
    print_info "执行命令: auto-coder.run -p \"$prompt\""
    
    # 继续优化代码
    auto-coder.run -p "$prompt" --output-format text --permission-mode acceptEdits --verbose --max-turns 5
    
    # 检查生成的测试文件
    if [ -f "test_calculator.py" ]; then
        print_success "test_calculator.py 文件生成成功"
        print_info "测试文件内容预览:"
        echo "----------------------------------------"
        head -15 test_calculator.py
        echo "----------------------------------------"
    else
        print_warning "test_calculator.py 文件未生成"
    fi
}

# 演示JSON输出格式
demo_json_output() {
    print_info "=== 演示3: JSON 输出格式 ==="
    print_info "使用 JSON 格式输出，便于程序化处理"
    
    local prompt="为项目创建一个 README.md 文件，说明如何使用这个计算器模块"
    
    print_info "执行命令: auto-coder.run -p \"$prompt\" --output-format json"
    
    # 使用JSON格式输出
    auto-coder.run -p "$prompt" --output-format json --permission-mode acceptEdits > output.json
    
    if [ -f "output.json" ]; then
        print_success "JSON 输出保存到 output.json"
        print_info "JSON 输出内容预览:"
        echo "----------------------------------------"
        head -10 output.json
        echo "----------------------------------------"
    fi
    
    # 检查README文件
    if [ -f "README.md" ]; then
        print_success "README.md 文件生成成功"
    fi
}

# 演示工具限制功能
demo_tool_restrictions() {
    print_info "=== 演示4: 工具限制 ==="
    print_info "限制只能使用读取和搜索工具，进行代码分析"
    
    local prompt="分析当前项目中的所有 Python 文件，总结代码结构和功能"
    
    print_info "执行命令: auto-coder.run -p \"$prompt\" --allowed-tools read_file search_files"
    
    # 限制工具使用
    auto-coder.run -p "$prompt" --allowed-tools read_file search_files --output-format text --verbose
}

# 显示项目结构
show_project_structure() {
    print_info "=== 最终项目结构 ==="
    print_info "生成的项目文件:"
    
    if command -v tree &> /dev/null; then
        tree .
    else
        find . -type f -name "*.py" -o -name "*.md" -o -name "*.json" | sort
    fi
    
    print_info "项目文件统计:"
    echo "Python 文件: $(find . -name "*.py" | wc -l)"
    echo "Markdown 文件: $(find . -name "*.md" | wc -l)"
    echo "JSON 文件: $(find . -name "*.json" | wc -l)"
}

# 运行测试（如果可能）
run_tests() {
    print_info "=== 运行测试 ==="
    
    if [ -f "test_calculator.py" ] && command -v pytest &> /dev/null; then
        print_info "运行单元测试..."
        pytest test_calculator.py -v || print_warning "测试运行失败，可能需要安装依赖"
    elif [ -f "test_calculator.py" ] && command -v python &> /dev/null; then
        print_info "使用 Python 运行测试..."
        python -m unittest test_calculator.py || print_warning "测试运行失败"
    else
        print_warning "无法运行测试：缺少测试文件或测试框架"
    fi
}

# 清理函数
cleanup() {
    print_info "演示完成"
    print_info "项目位置: $PROJECT_DIR"
    print_info "您可以查看生成的文件并进一步测试功能"
}

# 主函数
main() {
    print_info "Auto-Coder CLI 使用演示开始"
    print_info "项目名称: $PROJECT_NAME"
    print_info "项目路径: $PROJECT_DIR"
    echo
    
    # 执行演示步骤
    check_dependencies
    cleanup_old_project
    create_project
    
    echo
    demo_basic_code_generation
    echo
    
    demo_code_optimization
    echo
    
    demo_json_output
    echo
    
    demo_tool_restrictions
    echo
    
    show_project_structure
    echo
    
    run_tests
    echo
    
    cleanup
}

# 错误处理
trap 'print_error "脚本执行过程中发生错误"; exit 1' ERR

# 运行主函数
main "$@"
