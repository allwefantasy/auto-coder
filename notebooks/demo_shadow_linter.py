#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
演示使用 ShadowLinter 对影子文件进行代码检查的脚本。
本示例将展示如何检查 Python 脚本和前端（JavaScript/TypeScript）文件。
"""

import os
import sys
import tempfile
import json


from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.linters.shadow_linter import ShadowLinter

def create_demo_files(shadow_manager):
    """
    创建演示用的 Python 和 JavaScript 文件，并保存到影子目录。
    
    参数:
        shadow_manager: ShadowManager 实例
        
    返回:
        元组，包含 (python_project_path, js_project_path)
    """
    # 创建一个有 lint 问题的 Python 文件
    python_content = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

def calculate_something(a,b,   c):
    '''这是一个有问题的函数'''
    x = a+b+c  # 缺少空格
    unused_var = "This variable is never used"
    if x == 42:
        print('Found the answer!')
    else:
        print("Not the answer")
    return x

def unused_function():
    pass

calculate_something(1, 2, 3)
"""

    # 创建一个有 lint 问题的 JavaScript 文件
    js_content = """// 一个有问题的 JavaScript 文件
function calculateSomething(a,b,c) {
    var x = a+b+c;  // 缺少空格
    var unusedVar = "This variable is never used";
    if(x == 42) {
        console.log('Found the answer!');
    } else {
        console.log("Not the answer");
    }
    return x;
}

// 使用 == 而非 === (在 JavaScript 中是一个常见的 lint 问题)
if (1 == '1') {
    console.log("This is true in JavaScript with ==");
}

calculateSomething(1, 2, 3);
"""

    # 为演示文件创建项目路径
    python_project_path = os.path.join(shadow_manager.source_dir, "demo_python_file.py")
    js_project_path = os.path.join(shadow_manager.source_dir, "demo_js_file.js")
    
    # 将文件保存到影子目录
    shadow_manager.save_file(python_project_path, python_content)
    shadow_manager.save_file(js_project_path, js_content)
    
    print(f"创建了演示 Python 文件: {python_project_path}")
    print(f"创建了演示 JavaScript 文件: {js_project_path}")
    
    return python_project_path, js_project_path

def run_demo():
    """
    运行 ShadowLinter 演示。
    """
    # 创建临时目录作为演示项目的根目录
    temp_dir = os.path.join(os.path.dirname(__file__), "test_project")
    if os.path.exists(temp_dir):
        import shutil
        shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
    
    print(f"创建临时项目目录: {temp_dir}")
    
    # 初始化 ShadowManager
    shadow_manager = ShadowManager(temp_dir, event_file_id="demo_event")
    shadow_linter = ShadowLinter(shadow_manager, verbose=True)
    
    # 创建演示文件
    python_path, js_path = create_demo_files(shadow_manager)
    
    print("\n" + "="*80)
    print("1. 对单个 Python 文件进行代码检查")
    print("="*80)
    
    # 获取 Python 文件的影子路径
    python_shadow_path = shadow_manager.to_shadow_path(python_path)
    python_result = shadow_linter.lint_shadow_file(python_shadow_path)
    
    print("\nPython 文件检查结果:")
    print("-"*40)
    print(python_result.to_str())
    
    print("\n" + "="*80)
    print("2. 对单个 JavaScript 文件进行代码检查")
    print("="*80)
    
    # 获取 JavaScript 文件的影子路径
    js_shadow_path = shadow_manager.to_shadow_path(js_path)
    js_result = shadow_linter.lint_shadow_file(js_shadow_path)
    
    print("\nJavaScript 文件检查结果:")
    print("-"*40)
    print(js_result.to_str())
    
    print("\n" + "="*80)
    print("3. 对所有影子文件进行代码检查")
    print("="*80)
    
    # 对所有文件进行代码检查
    all_results = shadow_linter.lint_all_shadow_files()
    
    print("\n所有文件的检查结果:")
    print("-"*40)
    # 只显示有问题的文件
    print(all_results.to_str(include_all_files=False))
    
    print("\n" + "="*80)
    print("4. 使用修复模式对所有文件进行代码检查")
    print("="*80)
    
    # 尝试自动修复问题
    fix_results = shadow_linter.lint_all_shadow_files(fix=True)
    
    print("\n修复后的检查结果:")
    print("-"*40)
    print(fix_results.to_str())
    
    print("\n" + "="*80)
    print("5. 代码检查结果的 JSON 序列化示例")
    print("="*80)
    
    # 将结果转换为字典，然后进行序列化
    result_dict = all_results.dict()
    # 由于 datetime 对象不能直接序列化为 JSON，需要将其转换为字符串
    result_dict['timestamp'] = result_dict['timestamp'].isoformat()
    
    # 缩进格式输出 JSON
    print(json.dumps(result_dict, indent=2, ensure_ascii=False)[:500] + "...(截断)")
    
    print("\n演示完成。")

if __name__ == "__main__":
    run_demo() 