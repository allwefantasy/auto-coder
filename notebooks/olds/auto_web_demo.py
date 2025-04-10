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

# 启用调试模式，每步操作需要确认
python auto_web_demo.py --task "填写表单并提交" --debug

参数:
----
--task: 要执行的自动化任务描述
--screenshot: 可选的当前屏幕截图路径
--context: 可选的上下文信息
--output_dir: 输出目录，用于保存截图和结果
--model_name: 使用的LLM模型名称，默认为doubao
--max_iterations: 最大迭代次数，默认为10
--product_mode: 产品模式 [pro|lite]，默认为lite
--debug: 启用详细输出模式
"""

import os
import sys
import argparse
import json
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

import byzerllm
from autocoder.commands.auto_web import auto_web
from autocoder.common import AutoCoderArgs
from autocoder.common.computer_use import ComputerUse
from autocoder.utils.llms import get_single_llm

def parse_args():
    parser = argparse.ArgumentParser(description="执行网页自动化操作")
    parser.add_argument("--task", required=True, help="要执行的自动化任务描述")
    parser.add_argument("--screenshot", help="可选的截图路径，如果未提供，将自动截图")
    parser.add_argument("--context", help="可选的上下文信息")
    parser.add_argument("--output-dir", default="./output", help="输出目录")
    parser.add_argument("--model", default="doubao_vl", help="要使用的LLM模型名称")
    parser.add_argument("--product-mode", default="lite", choices=["pro", "lite"], help="产品模式 (pro|lite)")
    parser.add_argument("--debug", action="store_true", help="启用调试模式，每步操作需要确认")
    
    return parser.parse_args()

def main():
    # 解析命令行参数
    args = parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 准备控制台显示
    console = Console()
    console.print(f"🤖 [bold green]Auto Web Demo[/bold green]", style="bold")
    console.print(f"任务: [bold cyan]{args.task}[/bold cyan]", style="dim")
    
    # 初始化byzerllm
    console.print("初始化LLM...", style="italic")
    llm = get_single_llm(args.model,product_mode="lite")
    # 创建配置
    auto_coder_args = AutoCoderArgs(
        output=args.output_dir
    )
    
    # 执行自动化任务
    start_time = time.time()
    console.print("开始执行自动化任务...", style="bold blue")
    
    # 添加调试模式参数
    response = auto_web(
        llm=llm,
        user_input=args.task,
        screenshot_path=args.screenshot,
        context=args.context,
        args=auto_coder_args,
        debug=args.debug
    )
    
    execution_time = time.time() - start_time
    console.print(f"任务执行完成，总耗时: {execution_time:.2f}秒", style="green")
    
    # 展示结果
    if response.overall_status:
        status_color = {
            "completed": "green",
            "failed": "red",
            "in_progress": "yellow",
            "max_iterations_reached": "yellow",
            "cancelled": "red"
        }.get(response.overall_status, "white")
        
        console.print(f"\n状态: [bold {status_color}]{response.overall_status}[/bold {status_color}]")
    
    if response.explanation:
        console.print("\n说明:")
        console.print(response.explanation)
    
    if response.additional_info:
        console.print("\n附加信息:")
        console.print(response.additional_info)
    
    if response.suggested_next_steps:
        console.print("\n建议的下一步:")
        for step in response.suggested_next_steps:
            console.print(f"- {step}")
    
    # 展示执行的操作
    if response.actions:
        console.print("\n剩余未执行的操作:", style="bold")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("序号")
        table.add_column("操作")
        table.add_column("描述")
        
        for i, action in enumerate(response.actions):
            table.add_row(
                str(i+1),
                action.action,
                action.description or ""
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