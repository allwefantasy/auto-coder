#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ShadowManager的create_link_project方法使用示例
此示例演示了如何使用ShadowManager创建链接项目，
该项目会优先使用影子文件，如果影子文件不存在则使用源文件
"""

import os
import sys
import shutil
from pathlib import Path
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.compilers.shadow_compiler import ShadowCompiler
# 添加项目根目录到Python路径以便导入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

def main():
    # 使用test_project作为示例项目
    test_project_dir = os.path.join(current_dir, "test_project")
    if not os.path.exists(test_project_dir):
        print(f"错误: 找不到示例项目目录 {test_project_dir}")
        return
    
    print(f"使用示例项目: {test_project_dir}")
    
    # 初始化ShadowManager
    shadow_manager = ShadowManager(os.path.abspath(test_project_dir))
    print(f"初始化ShadowManager，影子目录: {shadow_manager.shadows_dir}")
            
    # 创建链接项目
    print("\n创建链接项目...")
    link_project_dir = shadow_manager.create_link_project()
    print(f"链接项目已创建: {link_project_dir}")
    shadow_manager.compare_directories()

    shadow_compiler = ShadowCompiler(shadow_manager)
    result = shadow_compiler.compile_all_shadow_files("reactjs")
    print(result)
    print(result.to_str())
    
    print("\n示例完成")


if __name__ == "__main__":
    main() 