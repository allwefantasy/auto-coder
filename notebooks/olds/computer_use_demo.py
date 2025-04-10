#!/usr/bin/env python
"""
ComputerUse 演示脚本
====================

这个脚本演示如何使用 ComputerUse 工具与电脑界面交互。

用法:
----
# 基本用法
python computer_use_demo.py --action screenshot

# 查找并点击元素
python computer_use_demo.py --action find_and_click --element "搜索按钮"

# 运行工作流
python computer_use_demo.py --action workflow --workflow workflow.json

参数:
----
--action: 要执行的操作，可选值: screenshot, detect, find_and_click, workflow
--element: 要查找的元素描述，用于 find_and_click 动作
--output_dir: 输出目录，默认为 ./output
--model_name: 视觉语言模型名称，默认为 doubao_vl
--product_mode: 产品模式 [pro|lite]，默认为 lite
--workflow: 工作流 JSON 文件路径，用于 workflow 动作
"""

import os
import sys
import json
import argparse
import time
from autocoder.utils.llms import get_single_llm
from autocoder.common import AutoCoderArgs
from computer_use import ComputerUse

def main():
    parser = argparse.ArgumentParser(description='演示 ComputerUse 工具的使用')
    parser.add_argument('--action', type=str, required=True,
                        choices=['screenshot', 'detect', 'find_and_click', 'workflow'],
                        help='要执行的操作')
    parser.add_argument('--element', type=str, default=None,
                        help='要查找的元素描述，用于 find_and_click 动作')
    parser.add_argument('--output_dir', type=str, default='./output',
                        help='输出目录')
    parser.add_argument('--model_name', type=str, default='doubao_vl',
                        help='视觉语言模型名称')
    parser.add_argument('--product_mode', type=str, default='lite',
                        choices=['pro', 'lite'], help='产品模式')
    parser.add_argument('--workflow', type=str, default=None,
                        help='工作流 JSON 文件路径，用于 workflow 动作')
    
    args = parser.parse_args()
    
    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)
    
    print(f"初始化 LLM，模型: {args.model_name}")
    # 获取 LLM 实例
    llm = get_single_llm(args.model_name, args.product_mode)
    
    # 准备 AutoCoderArgs
    autocoder_args = AutoCoderArgs(
        output=args.output_dir
    )
    
    print("创建 ComputerUse 实例")
    # 创建 ComputerUse 实例
    computer = ComputerUse(
        llm=llm,
        args=autocoder_args
    )
    
    # 根据不同操作执行相应的逻辑
    if args.action == 'screenshot':
        print("截取屏幕")
        screenshot_path = computer.screenshot()
        print(f"截图已保存到: {screenshot_path}")
        
    elif args.action == 'detect':
        print("检测屏幕上的元素")
        # 先截图
        screenshot_path = computer.screenshot()
        print(f"截图已保存到: {screenshot_path}")
        
        # 检测元素
        print("分析截图中的元素...")
        detection_result = computer.detect_objects.with_llm(computer.vl_model).run(screenshot_path)
        
        # 解析结果
        result_json = code_utils.extract_code(detection_result)[-1][1]
        result = json.loads(result_json)
        
        # 显示检测结果
        print(f"检测到 {len(result['objects'])} 个元素:")
        for i, obj in enumerate(result['objects']):
            bbox = obj['bounding_box']
            print(f"元素 {i+1}: 类型={obj.get('type', 'unknown')}, 描述={obj.get('text', 'N/A')}")
            print(f"    边界框: [{bbox[0]}, {bbox[1]}, {bbox[2]}, {bbox[3]}]")
            
    elif args.action == 'find_and_click':
        if not args.element:
            print("错误: 使用 find_and_click 动作时必须提供 --element 参数")
            sys.exit(1)
            
        print(f"查找并点击元素: '{args.element}'")
        # 先截图
        screenshot_path = computer.screenshot()
        
        # 尝试点击元素
        success = computer.click_element(screenshot_path, args.element)
        
        if success:
            print(f"成功点击了元素: '{args.element}'")
        else:
            print(f"未能找到或点击元素: '{args.element}'")
            
    elif args.action == 'workflow':
        if not args.workflow:
            print("错误: 使用 workflow 动作时必须提供 --workflow 参数")
            sys.exit(1)
            
        print(f"执行工作流: {args.workflow}")
        
        # 读取工作流文件
        try:
            with open(args.workflow, 'r', encoding='utf-8') as f:
                workflow = json.load(f)
                
            # 确保是列表
            if not isinstance(workflow, list):
                print("错误: 工作流必须是一个步骤列表")
                sys.exit(1)
                
            # 执行工作流
            print(f"开始执行工作流，共 {len(workflow)} 个步骤")
            results = computer.run_workflow(workflow)
            
            # 保存结果
            results_path = os.path.join(args.output_dir, 'workflow_results.json')
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
                
            print(f"工作流执行完毕，结果已保存到: {results_path}")
            
            # 显示摘要
            success_count = sum(1 for r in results if r.get('success', False))
            print(f"步骤总数: {len(workflow)}, 成功: {success_count}, 失败: {len(workflow) - success_count}")
            
        except Exception as e:
            print(f"执行工作流时出错: {str(e)}")

if __name__ == "__main__":
    main() 