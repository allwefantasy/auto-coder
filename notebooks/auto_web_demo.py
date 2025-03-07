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
--model_name: 使用的LLM模型名称，默认为dubao
--product_mode: 产品模式 [pro|lite]，默认为lite
"""

import os
import sys
import argparse
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
    parser.add_argument('--model_name', type=str, default='doubao',
                        help='使用的LLM模型名称')
    parser.add_argument('--product_mode', type=str, default='lite',
                        choices=['pro', 'lite'], help='产品模式')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    # 准备AutoCoderArgs
    autocoder_args = AutoCoderArgs(
        output=args.output_dir,
        product_mode=args.product_mode
    )
    
    # 如果没有提供截图但需要进行屏幕操作，先截个图
    screenshot_path = args.screenshot
    if not screenshot_path:
        print("未提供截图，正在截取当前屏幕...")
        try:
            # 获取LLM
            llm = get_single_llm(args.model_name, args.product_mode)
            
            # 使用ComputerUse截图
            computer = ComputerUse(llm=llm, args=autocoder_args)
            screenshot_path = computer.screenshot()
            print(f"已截取当前屏幕: {screenshot_path}")
        except Exception as e:
            print(f"截图失败: {str(e)}")
            print("继续执行，但可能无法进行某些屏幕操作")
    
    print(f"开始执行自动化任务: {args.task}")
    
    # 调用auto_web函数
    response = auto_web(
        user_input=args.task, 
        screenshot_path=screenshot_path,
        context=args.context,
        args=autocoder_args
    )
    
    # 输出结果摘要
    if response.explanation:
        print("\n任务执行总结:")
        print(response.explanation)
    
    if response.suggested_next_steps:
        print("\n建议的后续步骤:")
        for i, step in enumerate(response.suggested_next_steps, 1):
            print(f"{i}. {step}")
    
    print("\n自动化任务执行完成!")

if __name__ == "__main__":
    main() 