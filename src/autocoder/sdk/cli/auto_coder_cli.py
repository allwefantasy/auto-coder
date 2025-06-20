#!/usr/bin/env python3
"""
Auto-Coder SDK CLI 主接口

提供命令行接口来使用 Auto-Coder SDK 功能
"""

import sys
import argparse
import asyncio
import json
from typing import Optional, Dict, Any
from pathlib import Path

from autocoder.sdk import query_sync, modify_code, query, modify_code_stream, AutoCodeOptions, StreamEvent
from autocoder.sdk.models.responses import CLIResult

def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description="Auto-Coder SDK CLI - 智能代码修改助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s -p "添加错误处理到主函数"
  %(prog)s -p "实现用户认证功能" --cwd /path/to/project
  %(prog)s -p "重构数据库层" --output-format json
  %(prog)s -p "添加日志到所有API端点" --output-format stream-json
        """
    )
    
    # 基本参数
    parser.add_argument(
        "-p", "--prompt", 
        required=True,
        help="代码修改提示或查询内容"
    )
    
    parser.add_argument(
        "--cwd", 
        type=str,
        help="项目工作目录路径"
    )
    
    parser.add_argument(
        "--model", 
        type=str,
        help="使用的AI模型"
    )
    
    parser.add_argument(
        "--max-turns", 
        type=int, 
        default=10,
        help="最大对话轮数 (默认: 10)"
    )
    
    parser.add_argument(
        "--temperature", 
        type=float, 
        default=0.7,
        help="模型温度参数 (默认: 0.7)"
    )
    
    # 代码修改专用参数
    parser.add_argument(
        "--pre-commit", 
        action="store_true",
        help="执行预提交检查"
    )
    
    parser.add_argument(
        "--extra-args", 
        type=str,
        help="额外参数 (JSON格式)"
    )
    
    # 输出控制参数
    parser.add_argument(
        "--output-format", 
        choices=["text", "json", "stream-json"],
        default="text",
        help="输出格式 (默认: text)"
    )
    
    parser.add_argument(
        "--no-terminal-render", 
        action="store_true",
        help="禁用终端友好渲染，使用纯文本输出"
    )
    
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="详细输出模式"
    )
    
    parser.add_argument(
        "--version", 
        action="version",
        version="Auto-Coder SDK 1.0.0"
    )
    
    return parser

def create_options_from_args(args) -> AutoCodeOptions:
    """从命令行参数创建配置选项"""
    options = AutoCodeOptions()
    
    if args.cwd:
        options.cwd = Path(args.cwd)
    if args.model:
        options.model = args.model
    if args.max_turns:
        options.max_turns = args.max_turns
    if args.temperature:
        options.temperature = args.temperature
    if args.verbose:
        options.verbose = args.verbose
    
    return options

def format_output(content: str, format_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """格式化输出内容"""
    if format_type == "json":
        result = {
            "content": content,
            "metadata": metadata or {}
        }
        return json.dumps(result, ensure_ascii=False, indent=2)
    elif format_type == "stream-json":
        # 对于流式 JSON，我们需要分块输出
        lines = content.split('\n')
        output = []
        for i, line in enumerate(lines):
            if i == 0:
                output.append(json.dumps({
                    "event_type": "start",
                    "data": {"status": "started"},
                    "timestamp": None
                }))
            
            if line.strip():
                output.append(json.dumps({
                    "event_type": "content",
                    "data": {"content": line},
                    "timestamp": None
                }))
        
        output.append(json.dumps({
            "event_type": "end",
            "data": {"status": "completed"},
            "timestamp": None
        }))
        
        return '\n'.join(output)
    else:
        return content

def read_from_stdin() -> str:
    """从标准输入读取内容"""
    if not sys.stdin.isatty():
        return sys.stdin.read().strip()
    return ""


def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # 解析额外参数
        extra_args = {}
        if args.extra_args:
            try:
                extra_args = json.loads(args.extra_args)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --extra-args: {e}", file=sys.stderr)
                sys.exit(1)
        
        # 创建配置选项
        options = AutoCodeOptions(
            cwd=Path(args.cwd) if args.cwd else None,
            model=args.model,
            max_turns=args.max_turns,
            temperature=args.temperature
        )
        
        # 控制终端渲染
        show_terminal = not args.no_terminal_render and args.output_format == "text"
                
        # 使用代码修改功能
        if args.output_format == "stream-json":
            # 流式 JSON 输出
            async def stream_modify():
                async for event in modify_code_stream(
                    args.prompt,
                    pre_commit=args.pre_commit,
                    extra_args=extra_args,
                    options=options,
                    show_terminal=show_terminal
                ):
                    print(event.to_json(), flush=True)
            
            asyncio.run(stream_modify())
        else:
            # 同步代码修改
            result = modify_code(
                args.prompt,
                pre_commit=args.pre_commit,
                extra_args=extra_args,
                options=options,
                show_terminal=show_terminal
            )
            
            if args.output_format == "json":
                print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
            else:
                if not show_terminal:  # 只有在没有终端渲染时才输出结果
                    if result.success:
                        print("Code modification completed successfully!")
                        if result.modified_files:
                            print(f"Modified files: {', '.join(result.modified_files)}")
                        if result.created_files:
                            print(f"Created files: {', '.join(result.created_files)}")
                        if result.deleted_files:
                            print(f"Deleted files: {', '.join(result.deleted_files)}")
                        if result.message:
                            print(f"Message: {result.message}")
                    else:
                        print(f"Code modification failed: {result.error_details}")        
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main()) 