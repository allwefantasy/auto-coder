"""
CLI 主入口点模块

提供命令行接口的主要实现，处理参数解析和命令执行。
"""

import sys
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any, Union

try:
    import argcomplete
    ARGCOMPLETE_AVAILABLE = True
except ImportError:
    ARGCOMPLETE_AVAILABLE = False

from .options import CLIOptions, CLIResult
from .handlers import PrintModeHandler
from ..exceptions import AutoCoderSDKError


class AutoCoderCLI:
    """命令行接口主类，处理命令行参数和执行相应的操作。"""
    
    def __init__(self):
        """初始化CLI实例。"""
        pass
        
    def run(self, options: CLIOptions, cwd: Optional[str] = None) -> CLIResult:
        """
        运行CLI命令 - 统一使用 Print Mode。
        
        Args:
            options: CLI选项
            cwd: 当前工作目录，如果为None则使用系统当前目录
            
        Returns:
            命令执行结果
        """
        try:
            # 验证选项
            options.validate()
            
            # 移除模式判断，直接使用 PrintModeHandler
            return self.handle_print_mode(options, cwd)
                
        except Exception as e:
            return CLIResult(success=False, error=str(e))
            
    def handle_print_mode(self, options: CLIOptions, cwd: Optional[str] = None) -> CLIResult:
        """
        处理打印模式。
        
        Args:
            options: CLI选项
            cwd: 当前工作目录
            
        Returns:
            命令执行结果
        """
        handler = PrintModeHandler(options, cwd)
        return handler.handle()
        
        
    @classmethod
    def parse_args(cls, args: Optional[List[str]] = None) -> CLIOptions:
        """
        解析命令行参数。
        
        Args:
            args: 命令行参数列表，如果为None则使用sys.argv
            
        Returns:
            解析后的CLI选项
        """
        parser = argparse.ArgumentParser(
            description="Auto-Coder 命令行工具",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例:
  # 基本使用
  auto-coder.run "Write a function to calculate Fibonacci numbers" --model gpt-4
  
  # 通过管道提供输入
  echo "Explain this code" | auto-coder.run --model gpt-4
  
  # 指定输出格式
  auto-coder.run "Generate a hello world function" --output-format json --model gpt-4
  
  # 继续最近的对话
  auto-coder.run --continue "继续修改代码" --model gpt-4
  
  # 恢复特定会话
  auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000 "新的请求" --model gpt-4
  
  # 组合使用多个选项
  auto-coder.run "Optimize this code" --model claude-3-sonnet --max-turns 5 --verbose
"""
        )
        
        # 会话选项（移除模式选择，--continue 和 --resume 作为独立参数）
        parser.add_argument("-c", "--continue", dest="continue_session", action="store_true",
                           help="继续最近的对话")
        parser.add_argument("-r", "--resume", dest="resume_session", metavar="SESSION_ID",
                           help="恢复特定会话")
        
        # 输入输出选项
        parser.add_argument("prompt", nargs="?", help="提示内容，如果未提供则从stdin读取")
        parser.add_argument("--output-format", choices=["text", "json", "stream-json"],
                          default="text", help="输出格式 (默认: text)")
        parser.add_argument("--input-format", choices=["text", "json", "stream-json"],
                          default="text", help="输入格式 (默认: text)")
        parser.add_argument("-v", "--verbose", action="store_true", help="输出详细信息")
        
        # 高级选项
        advanced = parser.add_argument_group("高级选项")
        advanced.add_argument("--max-turns", type=int, default=3, help="最大对话轮数 (默认: 3)")
        advanced.add_argument("--system-prompt", help="系统提示")
        advanced.add_argument("--allowed-tools", nargs="+", help="允许使用的工具列表")
        advanced.add_argument("--permission-mode", choices=["manual", "acceptEdits"],
                           default="manual", help="权限模式 (默认: manual)")
        advanced.add_argument("--model", required=True, help="指定使用的模型名称 (如: gpt-4, gpt-3.5-turbo, claude-3-sonnet 等)")
        
        # 启用自动补全
        if ARGCOMPLETE_AVAILABLE:
            # 添加自定义补全器
            cls._setup_completers(parser)
            argcomplete.autocomplete(parser)
        
        # 解析参数
        parsed_args = parser.parse_args(args)
        
        # 转换为CLIOptions
        options = CLIOptions(
            continue_session=parsed_args.continue_session,
            resume_session=parsed_args.resume_session,
            prompt=parsed_args.prompt,
            output_format=parsed_args.output_format,
            input_format=parsed_args.input_format,
            verbose=parsed_args.verbose,
            max_turns=parsed_args.max_turns,
            system_prompt=parsed_args.system_prompt,
            allowed_tools=parsed_args.allowed_tools or [],
            permission_mode=parsed_args.permission_mode,
            model=parsed_args.model
        )
        
        return options
    
    @classmethod
    def _setup_completers(cls, parser: argparse.ArgumentParser) -> None:
        """设置自定义补全器"""
        if not ARGCOMPLETE_AVAILABLE:
            return
            
        # 为 --allowed-tools 参数设置补全器
        def tools_completer(prefix, parsed_args, **kwargs):
            """工具名称补全器"""
            available_tools = [
                "execute_command",
                "read_file", 
                "write_to_file",
                "replace_in_file",
                "search_files",
                "list_files",
                "list_code_definition_names",
                "ask_followup_question",
                "attempt_completion",
                "list_package_info",
                "mcp_tool",
                "rag_tool"
            ]
            return [tool for tool in available_tools if tool.startswith(prefix)]
        
        # 为 --resume 参数设置会话ID补全器
        def session_id_completer(prefix, parsed_args, **kwargs):
            """会话ID补全器"""
            try:
                # 这里可以从会话存储中获取可用的会话ID
                # 目前返回示例会话ID格式
                return [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                    "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
                ]
            except Exception:
                return []
        
        # 为 prompt 参数设置示例补全器
        def prompt_completer(prefix, parsed_args, **kwargs):
            """提示内容补全器"""
            common_prompts = [
                "Write a function to calculate Fibonacci numbers",
                "Explain this code",
                "Generate a hello world function",
                "Create a simple web page",
                "Write unit tests for this code",
                "Refactor this function",
                "Add error handling",
                "Optimize this algorithm",
                "Document this code",
                "Fix the bug in this code"
            ]
            return [prompt for prompt in common_prompts if prompt.lower().startswith(prefix.lower())]
        
        # 为 --model 参数设置模型名称补全器
        def model_completer(prefix, parsed_args, **kwargs):
            """模型名称补全器"""
            common_models = [
                # OpenAI models
                "gpt-4",
                "gpt-4-turbo",
                "gpt-4-turbo-preview",
                "gpt-4-0125-preview",
                "gpt-4-1106-preview",
                "gpt-3.5-turbo",
                "gpt-3.5-turbo-16k",
                "gpt-3.5-turbo-1106",
                # Anthropic models
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
                "claude-2.1",
                "claude-2.0",
                "claude-instant-1.2",
                # Google models
                "gemini-pro",
                "gemini-pro-vision",
                # Local/Open source models
                "llama2-7b",
                "llama2-13b",
                "llama2-70b",
                "codellama-7b",
                "codellama-13b",
                "codellama-34b",
                "mistral-7b",
                "mixtral-8x7b",
                # Azure OpenAI
                "azure-gpt-4",
                "azure-gpt-35-turbo",
            ]
            return [model for model in common_models if model.lower().startswith(prefix.lower())]
        
        # 应用补全器到对应的参数
        for action in parser._actions:
            if hasattr(action, 'dest'):
                if action.dest == 'allowed_tools':
                    action.completer = tools_completer
                elif action.dest == 'resume_session':
                    action.completer = session_id_completer
                elif action.dest == 'prompt':
                    action.completer = prompt_completer
                elif action.dest == 'model':
                    action.completer = model_completer
        
    @classmethod
    def main(cls) -> int:
        """
        CLI主入口点。
        
        Returns:
            退出码，0表示成功，非0表示失败
        """
        try:
            options = cls.parse_args()
            cli = cls()
            result = cli.run(options)
            
            if result.success:
                if result.output:
                    print(result.output)
                return 0
            else:
                print(f"错误: {result.error}", file=sys.stderr)
                return 1
                
        except Exception as e:
            print(f"未处理的错误: {str(e)}", file=sys.stderr)
            return 1


if __name__ == "__main__":
    sys.exit(AutoCoderCLI.main())
