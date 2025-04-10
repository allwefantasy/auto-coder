#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
演示如何使用活动上下文跟踪子系统
"""

import os
import time
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any
import yaml
import git

import byzerllm
from autocoder.utils.llms import get_single_llm
from autocoder.common import AutoCoderArgs
from autocoder.memory import ActiveContextManager
from autocoder.common.action_yml_file_manager import ActionYmlFileManager

# 创建临时项目目录
def create_test_project():
    """创建测试项目目录和文件"""    
    project_dir = "test_project"
    
    # 清理已存在的目录（如果有）
    if os.path.exists(project_dir):
        try:
            shutil.rmtree(project_dir)
            print(f"已清理现有项目目录: {project_dir}")
        except Exception as e:
            print(f"清理目录失败: {e}")
    
    # 创建项目结构
    src_dir = os.path.join(project_dir, "src")
    pkg1_dir = os.path.join(src_dir, "package1")
    pkg2_dir = os.path.join(src_dir, "package1", "package2")
    pkg3_dir = os.path.join(src_dir, "package3")
    
    # 创建目录
    os.makedirs(pkg1_dir, exist_ok=True)
    os.makedirs(pkg2_dir, exist_ok=True)
    os.makedirs(pkg3_dir, exist_ok=True)
    
    # 创建测试文件
    with open(os.path.join(pkg1_dir, "a.py"), "w") as f:
        f.write("""
def function_a():
    '''Function A'''
    print("This is function A")
    return "A"
""")
    
    with open(os.path.join(pkg2_dir, "b.py"), "w") as f:
        f.write("""
def function_b():
    '''Function B'''
    print("This is function B")
    return "B"
""")
    
    with open(os.path.join(pkg3_dir, "c.py"), "w") as f:
        f.write("""
def function_c():
    '''Function C'''
    print("This is function C")
    return "C"
""")
    
    with open(os.path.join(pkg3_dir, "d.py"), "w") as f:
        f.write("""
def function_d():
    '''Function D'''
    print("This is function D")
    return "D"
