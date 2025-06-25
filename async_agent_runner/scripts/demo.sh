#!/bin/bash

set -e

echo "🚀 Auto-Coder 异步代理运行器演示"
echo "=================================="

# 确保二进制文件存在
if [ ! -f "bin/ac" ]; then
    echo "构建二进制文件..."
    go build -o bin/ac .
fi

echo ""
echo "📋 演示使用的 markdown 文件内容："
echo "---"
cat examples/structured_test.md
echo "---"
echo ""

echo "🔍 测试不同的分割模式："
echo ""

# 模拟模式（不实际执行 auto-coder.run）
MODEL="demo/test-model"

echo "1️⃣  按 H1 标题分割 (默认模式)："
echo "命令: cat examples/structured_test.md | ./bin/ac --model $MODEL --split h1"
echo ""

# 测试 H1 分割但不实际执行（因为没有真实的 auto-coder.run）
echo "期望结果: 应该分割成 4 个任务 (每个 # 标题一个)"
echo ""

echo "2️⃣  按 H2 标题分割："
echo "命令: cat examples/structured_test.md | ./bin/ac --model $MODEL --split h2"
echo ""
echo "期望结果: 应该分割成更多任务 (每个 ## 标题也会分割)"
echo ""

echo "3️⃣  按自定义分隔符分割 (兼容模式)："
echo "命令: cat examples/test.md | ./bin/ac --model $MODEL --split delimiter --delimiter '==='"
echo ""
echo "期望结果: 应该按 === 分割成 3 个任务"
echo ""

echo "4️⃣  按指定级别范围分割："
echo "命令: cat examples/structured_test.md | ./bin/ac --model $MODEL --split any --min-level 2 --max-level 3"
echo ""
echo "期望结果: 只在 H2 和 H3 级别分割"
echo ""

echo "💡 实际使用示例："
echo "# 处理你的 markdown 文件"
echo "cat your_tasks.md | ./bin/ac --model cus/anthropic/claude-sonnet-4 --split h1 --pr"
echo ""
echo "# 查看所有创建的 worktree"
echo "./bin/ac list"
echo ""
echo "# 清理所有 worktree"
echo "./bin/ac cleanup"
echo ""

echo "📚 支持的分割模式："
echo "- h1: 按一级标题 (# 标题) 分割 [默认]"
echo "- h2: 按一、二级标题 (# ## 标题) 分割"
echo "- h3: 按一、二、三级标题 (# ## ### 标题) 分割"
echo "- any: 按指定级别范围的标题分割"
echo "- delimiter: 按自定义分隔符分割 (兼容模式)"
echo ""

echo "✅ 演示完成！"