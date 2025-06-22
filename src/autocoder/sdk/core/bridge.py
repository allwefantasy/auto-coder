"""
Auto-Coder SDK 桥接层

连接 SDK 和底层 auto_coder_runner 功能
"""

import os
import sys
from typing import Any, Dict, Optional, Iterator, Union
from pathlib import Path
import subprocess

from ..exceptions import BridgeError
from ..models.responses import StreamEvent
from autocoder.auto_coder_runner import run_auto_command,configure
from ..models.options import AutoCodeOptions

# 不导入事件类型，使用动态检查避免类型冲突


class AutoCoderBridge:
    """桥接层，连接现有功能"""

    def __init__(self, project_root: str,options:AutoCodeOptions):
        """
        初始化桥接层

        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or os.getcwd()
        self.options = options  
        self._setup_environment()

    def _setup_environment(self):
        """设置环境和内存"""
        try:
            # 切换到项目根目录
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            # 尝试初始化 auto_coder_runner 环境
            try:
                self.init_project_if_required()
                from autocoder.auto_coder_runner import start                
                start()
            except ImportError:
                # 如果无法导入，跳过初始化
                pass

            # 恢复原始工作目录
            os.chdir(original_cwd)

        except Exception as e:
            # 设置环境失败不应该阻止程序运行
            pass

    def init_project_if_required(self):
        if not os.path.exists(".auto-coder") or not os.path.exists("actions"):
            subprocess.run(
                ["auto-coder", "init", "--source_dir", "."], check=True
            )        

    def call_run_auto_command(
        self,
        query: str,
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None,
        stream: bool = True
    ) -> Iterator[StreamEvent]:
        """
        调用 run_auto_command 功能并返回事件流

        Args:
            query: 查询内容
            pre_commit: 是否预提交
            extra_args: 额外参数
            stream: 是否流式返回

        Yields:
            StreamEvent: 事件流

        Raises:
            BridgeError: 桥接层错误
        """
        try:
            # 切换到项目根目录
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            # 准备参数
            extra_args = extra_args or {}

            # 发送开始事件
            yield StreamEvent(
                event_type="start",
                data={"query": query, "pre_commit": pre_commit}
            )
            
            try:
               
                configure(f"model:{self.options.model}")
                events = run_auto_command(
                    query=query,
                    pre_commit=pre_commit,
                    extra_args=extra_args
                )

                # 如果返回的是生成器，逐个处理事件
                if hasattr(events, '__iter__') and not isinstance(events, (str, bytes)):
                    for event in events:
                        # 转换事件格式
                        stream_event = self._convert_event_to_stream_event(
                            event)
                        if stream_event:  # 只yield非None的事件
                            yield stream_event
                else:
                    # 如果不是生成器，包装成单个事件
                    yield StreamEvent(
                        event_type="content",
                        data={"content": str(events)}
                    )

            except (ImportError, FileNotFoundError, Exception) as e:
                # import traceback
                # traceback.print_exc()
                # 如果无法导入或出现其他错误
                raise BridgeError(
                    f"run_auto_command failed: {str(e)}", original_error=e)

            # 发送完成事件
            yield StreamEvent(
                event_type="end",
                data={"status": "completed"}
            )

        except Exception as e:
            # 发送错误事件
            yield StreamEvent(
                event_type="error",
                data={"error": str(e), "error_type": type(e).__name__}
            )
            raise BridgeError(
                f"run_auto_command failed: {str(e)}", original_error=e)
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)

    def _simulate_auto_command_response(self, query: str) -> Iterator[StreamEvent]:
        """
        模拟 auto_command 响应

        Args:
            query: 查询内容

        Yields:
            StreamEvent: 模拟的事件流
        """
        yield StreamEvent(
            event_type="content",
            data={"content": f"[模拟模式] 正在处理查询: {query}"}
        )
        yield StreamEvent(
            event_type="content",
            data={"content": f"[模拟模式] 这是对您查询的模拟响应。在真实环境中，Auto-Coder 会："}
        )

        # 根据查询内容生成合适的模拟响应
        if any(keyword in query.lower() for keyword in ["function", "函数", "write", "create", "写"]):
            yield StreamEvent(
                event_type="content",
                data={"content": "1. 分析您的需求"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "2. 生成相应的代码"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "3. 添加适当的注释和文档"}
            )
        elif any(keyword in query.lower() for keyword in ["error", "错误", "handling", "处理"]):
            yield StreamEvent(
                event_type="content",
                data={"content": "1. 识别潜在的错误点"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "2. 添加 try-catch 块"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "3. 添加适当的日志记录"}
            )
        elif any(keyword in query.lower() for keyword in ["explain", "解释", "how", "如何"]):
            yield StreamEvent(
                event_type="content",
                data={"content": "1. 分析代码结构"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "2. 提供详细的解释"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "3. 给出使用示例"}
            )
        else:
            yield StreamEvent(
                event_type="content",
                data={"content": "1. 理解您的请求"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "2. 执行相应的操作"}
            )
            yield StreamEvent(
                event_type="content",
                data={"content": "3. 返回结果"}
            )

        yield StreamEvent(
            event_type="content",
            data={"content": "\n注意：当前运行在模拟模式下。要使用完整功能，请确保正确安装 Auto-Coder 核心组件。"}
        )

    def _convert_event_to_stream_event(self, event: Any) -> Optional[StreamEvent]:
        """
        将 run_auto_command 的事件转换为 StreamEvent

        Args:
            event: 原始事件

        Returns:
            StreamEvent: 转换后的事件，如果不需要转换则返回 None
        """
        try:
            # 获取事件类型名称
            event_class_name = type(event).__name__

            # 根据事件类型名称进行转换
            if event_class_name == "LLMThinkingEvent":
                return StreamEvent(
                    event_type="llm_thinking",
                    data={"text": getattr(event, 'text', '')}
                )

            elif event_class_name == "LLMOutputEvent":
                return StreamEvent(
                    event_type="llm_output",
                    data={"text": getattr(event, 'text', '')}
                )

            elif event_class_name == "ToolCallEvent":
                tool_name = "Unknown"
                tool_args = {}
                tool_xml = ""

                if hasattr(event, 'tool'):
                    tool_name = type(event.tool).__name__ if hasattr(
                        event.tool, '__class__') else "Unknown"
                    if hasattr(event.tool, 'model_dump'):
                        try:
                            tool_args = event.tool.model_dump()
                        except:
                            tool_args = {}
                    elif hasattr(event.tool, '__dict__'):
                        tool_args = event.tool.__dict__

                if hasattr(event, 'tool_xml'):
                    tool_xml = event.tool_xml

                return StreamEvent(
                    event_type="tool_call",
                    data={
                        "tool_name": tool_name,
                        "args": tool_args,
                        "tool_xml": tool_xml
                    }
                )

            elif event_class_name == "ToolResultEvent":
                result_data = {
                    "tool_name": getattr(event, 'tool_name', 'Unknown'),
                    "success": True,
                    "message": "",
                    "content": None
                }

                if hasattr(event, 'result') and event.result:
                    if hasattr(event.result, 'success'):
                        result_data["success"] = event.result.success
                    if hasattr(event.result, 'message'):
                        result_data["message"] = event.result.message
                    if hasattr(event.result, 'content'):
                        result_data["content"] = event.result.content

                return StreamEvent(
                    event_type="tool_result",
                    data=result_data
                )

            elif event_class_name == "CompletionEvent":
                result = ""
                if hasattr(event, 'completion'):
                    if hasattr(event.completion, 'result'):
                        result = event.completion.result
                    elif hasattr(event.completion, 'response'):
                        result = event.completion.response

                return StreamEvent(
                    event_type="completion",
                    data={"result": result}
                )

            elif event_class_name == "ErrorEvent":
                return StreamEvent(
                    event_type="error",
                    data={"error": getattr(
                        event, 'message', 'Unknown error'), "error_type": "AgenticError"}
                )

            elif event_class_name == "TokenUsageEvent":
                return StreamEvent(
                    event_type="token_usage",
                    data={"usage": getattr(event, 'usage', {})}
                )

            elif event_class_name == "WindowLengthChangeEvent":
                return StreamEvent(
                    event_type="window_change",
                    data={"tokens_used": getattr(event, 'tokens_used', 0)}
                )

            elif event_class_name == "ConversationIdEvent":
                return StreamEvent(
                    event_type="conversation_id",
                    data={"conversation_id": getattr(
                        event, 'conversation_id', '')}
                )

            elif event_class_name == "PlanModeRespondEvent":
                result = ""
                if hasattr(event, 'completion'):
                    if hasattr(event.completion, 'response'):
                        result = event.completion.response

                return StreamEvent(
                    event_type="plan_mode_respond",
                    data={"result": result}
                )

            # 处理简单字符串或其他类型
            elif isinstance(event, str):
                return StreamEvent(
                    event_type="content",
                    data={"content": event}
                )

            # 如果有event_type属性，尝试直接使用
            elif hasattr(event, 'event_type'):
                return StreamEvent(
                    event_type=event.event_type,
                    data=getattr(event, 'data', {}),
                    timestamp=getattr(event, 'timestamp', None)
                )

            # 未知事件类型，包装成内容事件
            else:
                return StreamEvent(
                    event_type="content",
                    data={"content": str(event)}
                )

        except Exception as e:
            # 转换失败，返回错误事件
            return StreamEvent(
                event_type="content",
                data={"content": f"[Event Conversion Error: {str(e)}]"}
            )

    def get_memory(self) -> Dict[str, Any]:
        """
        获取当前内存状态

        Returns:
            Dict[str, Any]: 内存数据
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            try:
                from autocoder.auto_coder_runner import get_memory
                memory_data = get_memory()
                return memory_data
            except ImportError:
                # 模拟内存数据
                return {
                    "current_files": {"files": [], "groups": {}},
                    "conf": {},
                    "exclude_dirs": [],
                    "mode": "auto_detect"
                }

        except Exception as e:
            raise BridgeError(
                f"Failed to get memory: {str(e)}", original_error=e)
        finally:
            os.chdir(original_cwd)

    def save_memory(self, memory_data: Dict[str, Any]) -> None:
        """
        保存内存状态

        Args:
            memory_data: 要保存的内存数据
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            try:
                from autocoder.auto_coder_runner import save_memory, memory
                # 更新全局 memory 变量
                memory.update(memory_data)
                save_memory()
            except ImportError:
                # 模拟保存
                pass

        except Exception as e:
            raise BridgeError(
                f"Failed to save memory: {str(e)}", original_error=e)
        finally:
            os.chdir(original_cwd)

    def get_project_config(self) -> Dict[str, Any]:
        """
        获取项目配置

        Returns:
            Dict[str, Any]: 项目配置
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            try:
                from autocoder.auto_coder_runner import get_final_config
                config = get_final_config()
                return config.__dict__ if hasattr(config, '__dict__') else {}
            except ImportError:
                # 模拟配置
                return {"mock_config": True}

        except Exception as e:
            raise BridgeError(
                f"Failed to get project config: {str(e)}", original_error=e)
        finally:
            os.chdir(original_cwd)

    def setup_project_context(self) -> None:
        """设置项目上下文"""
        try:
            # 确保项目环境已正确初始化
            self._setup_environment()
        except Exception as e:
            raise BridgeError(
                f"Failed to setup project context: {str(e)}", original_error=e)

    def cleanup(self) -> None:
        """清理资源"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)

            try:
                from autocoder.auto_coder_runner import stop
                stop()
            except ImportError:
                pass

        except Exception as e:
            # 清理失败不应该阻止程序继续运行，只记录错误
            print(f"Warning: Failed to cleanup resources: {str(e)}")
        finally:
            os.chdir(original_cwd)

    def __enter__(self):
        """上下文管理器入口"""
        self.setup_project_context()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()
