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
from autocoder.common import SourceCode, SourceCodeList
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.compilers.shadow_compiler import ShadowCompiler
from autocoder.helper.project_creator import ProjectCreator
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.rag.token_counter import count_tokens


def file_to_source_code(file_path: str) -> SourceCode:
    """将文件转换为 SourceCode 对象"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return SourceCode(module_name=file_path, source_code=content, tokens=count_tokens(content))


def get_source_code_list(project_dir: str) -> SourceCodeList:
    """获取项目中所有 Python 文件的 SourceCode 列表"""
    source_codes = []
    
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith('.tsx'):
                file_path = os.path.join(root, file)
                source_codes.append(file_to_source_code(file_path))
    
    return SourceCodeList(sources=source_codes)

def create_compiler_config(project_dir: str):
    config = '''
compilers:
- args:
  - run
  - build
  command: npm
  name: reactjs
  triggers:
  - '.js'
  - '.jsx'
  - '.ts'
  - '.tsx'
  type: vite
  version: '1.0'
  working_dir: .

'''
    projects_dir = os.path.join(project_dir,".auto-coder","projects")
    os.makedirs(projects_dir, exist_ok=True)
    with open(os.path.join(projects_dir, 'compiler.yml'), 'w', encoding='utf-8') as f:
        f.write(config)


def main():
    load_tokenizer()
    # 创建示例项目
    creator = ProjectCreator(
        project_name="test_project",
        project_type="reactjs",  # 可以切换为 "react" 创建 React 项目
        query="给计算器添加乘法和除法功能，并为所有方法添加类型提示"
    )
    project_dir = creator.create_project()
    print(f"创建了示例项目: {project_dir}")
        
    ## 切换工作目录到 project_dir
    os.chdir(project_dir)
    create_compiler_config(project_dir)

    
    # 初始化ShadowManager
    shadow_manager = ShadowManager(os.path.abspath(project_dir))
    print(f"初始化ShadowManager，影子目录: {shadow_manager.shadows_dir}")
            
    # 创建链接项目
    print("\n创建链接项目...")
    link_project_dir = shadow_manager.create_link_project()
    print(f"链接项目已创建: {link_project_dir}")
    shadow_manager.compare_directories()

    shadow_compiler = ShadowCompiler(shadow_manager)
    result = shadow_compiler.compile_all_shadow_files()
    print(result)
    print(result.to_str())
    
    print("\n示例完成")


if __name__ == "__main__":
    main() 