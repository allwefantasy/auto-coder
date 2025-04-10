import os
import sys
import shutil
from pathlib import Path
from typing import List, Dict, Any

from autocoder.common import AutoCoderArgs, SourceCode, SourceCodeList
from autocoder.utils.llms import get_single_llm
from autocoder.common.v2.code_editblock_manager import CodeEditBlockManager
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.rag.token_counter import count_tokens
from autocoder.helper.project_creator import ProjectCreator


def file_to_source_code(file_path: str) -> SourceCode:
    """将文件转换为 SourceCode 对象"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return SourceCode(module_name=file_path, source_code=content, tokens=count_tokens(content))


def get_source_code_list(project_dir: str) -> SourceCodeList:
    """获取项目中所有 JavaScript/React 文件的 SourceCode 列表"""
    source_codes = []
    js_extensions = ('.js', '.jsx', '.ts', '.tsx')
    
    for root, _, files in os.walk(project_dir):
        for file in files:
            if file.endswith(js_extensions):
                file_path = os.path.join(root, file)
                source_codes.append(file_to_source_code(file_path))
    
    return SourceCodeList(sources=source_codes)


def main():
    load_tokenizer()
    # 创建示例 React 项目
    creator = ProjectCreator(
        project_name="test_project",
        project_type="react",  # 指定为 React 项目
        query="为计算器添加乘法和除法功能，并美化用户界面",
        git_init=True
    )
    project_dir = creator.create_project()
    print(f"创建了示例 React 项目: {project_dir}")
    
    # 获取项目中的源代码
    source_code_list = get_source_code_list(project_dir)
    print(f"获取到 {len(source_code_list.sources)} 个源代码文件")
    
    # 切换工作目录到项目目录
    os.chdir(project_dir)
    
    # 获取 LLM 实例
    llm = get_single_llm("v3_chat", product_mode="lite")
    print("初始化 LLM 完成")
    
    # 创建 AutoCoderArgs 实例
    args = AutoCoderArgs(
        source_dir=project_dir,        
        auto_fix_lint_max_attempts=3,
        enable_auto_fix_lint=True,
        generate_times_same_model=1,  
        target_file= os.path.join(project_dir, "output.txt"),
        file=os.path.join(project_dir, "actions", "000000000001_chat_action.yml")            
    )
    
    # 初始化 CodeEditBlockManager
    edit_manager = CodeEditBlockManager(llm=llm, args=args)
    print("初始化 CodeEditBlockManager 完成")
    
    # 使用相同的查询字符串运行代码生成和修复
    query = creator.query
    print(f"\n开始执行代码生成与修复...\n查询: {query}")
    edit_manager.run(query, source_code_list)
       
    
    print("\n如需运行 React 项目，请执行以下命令:")
    print(f"cd {project_dir}")
    print("npm install")
    print("npm start")
    
    print("\n示例完成")


if __name__ == "__main__":
    main() 