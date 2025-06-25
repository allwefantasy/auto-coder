#!/bin/bash

set -e

echo "🚀 Async Agent Runner PR 演示脚本"
echo "================================="
echo ""

# 检查必要的工具
echo "🔍 检查必要工具..."

# 检查 ac 命令是否存在
if ! command -v ac &> /dev/null; then
    echo "❌ 错误: 'ac' 命令未找到"
    echo "请确保已安装 async_agent_runner 并且 ac 在 PATH 中"
    echo ""
    echo "安装步骤:"
    echo "1. cd async_agent_runner"
    echo "2. make build"
    echo "3. make install-user"
    echo "4. 确保 ~/bin 在 PATH 中"
    exit 1
fi

# 检查 auto-coder.run 是否存在
if ! command -v auto-coder.run &> /dev/null; then
    echo "❌ 错误: 'auto-coder.run' 命令未找到"
    echo "请确保已安装 auto-coder"
    exit 1
fi

echo "✅ 所有必要工具都已安装"
echo ""

# 进入目标目录
TARGET_DIR="/Users/williamzhu/projects/pr_demo"
echo "📂 进入目录: $TARGET_DIR"

if [ ! -d "$TARGET_DIR" ]; then
    echo "❌ 错误: 目录 $TARGET_DIR 不存在"
    exit 1
fi

cd "$TARGET_DIR"
echo "✅ 当前工作目录: $(pwd)"
echo ""

# 检查是否在 git 仓库中
if [ ! -d ".git" ]; then
    echo "❌ 错误: 当前目录不是 git 仓库"
    exit 1
fi

echo "✅ 当前在 git 仓库中"
echo ""

# 创建 task.md 文件
echo "📝 创建 task.md 文件..."
cat > task.md << 'EOF'
# 任务：创建一个简单的 JavaScript 计算器

请创建一个基本的 JavaScript 计算器应用，包含以下功能：

## 基本要求

- 创建 calculator.html 文件作为主页面
- 创建 calculator.js 文件实现计算逻辑
- 创建 calculator.css 文件添加样式

## 功能需求

### 基本运算
- 加法 (+)
- 减法 (-)
- 乘法 (*)
- 除法 (/)

### 界面要求
- 数字按钮 (0-9)
- 运算符按钮 (+, -, *, /)
- 等号按钮 (=)
- 清除按钮 (C)
- 显示屏显示当前数字和结果

### 功能特性
- 支持连续运算
- 支持小数点输入
- 错误处理（如除零）
- 响应式设计

## 技术要求

- 使用原生 JavaScript，不依赖外部库
- 使用 CSS Grid 或 Flexbox 布局
- 确保代码结构清晰，有适当注释
- 添加基本的错误处理

## 验收标准

- 所有基本运算功能正常工作
- 界面美观且用户友好
- 代码质量良好，结构清晰
- 在现代浏览器中正常运行
EOF

echo "✅ task.md 文件创建成功"
echo ""

echo "📄 task.md 内容预览:"
echo "---"
head -20 task.md
echo "... (文件已创建，包含完整的计算器开发任务)"
echo "---"
echo ""

# 显示即将执行的命令
echo "🚀 准备执行 async agent runner..."
echo "命令: cat task.md | ac --model cus/anthropic/claude-sonnet-4 --pr"
echo ""

# 询问用户是否继续
echo "⚠️  注意: 这将会:"
echo "   1. 创建新的 git worktree"
echo "   2. 调用 auto-coder.run 生成代码"
echo "   3. 如果成功，可能会创建 Pull Request"
echo ""

read -p "是否继续执行? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 用户取消操作"
    echo "💡 提示: task.md 文件已创建，你可以稍后手动运行:"
    echo "   cat task.md | ac --model cus/anthropic/claude-sonnet-4 --pr"
    exit 0
fi

echo ""
echo "🔥 开始执行..."
echo "================================="

# 执行命令并捕获输出
echo "执行命令: cat task.md | ac --model cus/anthropic/claude-sonnet-4 --pr"
echo ""

# 使用 tee 同时显示输出并保存到文件
OUTPUT_FILE="ac_execution_output.log"
cat task.md | ac --model cus/anthropic/claude-sonnet-4 --pr 2>&1 | tee "$OUTPUT_FILE"

echo ""
echo "================================="
echo "🔍 分析执行结果..."
echo ""

# 检查输出中是否包含 PR 链接
if grep -q "pull.*request\|PR\|merge.*request\|github.com.*pull\|gitlab.*merge" "$OUTPUT_FILE"; then
    echo "✅ 发现 PR 相关信息!"
    echo ""
    echo "🔗 PR 相关输出:"
    grep -i "pull.*request\|PR\|merge.*request\|github.com.*pull\|gitlab.*merge" "$OUTPUT_FILE" || true
    echo ""
else
    echo "⚠️  未在输出中发现明确的 PR 链接"
    echo ""
fi

# 检查是否有 worktree 创建
echo "📋 检查创建的 worktree:"
if command -v ac &> /dev/null; then
    ac list --only-managed 2>/dev/null || echo "无法获取 worktree 列表"
else
    echo "ac 命令不可用"
fi
echo ""

# 显示完整输出文件位置
echo "📄 完整执行日志保存在: $OUTPUT_FILE"
echo ""

# 清理询问
read -p "是否清理创建的 worktree? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🧹 清理 worktree..."
    if command -v ac &> /dev/null; then
        ac cleanup 2>/dev/null && echo "✅ 清理完成" || echo "⚠️  清理过程中出现问题"
    else
        echo "❌ ac 命令不可用，无法自动清理"
    fi
else
    echo "💡 worktree 保留，可以手动检查生成的代码"
    echo "   使用 'ac list' 查看 worktree"
    echo "   使用 'ac cleanup' 清理 worktree"
fi

echo ""
echo "🎉 演示完成!"
echo ""
echo "📊 总结:"
echo "- task.md 文件已创建"
echo "- async agent runner 已执行"
echo "- 执行日志保存在 $OUTPUT_FILE"
echo "- 请检查上述输出确认是否包含 PR 链接"