""")
    
    # 创建.auto-coder和actions目录
    os.makedirs(os.path.join(project_dir, ".auto-coder"), exist_ok=True)
    os.makedirs(os.path.join(project_dir, "actions"), exist_ok=True)
    
    # 创建YAML文件
    create_test_yaml(project_dir)
    
    # 初始化git仓库，以便测试文件变更跟踪
    repo = None
    try:
        print("\n初始化Git仓库...")
        repo = git.Repo.init(project_dir)
        
        # 配置Git用户信息(避免使用全局配置)
        repo.git.config('user.name', 'Test User')
        repo.git.config('user.email', 'test@example.com')
        
        # 添加所有文件并提交
        repo.git.add('--all')
        commit = repo.git.commit('-m', 'Initial commit')
        print(f"Git仓库初始化成功，初始提交: {commit[:8]}")
        
        # 验证Git状态
        status = repo.git.status(porcelain=True)
        if status:
            print(f"警告：Git仓库状态不干净，有未提交的变更: {status}")
        else:
            print("Git仓库状态干净，所有变更已提交")
            
        # 打印提交历史
        commits = list(repo.iter_commits())
        print(f"当前Git提交历史: {len(commits)} 个提交")
        for c in commits:
            print(f"  {c.hexsha[:8]} - {c.message.strip()}")
            
    except Exception as e:
        print(f"Git初始化或提交失败: {e}")
    
    return project_dir, repo

def create_test_yaml(project_dir, suffix="", query="添加日志功能到所有函数", commit_id=None):
    """创建测试YAML文件"""
    # 构建文件路径
    file_paths = [
        os.path.join(project_dir, "src", "package1", "a.py"),
        os.path.join(project_dir, "src", "package1", "package2", "b.py"),
        os.path.join(project_dir, "src", "package3", "c.py"),
        os.path.join(project_dir, "src", "package3", "d.py")
    ]
    
    # 创建YAML内容
    yaml_content = {
        "query": query,
        "urls": file_paths[0:2],  # a.py和b.py作为当前文件
        "dynamic_urls": [],
        "add_updated_urls": file_paths  # 所有文件都作为更新文件
    }
    
    # 添加commit_id如果提供
    if commit_id:
        yaml_content["commit_id"] = commit_id
    
    # 写入YAML文件
    yaml_file_path = os.path.join(project_dir, "actions", f"000000000001_test_action{suffix}.yml")
    with open(yaml_file_path, "w") as f:
        yaml.dump(yaml_content, f, default_flow_style=False)
    
    return yaml_file_path

def test_active_context_basic():
    """基本功能测试：演示如何使用ActiveContextManager处理代码变更"""
    print("\n=== 测试1: 基本功能测试 ===")
    
    # 创建测试项目
    project_dir, _ = create_test_project()
    print(f"创建测试项目目录: {project_dir}")
    
    try:
        # 配置参数
        args = AutoCoderArgs(
            source_dir=project_dir,
            file=os.path.join(project_dir, "actions", "000000000001_test_action.yml")
        )
        
        # 获取LLM实例
        llm = get_single_llm("v3_chat", product_mode="lite")
        
        # 创建ActiveContextManager实例
        active_context_manager = ActiveContextManager(llm, args)
        
        # 处理变更 - 异步执行
        task_id = active_context_manager.process_changes()
        print(f"启动任务: {task_id}")
        
        # 检查任务状态
        for _ in range(5):  # 最多等待5次
            status = active_context_manager.get_task_status(task_id)
            print(f"任务状态: {status['status']}")
            
            if status['status'] in ['completed', 'failed']:
                break
                
            time.sleep(1)  # 等待1秒
        
        # 显示任务详情
        final_status = active_context_manager.get_task_status(task_id)
        print("\n任务详情:")
        for key, value in final_status.items():
            print(f"  {key}: {value}")
        
        # 检查生成的文件
        active_context_dir = os.path.join(project_dir, ".auto-coder", "active-context")
        if os.path.exists(active_context_dir):
            print("\n生成的活动上下文目录:")
            for root, dirs, files in os.walk(active_context_dir):
                for file in files:
                    print(f"  {os.path.join(os.path.relpath(root, project_dir), file)}")
                    
                    # 显示文件内容摘要
                    file_path = os.path.join(root, file)
                    with open(file_path, "r") as f:
                        content = f.read()
                        print(f"    内容摘要: {content[:150]}...\n")
    
    finally:               
        print(f"测试项目目录: {project_dir}")

def test_active_context_file_update():
    """文件更新测试：演示如何更新现有的active.md文件"""
    print("\n=== 测试4: 文件更新测试 ===")
    
    # 创建测试项目
    project_dir, _ = create_test_project()
    print(f"创建测试项目目录: {project_dir}")
    
    try:
        # 1. 首先运行一次生成初始文件
        args = AutoCoderArgs(
            source_dir=project_dir,
            file=os.path.join(project_dir, "actions", "000000000001_test_action.yml")
        )
        
        llm = get_single_llm("v3_chat", product_mode="lite")
        active_context_manager = ActiveContextManager(llm, args)
        
        print("第1步: 生成初始活动文件...")
        task_id = active_context_manager.process_changes()
        
        # 等待任务完成
        for _ in range(5):
            status = active_context_manager.get_task_status(task_id)
            if status['status'] in ['completed', 'failed']:
                break
            time.sleep(1)
        
        # 2. 检查现有文件
        active_context_dir = os.path.join(project_dir, ".auto-coder", "active-context")
        print("\n第1步完成，显示已生成的活动文件:")
        existing_files = []
        for root, dirs, files in os.walk(active_context_dir):
            for file in files:
                file_path = os.path.join(root, file)
                existing_files.append(file_path)
                print(f"  {os.path.relpath(file_path, project_dir)}")
        
        # 3. 创建新的YAML文件，表示新的变更
        print("\n第2步: 创建新的YAML文件，代表新的变更...")
        new_yaml = create_test_yaml(
            project_dir, 
            suffix="_update",
            query="优化函数性能并添加更多注释"
        )
        
        # 4. 使用新的YAML运行一次，更新现有文件
        args.file = new_yaml
        active_context_manager = ActiveContextManager(llm, args)
        
        print("第3步: 更新现有活动文件...")
        update_task_id = active_context_manager.process_changes()
        
        # 等待任务完成
        for _ in range(5):
            status = active_context_manager.get_task_status(update_task_id)
            print(f"更新任务状态: {status['status']}")
            if status['status'] in ['completed', 'failed']:
                break
            time.sleep(1)
        
        # 5. 显示更新后的内容
        print("\n更新后的活动文件内容:")
        for file_path in existing_files:
            with open(file_path, "r") as f:
                content = f.read()
                print(f"\n文件: {os.path.relpath(file_path, project_dir)}")
                print(f"内容摘要: {content[:150]}...")
                print("...")
    
    finally:               
        print(f"测试项目目录: {project_dir}")

def test_active_context_with_changes():
    """文件变更测试：演示如何利用文件变更历史生成更详细的活动文件"""
    print("\n=== 测试5: 文件变更测试 ===")
    
    # 创建测试项目
    project_dir, repo = create_test_project()
    print(f"创建测试项目目录: {project_dir}")
    
    try:
        # 确认Git仓库已初始化
        if not repo:
            print("警告: Git仓库未初始化，将尝试重新打开仓库")
            try:
                repo = git.Repo(project_dir)
            except Exception as e:
                print(f"Error reopening git repository: {e}")
                print("将继续测试，但可能无法检测文件变更")
                repo = None

        # 记录原始文件内容，以便展示差异
        a_py_path = os.path.join(project_dir, "src", "package1", "a.py")
        b_py_path = os.path.join(project_dir, "src", "package1", "package2", "b.py")
        
        original_a_content = ""
        original_b_content = ""
        
        try:
            with open(a_py_path, "r") as f:
                original_a_content = f.read()
            with open(b_py_path, "r") as f:
                original_b_content = f.read()
            print("\n已记录原始文件内容")
        except Exception as e:
            print(f"读取原始文件内容失败: {e}")
        
        # 1. 修改测试文件，创建变更历史
        print("\n步骤1: 修改文件...")
        with open(a_py_path, "w") as f:
            f.write("""
