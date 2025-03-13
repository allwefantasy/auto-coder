#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AutoLearnFromCommit演示脚本
===========================

这个脚本演示了如何使用AutoLearnFromCommit类从提交历史中学习代码变更模式。
参考了test_context_prune_v2.py的结构设计方式。

主要功能:
1. 设置LLM和必要的环境参数
2. 初始化AutoLearnFromCommit类
3. 展示最新的代码提交信息
4. 从提交历史中学习并总结代码变更模式
5. 展示学习结果
"""

from typing import List, Dict, Generator, Optional, Tuple, Any
import os
import sys
import traceback
import git
import yaml
import byzerllm
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm
from autocoder.agent.auto_learn_from_commit import AutoLearnFromCommit, load_yaml_config

# 设置控制台对象，用于美观输出
console = Console()

def setup_demo_environment() -> Dict:
    """设置演示环境，返回配置信息"""
    # 获取当前工作目录
    current_dir = os.path.abspath(os.path.dirname(os.getcwd()))
    
    # 创建配置
    config = {
        "source_dir": current_dir,
        "llm_model": "v3_chat",
        "product_mode": "lite",
        "actions_dir": os.path.join(current_dir, "actions")
    }    
    
    return config

def get_latest_commit_info(config: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """获取最新提交的信息"""
    actions_dir = config["actions_dir"]
    if not os.path.exists(actions_dir):
        console.print("[bold red]actions目录不存在，无法获取提交信息[/bold red]")
        return None, None
    
    # 获取所有YAML文件
    action_files = [
        f for f in os.listdir(actions_dir)
        if (f[:3].isdigit() and "_" in f and f.endswith('.yml')) or f.endswith('.yml')
    ]
    
    if not action_files:
        console.print("[bold red]actions目录中没有找到YAML文件[/bold red]")
        return None, None
    
    # 按序号排序
    def get_seq(name):
        try:
            if name[:3].isdigit() and "_" in name:
                return int(name.split("_")[0])
            return 0
        except:
            return 0
    
    # 获取最新的action文件
    action_files = sorted(action_files, key=get_seq, reverse=True)
    latest_action_file = action_files[0]
    
    # 加载YAML配置
    yaml_path = os.path.join(actions_dir, latest_action_file)
    config = load_yaml_config(yaml_path)
    
    return latest_action_file, config

def display_commit_info(action_file: str, config: Dict):
    """显示提交信息"""
    table = Table(title=f"最新提交 [{action_file}]")
    
    # 创建表格列
    table.add_column("属性", style="cyan")
    table.add_column("值", style="green")
    
    # 添加关键信息
    for key in ["query", "model", "product_mode"]:
        if key in config:
            value = str(config[key])
            # 截断过长的值
            if len(value) > 70:
                value = value[:67] + "..."
            table.add_row(key, value)
    
    # 添加URL信息
    if "urls" in config and config["urls"]:
        url_value = "\n".join(config["urls"][:5])
        if len(config["urls"]) > 5:
            url_value += f"\n... (total: {len(config['urls'])})"
        table.add_row("urls", url_value)
    else:
        table.add_row("urls", "[]")
    
    console.print(table)

def demo_auto_learn_from_commit():
    """演示如何使用AutoLearnFromCommit从提交历史中学习"""
    try:
        # 设置演示环境
        console.print(Panel("[bold]设置演示环境[/bold]", style="green"))
        config = setup_demo_environment()
        console.print(f"源代码目录: {config['source_dir']}")
        console.print(f"LLM模型: {config['llm_model']}")
        console.print(f"产品模式: {config['product_mode']}")
        
        # 获取最新提交信息
        console.print(Panel("[bold]获取最新的提交信息[/bold]", style="green"))
        latest_action_file, action_config = get_latest_commit_info(config)
        
        if latest_action_file and action_config:
            display_commit_info(latest_action_file, action_config)
        else:
            console.print("[yellow]无法获取最新的提交信息，将使用默认查询进行演示[/yellow]")
        
        # 创建LLM实例
        console.print(Panel("[bold]创建LLM实例[/bold]", style="green"))
        try:
            llm = get_single_llm(config["llm_model"], product_mode=config["product_mode"])
            console.print(f"LLM实例已创建: {config['llm_model']}")
        except Exception as e:
            console.print(f"[bold red]创建LLM实例失败: {str(e)}[/bold red]")
            return
        
        # 创建AutoCoderArgs实例
        console.print(Panel("[bold]创建AutoCoderArgs实例[/bold]", style="green"))
        args = AutoCoderArgs(
            source_dir=config["source_dir"],
            model=config["llm_model"],
            product_mode=config["product_mode"]
        )
        console.print(f"AutoCoderArgs实例已创建")
        
        # 创建AutoLearnFromCommit实例
        console.print(Panel("[bold]创建AutoLearnFromCommit实例[/bold]", style="green"))
        auto_learn = AutoLearnFromCommit(
            llm=llm,
            args=args,
            skip_diff=False,
            console=console
        )
        console.print(f"AutoLearnFromCommit实例已创建")
        
        # 设置学习查询
        # 如果有最新提交，使用其查询；否则使用默认查询
        query = action_config.get("query", "分析提交的代码变更，总结其中的通用模式和最佳实践") if action_config else "分析提交的代码变更，总结其中的通用模式和最佳实践"
        
        console.print(Panel(f"[bold]设置学习查询[/bold]", style="green"))
        console.print(f"查询: {query[:100]}..." if len(query) > 100 else f"查询: {query}")
        
        # 模拟对话历史
        conversations = [
            {"role": "user", "content": "请分析最近的代码提交并总结模式"},
            {"role": "assistant", "content": "好的，我将分析最近的代码提交并总结其中的模式。"},
            {"role": "user", "content": query}
        ]
        console.print(Panel("[bold]模拟对话历史[/bold]", style="green"))
        for i, conv in enumerate(conversations):
            prefix = f"[{i+1}] "
            role_style = "blue" if conv["role"] == "user" else "green"
            content = conv["content"]
            if len(content) > 80:
                content = content[:77] + "..."
            console.print(f"{prefix}[{role_style}]{conv['role']}[/{role_style}]: {content}")
        
        # 执行从提交中学习
        console.print(Panel("[bold]从提交中学习[/bold]", style="green"))
        console.print("正在从最近的提交中学习代码变更模式...")
        
        # 调用learn_from_commit方法
        result_generator = auto_learn.learn_from_commit(query, conversations)
        
        if result_generator:
            console.print(Panel("[bold]学习结果[/bold]", style="green"))
            
            # 收集完整结果
            full_result = ""
            for (result_chunk,meta) in result_generator:
                full_result += result_chunk
                console.print(result_chunk, end="")
            
            # 输出完整的Markdown格式结果
            console.print("\n\n[bold]结果摘要[/bold]")
            try:
                # 尝试提取摘要部分
                if "总结" in full_result:
                    summary_parts = full_result.split("总结")
                    if len(summary_parts) > 1:
                        summary = "总结" + summary_parts[1]
                        console.print(Markdown(summary[:500] + "..." if len(summary) > 500 else summary))
            except Exception:
                pass
        else:
            console.print("\n[bold red]未找到可学习的提交[/bold red]")
            console.print("可能的原因:")
            console.print("1. actions目录中没有有效的提交记录")
            console.print("2. 最新的提交没有关联的代码变更")
            console.print("3. git仓库访问出现问题")
            
    except Exception as e:
        console.print(f"\n[bold red]演示过程中发生错误:[/bold red]")
        console.print(str(e))
        console.print(traceback.format_exc())

def main():
    """主函数"""
    console.print(Panel("[bold]AutoLearnFromCommit演示[/bold]", style="yellow"))
    demo_auto_learn_from_commit()
    console.print(Panel("[bold]演示结束[/bold]", style="yellow"))

if __name__ == "__main__":
    main() 