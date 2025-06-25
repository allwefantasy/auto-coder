
#!/bin/bash

# 快速演示脚本 - 直接运行示例
set -e

echo "🚀 Async Agent Runner 快速演示"
echo "============================="
echo ""

# 检查是否在正确的目录
if [ ! -f "scripts/pr_demo.sh" ]; then
    echo "❌ 请在 async_agent_runner 目录中运行此脚本"
    exit 1
fi

echo "📋 这个脚本将演示 async_agent_runner 的核心功能："
echo "   1. 进入 /Users/williamzhu/projects/pr_demo"
echo "   2. 创建一个 task.md 文件"
echo "   3. 运行 ac --model cus/anthropic/claude-sonnet-4 --pr"
echo "   4. 检查输出中是否包含 PR 链接"
echo ""

read -p "是否继续? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ 用户取消操作"
    exit 0
fi

echo ""
echo "🔥 启动详细演示脚本..."
echo ""

# 运行主演示脚本
./scripts/pr_demo.sh