def function_a():
    '''Function A - Modified'''
    # 添加日志
    print("[LOG] Function A started")
    print("This is function A")
    print("[LOG] Function A completed")
    return "A"
""")

        with open(b_py_path, "w") as f:
            f.write("""
def function_b():
    '''Function B - Modified'''
    # 添加日志
    print("[LOG] Function B started")
    print("This is function B")
    print("[LOG] Function B completed")
    return "B"
""")
        
        # 显示文件变更
        try:
            with open(a_py_path, "r") as f:
                new_a_content = f.read()
            with open(b_py_path, "r") as f:
                new_b_content = f.read()
                
            print("\n文件 a.py 变更:")
            print(f"变更前: {original_a_content.strip()}")
            print(f"变更后: {new_a_content.strip()}")
            
            print("\n文件 b.py 变更:")
            print(f"变更前: {original_b_content.strip()}")
            print(f"变更后: {new_b_content.strip()}")
        except Exception as e:
            print(f"显示文件变更失败: {e}")

        # 2. 提交变更到git
        latest_commit = None
        if repo:
            try:
                print("\n步骤2: 提交变更到Git...")
                
                # 显示当前Git状态
                status = repo.git.status(porcelain=True)
                if status:
                    print(f"Git状态 (变更前提交): \n{status}")
                else:
                    print("警告: 没有检测到文件变更")
                
                # 添加并提交变更
                repo.git.add('--all')
                commit = repo.git.commit('-m', 'Added logging to functions')
                print(f"变更已提交: {commit[:8]}")
                
                # 获取最新的commit ID
                latest_commit = repo.head.commit.hexsha
                print(f"最新的commit ID: {latest_commit[:8]}...")
                
                # 显示提交差异
                try:
                    if len(list(repo.iter_commits())) >= 2:
                        diffs = repo.git.diff('HEAD~1..HEAD', '--stat')
                        print(f"\nGit差异统计: \n{diffs}")
                except Exception as e:
                    print(f"获取差异统计失败: {e}")
            except Exception as e:
                print(f"Git提交失败: {e}")
                latest_commit = "dummy_commit_id"
        else:
            print("跳过Git提交，因为Git仓库不可用")
            latest_commit = "dummy_commit_id"
        
        # 3. 创建新的YAML文件，包含commit ID
        print("\n步骤3: 创建包含commit ID的YAML文件...")
        yaml_path = create_test_yaml(
            project_dir, 
            suffix="_with_changes",
            query="检查所有日志功能的实现",
            commit_id=latest_commit
        )
        print(f"已创建YAML文件: {yaml_path}")
        
        # 4. 使用新的YAML运行生成任务
        args = AutoCoderArgs(
            source_dir=project_dir,
            file=yaml_path
        )
        
        llm = get_single_llm("v3_chat", product_mode="lite")
        active_context_manager = ActiveContextManager(llm, args)
        
        print("\n步骤4: 处理包含文件变更信息的任务...")
        task_id = active_context_manager.process_changes()
        print(f"已启动任务: {task_id}")
        
        # 等待任务完成
        for i in range(10):  # 增加等待时间到10秒
            status = active_context_manager.get_task_status(task_id)
            print(f"任务状态 ({i+1}/10): {status['status']}")
            if status['status'] in ['completed', 'failed']:
                break
            time.sleep(1)
        
        # 5. 显示生成的文件内容
        active_context_dir = os.path.join(project_dir, ".auto-coder", "active-context")
        print("\n步骤5: 生成的活动文件内容:")
        
        if not os.path.exists(active_context_dir):
            print(f"警告: 活动上下文目录不存在: {active_context_dir}")
        else:
            found_files = False
            for root, dirs, files in os.walk(active_context_dir):
                for file in files:
                    found_files = True
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r") as f:
                            content = f.read()
                            print(f"\n文件: {os.path.relpath(file_path, project_dir)}")
                            print(f"内容摘要 (前200字符): {content[:200]}...")
                            
                            # 检查内容是否包含变更信息
                            if "变更前" in content and "变更后" in content:
                                print("✅ 文件包含变更对比信息")
                            elif "文件变更摘要" in content:
                                print("✅ 文件包含变更摘要信息")
                            else:
                                print("❌ 警告: 文件不包含明显的变更信息")
                    except Exception as e:
                        print(f"读取文件失败: {e}")
            
            if not found_files:
                print("没有找到生成的活动文件")
    
    finally:               
        print(f"测试项目目录: {project_dir}")

def test_active_context_multiple_tasks():
    """多任务测试：演示如何处理多个并发任务"""
    print("\n=== 测试2: 多任务测试 ===")
    
    # 创建测试项目
    project_dir, _ = create_test_project()
    print(f"创建测试项目目录: {project_dir}")
    
    try:
        # 配置参数
        args = AutoCoderArgs(
            source_dir=project_dir,
            file=os.path.join(project_dir, "actions", "000000000001_test_action.yml")
        )
        
        # 获取LLM实例
        llm = get_single_llm("v3_chat", product_mode="lite")
        
        # 创建ActiveContextManager实例
        active_context_manager = ActiveContextManager(llm, args)
        
        # 处理多个变更 - 异步执行
        task_ids = []
        for i in range(3):  # 启动3个任务
            task_id = active_context_manager.process_changes()
            task_ids.append(task_id)
            print(f"启动任务 {i+1}: {task_id}")
        
        # 等待一段时间
        print("\n等待3秒...")
        time.sleep(3)
        
        # 获取所有任务状态
        all_tasks = active_context_manager.get_all_tasks()
        print(f"\n所有任务 ({len(all_tasks)}):")
        for task in all_tasks:
            print(f"  {task['task_id']}: {task['status']}")
        
        # 获取运行中的任务
        running_tasks = active_context_manager.get_running_tasks()
        print(f"\n运行中的任务 ({len(running_tasks)}):")
        for task in running_tasks:
            print(f"  {task['task_id']}: {task['status']}")
            
        # 等待任务完成
        print("\n等待所有任务完成...")
        for _ in range(10):  # 最多等待10秒
            all_done = True
            for task_id in task_ids:
                status = active_context_manager.get_task_status(task_id)
                if status['status'] not in ['completed', 'failed']:
                    all_done = False
            
            if all_done:
                break
                
            time.sleep(1)
            
        # 最终状态
        print("\n最终任务状态:")
        for task_id in task_ids:
            status = active_context_manager.get_task_status(task_id)
            print(f"  {task_id}: {status['status']}")
    
    finally:                
        print(f"测试项目目录: {project_dir}")

def test_active_context_error_handling():
    """错误处理测试：演示如何处理各种错误情况"""
    print("\n=== 测试3: 错误处理测试 ===")
    
    # 创建测试项目
    project_dir, _ = create_test_project()
    print(f"创建测试项目目录: {project_dir}")
    
    try:
        # 配置参数
        args = AutoCoderArgs(
            source_dir=project_dir,
            file=os.path.join(project_dir, "actions", "000000000001_test_action.yml")
        )
        
        # 获取LLM实例
        llm = get_single_llm("v3_chat", product_mode="lite")
        
        # 创建ActiveContextManager实例
        active_context_manager = ActiveContextManager(llm, args)
        
        # 测试不存在的YAML文件
        print("\n测试不存在的YAML文件:")
        try:
            active_context_manager.process_changes("non_existent.yml")
        except Exception as e:
            print(f"  捕获到异常: {e}")
        
        # 测试没有权限的目录
        print("\n测试没有权限的目录:")
        restricted_dir = os.path.join(project_dir, "restricted")
        os.makedirs(restricted_dir, exist_ok=True)
        
        try:
            # 移除目录权限
            os.chmod(restricted_dir, 0o000)
            
            # 修改目标目录为没有权限的目录
            # 注意：这只是一个模拟的错误场景
            old_source_dir = active_context_manager.args.source_dir
            active_context_manager.args.source_dir = restricted_dir
            
            try:
                active_context_manager.process_changes()
            except Exception as e:
                print(f"  捕获到异常: {e}")
            
            # 恢复原来的设置
            active_context_manager.args.source_dir = old_source_dir
        finally:
            # 恢复目录权限，以便于清理
            os.chmod(restricted_dir, 0o755)
    
    finally:                    
        print(f"测试项目目录: {project_dir}")

def test_load_active_contexts():
    """加载活动上下文测试：演示如何加载指定文件的活动上下文信息"""
    print("\n=== 测试6: 加载活动上下文测试 ===")
    
    # 创建测试项目
    project_dir, repo = create_test_project()
    print(f"创建测试项目目录: {project_dir}")
    
    try:
        # 1. 先生成活动上下文文件
        args = AutoCoderArgs(
            source_dir=project_dir,
            file=os.path.join(project_dir, "actions", "000000000001_test_action.yml")
        )
        
        llm = get_single_llm("v3_chat", product_mode="lite")
        active_context_manager = ActiveContextManager(llm, args)
        
        print("步骤1: 生成活动上下文文件...")
        task_id = active_context_manager.process_changes()
        
        # 等待任务完成
        for _ in range(5):
            status = active_context_manager.get_task_status(task_id)
            print(f"任务状态: {status['status']}")
            if status['status'] in ['completed', 'failed']:
                break
            time.sleep(1)
        
        # 2. 准备要查询的文件路径
        file_paths = [
            os.path.join(project_dir, "src", "package1", "a.py"),
            os.path.join(project_dir, "src", "package1", "package2", "b.py"),
            os.path.join(project_dir, "src", "package3", "c.py"),
            # 添加一个不存在的文件
            os.path.join(project_dir, "src", "non_existent", "file.py")
        ]
        
        print("\n步骤2: 查询以下文件的活动上下文:")
        for file_path in file_paths:
            print(f"  - {os.path.relpath(file_path, project_dir)}")
        
        # 3. 调用load_active_contexts_for_files方法
        print("\n步骤3: 加载活动上下文...")
        result = active_context_manager.load_active_contexts_for_files(file_paths)
        
        # 4. 显示结果
        print(f"\n找到 {len(result.contexts)} 个相关的活动上下文目录:")
        for dir_path, context in result.contexts.items():
            rel_path = os.path.relpath(dir_path, project_dir)
            print(f"\n目录: {rel_path}")
            print(f"活动文件路径: {os.path.relpath(context.active_md_path, project_dir)}")
            print(f"关联的文件: {[os.path.relpath(f, project_dir) for f in context.files]}")
            
            # 显示部分内容
            print("\n内容摘要:")
            
            if context.sections.header:
                print(f"标题: {context.sections.header[:50]}...")
            
            if context.sections.current_change:
                print(f"当前变更: {context.sections.current_change[:50]}...")
            
            if context.sections.document:
                print(f"文档: {context.sections.document[:50]}...")
        
        # 5. 显示未找到活动上下文的文件
        if result.not_found_files:
            print(f"\n未找到活动上下文的文件 ({len(result.not_found_files)}):")
            for file_path in result.not_found_files:
                print(f"  - {os.path.relpath(file_path, project_dir)}")
        
        # 6. 测试模型序列化和反序列化
        print("\n步骤4: 测试模型序列化和反序列化...")
        try:
            # 序列化为JSON
            json_str = result.model_dump_json(indent=2)
            print(f"模型序列化成功，JSON大小: {len(json_str)} 字节")
            
            # 输出一小部分JSON示例
            preview_length = min(150, len(json_str))
            print(f"JSON预览: {json_str[:preview_length]}...")
            
            # 测试反序列化
            from autocoder.memory.active_context_manager import FileContextsResult
            try:
                import json
                parsed_data = json.loads(json_str)
                reconstructed = FileContextsResult.model_validate(parsed_data)
                print(f"模型反序列化成功，包含 {len(reconstructed.contexts)} 个上下文和 {len(reconstructed.not_found_files)} 个未找到的文件")
            except Exception as e:
                print(f"模型反序列化失败: {e}")
                
        except Exception as e:
            print(f"模型序列化测试失败: {e}")
        
    finally:
        print(f"测试项目目录: {project_dir}")

def main():
    """主函数，运行所有测试"""
    print("=== 活动上下文跟踪子系统演示 ===")
    
    # 运行测试
    # test_active_context_basic()
    # test_active_context_file_update() 
    # test_active_context_with_changes()  # 文件变更测试
    # test_active_context_multiple_tasks()
    # test_active_context_error_handling()
    test_load_active_contexts()  # 新增: 加载活动上下文测试
    
    print("\n所有测试完成!")

if __name__ == "__main__":
    main() 