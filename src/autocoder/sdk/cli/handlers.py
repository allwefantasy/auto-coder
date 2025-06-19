"""
命令处理器模块

提供处理不同命令行模式的处理器，包括打印模式和会话模式。
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from ..core import AutoCoderCore
from ..session import SessionManager
from ..models import AutoCodeOptions, Message
from ..exceptions import SessionNotFoundError, AutoCoderSDKError
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
            session_id=self.options.resume_session
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
    """打印模式处理器，执行一次查询后退出。"""
    
    def handle(self) -> CLIResult:
        """
        处理打印模式命令。
        
        Returns:
            命令执行结果
        """
        try:
            prompt = self._get_prompt()
            core_options = self._create_core_options()
            core = AutoCoderCore(core_options)
            
            # 根据输出格式选择不同的处理方式
            if self.options.output_format == "stream-json":
                # 流式JSON输出
                result = asyncio.run(self._handle_stream(core, prompt))
            else:
                # 同步查询
                response = core.query_sync(prompt)
                
                # 格式化输出
                if self.options.output_format == "json":
                    result = self.output_formatter.format_json(response)
                else:
                    result = self.output_formatter.format_text(response)
                    
            return CLIResult(success=True, output=result)
            
        except Exception as e:
            return CLIResult(success=False, error=str(e))
            
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


class SessionModeHandler(CommandHandler):
    """会话模式处理器，支持多轮对话。"""
    
    def handle(self) -> CLIResult:
        """
        处理会话模式命令。
        
        Returns:
            命令执行结果
        """
        try:
            core_options = self._create_core_options()
            core = AutoCoderCore(core_options)
            session_manager = core.get_session_manager()
            
            # 根据选项决定是继续最近会话还是恢复特定会话
            if self.options.continue_session:
                return self._continue_latest_session(session_manager)
            elif self.options.resume_session:
                return self._resume_specific_session(session_manager)
            else:
                # 创建新会话
                return self._create_new_session(session_manager)
                
        except SessionNotFoundError as e:
            return CLIResult(success=False, error=f"会话未找到: {str(e)}")
        except Exception as e:
            return CLIResult(success=False, error=str(e))
            
    def _continue_latest_session(self, session_manager: SessionManager) -> CLIResult:
        """
        继续最近的会话。
        
        Args:
            session_manager: 会话管理器
            
        Returns:
            命令执行结果
        """
        try:
            session = session_manager.get_latest_session()
            if not session:
                return CLIResult(success=False, error="没有找到最近的会话")
                
            prompt = self._get_prompt() if self.options.prompt else None
            if prompt:
                response = asyncio.run(session.query(prompt))
                
                # 格式化输出
                if self.options.output_format == "json":
                    output = self.output_formatter.format_json(response)
                else:
                    output = self.output_formatter.format_text(response)
                    
                return CLIResult(success=True, output=output)
            else:
                # 如果没有提示，则显示会话历史
                history = session.get_history()
                
                if self.options.output_format == "json":
                    output = self.output_formatter.format_json({"history": history})
                else:
                    output = self._format_history_text(history)
                    
                return CLIResult(success=True, output=output)
                
        except Exception as e:
            return CLIResult(success=False, error=str(e))
            
    def _resume_specific_session(self, session_manager: SessionManager) -> CLIResult:
        """
        恢复特定会话。
        
        Args:
            session_manager: 会话管理器
            
        Returns:
            命令执行结果
        """
        try:
            session = session_manager.get_session(self.options.resume_session)
            
            prompt = self._get_prompt() if self.options.prompt else None
            if prompt:
                response = asyncio.run(session.query(prompt))
                
                # 格式化输出
                if self.options.output_format == "json":
                    output = self.output_formatter.format_json(response)
                else:
                    output = self.output_formatter.format_text(response)
                    
                return CLIResult(success=True, output=output)
            else:
                # 如果没有提示，则显示会话历史
                history = session.get_history()
                
                if self.options.output_format == "json":
                    output = self.output_formatter.format_json({"history": history})
                else:
                    output = self._format_history_text(history)
                    
                return CLIResult(success=True, output=output)
                
        except Exception as e:
            return CLIResult(success=False, error=str(e))
            
    def _create_new_session(self, session_manager: SessionManager) -> CLIResult:
        """
        创建新会话。
        
        Args:
            session_manager: 会话管理器
            
        Returns:
            命令执行结果
        """
        try:
            session = session_manager.create_session(self._create_core_options())
            
            prompt = self._get_prompt()
            response = asyncio.run(session.query(prompt))
            
            # 格式化输出
            if self.options.output_format == "json":
                output = self.output_formatter.format_json(response)
            else:
                output = self.output_formatter.format_text(response)
                
            return CLIResult(success=True, output=output)
                
        except Exception as e:
            return CLIResult(success=False, error=str(e))
            
    def _format_history_text(self, history: List[Message]) -> str:
        """
        将会话历史格式化为文本。
        
        Args:
            history: 会话历史
            
        Returns:
            格式化后的文本
        """
        result = []
        for message in history:
            role = "用户" if message.role == "user" else "助手"
            result.append(f"[{role}]\n{message.content}\n")
            
        return "\n".join(result)
