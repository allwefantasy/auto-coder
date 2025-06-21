"""
命令处理器模块

提供统一的命令处理器，支持单次运行和会话复用功能。
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from ..core import AutoCoderCore
from ..models import AutoCodeOptions, Message
from ..exceptions import AutoCoderSDKError
from .options import CLIOptions, CLIResult
from .formatters import OutputFormatter, InputFormatter


class CommandHandler:
    """命令处理器基类，提供通用功能。"""
    
    def __init__(self, options: CLIOptions, cwd: Optional[str] = None):
        """
        初始化命令处理器。
        
        Args:
            options: CLI选项
            cwd: 当前工作目录，如果为None则使用系统当前目录
        """
        self.options = options
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.output_formatter = OutputFormatter(verbose=options.verbose)
        self.input_formatter = InputFormatter()
        
    def _create_core_options(self) -> AutoCodeOptions:
        """
        创建核心选项。
        
        Returns:
            AutoCodeOptions实例
        """
        return AutoCodeOptions(
            max_turns=self.options.max_turns,
            system_prompt=self.options.system_prompt,
            cwd=str(self.cwd),
            allowed_tools=self.options.allowed_tools,
            permission_mode=self.options.permission_mode,
            output_format=self.options.output_format,
            stream=self.options.output_format.startswith("stream"),
            session_id=self.options.resume_session,
            continue_session=self.options.continue_session,
            model=self.options.model
        )
        
    def _get_prompt(self) -> str:
        """
        获取提示内容，如果未提供则从stdin读取。
        
        Returns:
            提示内容
            
        Raises:
            ValueError: 如果未提供提示且stdin为空
        """
        if self.options.prompt:
            return self.options.prompt
            
        # 从stdin读取
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            if not content.strip():
                raise ValueError("未提供提示内容且标准输入为空")
                
            # 根据输入格式处理
            if self.options.input_format == "text":
                return self.input_formatter.format_text(content)
            elif self.options.input_format == "json":
                result = self.input_formatter.format_json(content)
                # 尝试提取提示内容
                if isinstance(result, dict):
                    if "prompt" in result:
                        return result["prompt"]
                    elif "message" in result:
                        message = result["message"]
                        if isinstance(message, dict) and "content" in message:
                            return message["content"]
                        elif isinstance(message, str):
                            return message
                return content  # 如果无法提取，则返回原始内容
            else:
                # 对于流式输入，暂时只支持直接传递
                return content
        else:
            raise ValueError("未提供提示内容且没有标准输入")


class PrintModeHandler(CommandHandler):
    """统一的命令处理器，支持单次运行和会话复用。"""
    
    def handle(self) -> CLIResult:
        """
        处理命令，支持会话复用。
        
        Returns:
            命令执行结果
        """
        try:
            prompt = self._get_prompt()
            core_options = self._create_core_options()
            core = AutoCoderCore(core_options)

            # 根据会话参数构建完整的 prompt
            final_prompt = self._build_prompt_with_session_context(prompt)
            
            # 根据输出格式选择不同的处理方式
            if self.options.output_format == "stream-json":
                # 流式JSON输出
                result = asyncio.run(self._handle_stream(core, final_prompt))
            else:
                # 同步查询
                response = core.query_sync(final_prompt)
                
                # 格式化输出
                if self.options.output_format == "json":
                    result = self.output_formatter.format_json(response)
                else:
                    result = self.output_formatter.format_text(response)
                    
            return CLIResult(success=True, output=result)
            
        except Exception as e:
            return CLIResult(success=False, error=str(e))
    
    def _build_prompt_with_session_context(self, prompt: str) -> str:
        """
        根据会话参数构建完整的 prompt。
        
        Args:
            prompt: 原始提示内容
            
        Returns:
            str: 构建后的完整提示
        """
        if self.options.continue_session:
            return f" {prompt}" if prompt else ""
        elif self.options.resume_session:
            return f"/resume {self.options.resume_session} {prompt}" if prompt else f"/resume {self.options.resume_session}"
        else:
            return f"/new {prompt}"
            
    async def _handle_stream(self, core: AutoCoderCore, prompt: str) -> str:
        """
        处理流式输出。
        
        Args:
            core: AutoCoderCore实例
            prompt: 提示内容
            
        Returns:
            处理结果
        """
        result = []
        async for message in core.query_stream(prompt):
            formatted = await anext(self.output_formatter.format_stream_json([message]))
            result.append(formatted)
            # 实时输出到stdout
            print(formatted, flush=True)
            
        return "\n".join(result)


