#!/usr/bin/env python
"""
Auto Web Demo Script
===================

这个脚本演示如何使用auto_web模块来执行网页自动化操作。

用法:
----
# 基本用法
python auto_web_demo.py --task "打开浏览器并搜索Python自动化"

# 提供截图路径
python auto_web_demo.py --task "点击页面上的登录按钮" --screenshot "path/to/screenshot.png"

# 提供上下文信息
python auto_web_demo.py --task "填写表单并提交" --context "我正在尝试注册一个新账户"

参数:
----
--task: 要执行的自动化任务描述
--screenshot: 可选的当前屏幕截图路径
--context: 可选的上下文信息
--output_dir: 输出目录，用于保存截图和结果
--model_name: 使用的LLM模型名称，默认为doubao
--max_iterations: 最大迭代次数，默认为10
--product_mode: 产品模式 [pro|lite]，默认为lite
--verbose: 启用详细输出模式
"""

import os
import sys
import argparse
import json
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

from autocoder.commands.auto_web import auto_web
from autocoder.common import AutoCoderArgs
from autocoder.common.computer_use import ComputerUse
from autocoder.utils.llms import get_single_llm

def main():
    parser = argparse.ArgumentParser(description='执行网页自动化操作')
    parser.add_argument('--task', type=str, required=True,
                        help='要执行的自动化任务描述')
    parser.add_argument('--screenshot', type=str, default=None,
                        help='可选的当前屏幕截图路径')
    parser.add_argument('--context', type=str, default=None,
                        help='可选的上下文信息')
    parser.add_argument('--output_dir', type=str, default='./output',
                        help='输出目录，用于保存截图和结果')
    parser.add_argument('--model_name', type=str, default='doubao_vl',
                        help='使用的LLM模型名称')
    parser.add_argument('--max_iterations', type=int, default=10,
                        help='最大迭代次数')
    parser.add_argument('--product_mode', type=str, default='lite',
                        choices=['pro', 'lite'], help='产品模式')
    parser.add_argument('--verbose', action='store_true',
                        help='启用详细输出模式')
    
    args = parser.parse_args()
    console = Console()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 准备AutoCoderArgs
    autocoder_args = AutoCoderArgs(
        output=args.output_dir,
        product_mode=args.product_mode,
        model=args.model_name
    )
    
    # 如果没有提供截图但需要进行屏幕操作，先截个图
    screenshot_path = args.screenshot
    if not screenshot_path:
        console.print("未提供截图，正在截取当前屏幕...", style="yellow")
        try:
            # 获取LLM
            llm = get_single_llm(autocoder_args.model,"lite")
            
            # 使用ComputerUse截图
            computer = ComputerUse(llm=llm, args=autocoder_args)
            screenshot_path = computer.screenshot()
            console.print(f"已截取当前屏幕: {screenshot_path}", style="green")
        except Exception as e:
            console.print(f"截图失败: {str(e)}", style="red")
            console.print("继续执行，但可能无法进行某些屏幕操作", style="yellow")
    
    # 显示任务信息
    console.print(Panel(
        Text(args.task, style="bold"),
        title="📋 自动化任务",
        border_style="blue"
    ))
    
    # 调用auto_web函数
    response = auto_web(
        user_input=args.task, 
        screenshot_path=screenshot_path,
        context=args.context,
        args=autocoder_args
    )
    
    # 输出任务结果
    status_style = {
        "completed": "green",
        "failed": "red",
        "cancelled": "yellow",
        "in_progress": "blue",
        "max_iterations_reached": "yellow"
    }.get(response.overall_status, "white")
    
    # 显示任务执行总结
    if response.explanation:
        console.print(Panel(
            Text(response.explanation, style="italic"),
            title=f"✨ 任务执行总结 ({response.overall_status})",
            border_style=status_style
        ))
    
    # 显示额外信息
    if response.additional_info and args.verbose:
        console.print(Panel(
            Text(response.additional_info),
            title="ℹ️ 额外信息",
            border_style="cyan"
        ))
    
    # 显示建议的后续步骤
    if response.suggested_next_steps:
        suggestions = "\n".join([f"• {step}" for step in response.suggested_next_steps])
        console.print(Panel(
            Text(suggestions),
            title="👉 建议的后续步骤",
            border_style="green"
        ))
    
    # 显示剩余操作（如果有）
    if response.actions:
        table = Table(title="⏭️ 未执行的操作")
        table.add_column("序号", style="dim")
        table.add_column("操作", style="cyan")
        table.add_column("描述", style="green")
        
        for i, action in enumerate(response.actions, 1):
            table.add_row(
                str(i),
                action.action,
                action.description or "无描述"
            )
        
        console.print(table)
    
    # 保存执行结果
    result_path = os.path.join(args.output_dir, "auto_web_result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(response.model_dump(), f, ensure_ascii=False, indent=2)
    
    console.print(f"\n结果已保存至: {result_path}", style="dim")
    console.print("\n🎉 自动化任务执行完成!", style="bold green")

if __name__ == "__main__":
    main() 