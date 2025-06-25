"""
EventRunner 提供将代理事件转换为标准事件系统格式的功能。

这个模块负责将内部代理事件转换为标准事件系统格式，并通过事件管理器写入。
它支持流式处理事件和结果事件的写入。
"""

import logging
from typing import Any, Dict, Optional

from autocoder.common.v2.agent.agentic_edit_types import (
    AgenticEditRequest, AgentEvent, CompletionEvent,
    LLMOutputEvent, LLMThinkingEvent, ToolCallEvent,
    ToolResultEvent, TokenUsageEvent, ErrorEvent,PlanModeRespondEvent,
    WindowLengthChangeEvent,ConversationIdEvent
)
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events.event_types import EventMetadata
from autocoder.events import event_content as EventContentCreator
from byzerllm.utils.types import SingleOutputMeta
from .base_runner import BaseRunner

logger = logging.getLogger(__name__)

class EventRunner(BaseRunner):
    """
    将代理事件转换为标准事件系统格式并写入事件管理器。
    
    这个运行器负责将内部代理事件转换为标准事件系统格式，
    并通过事件管理器写入，支持流式处理和结果事件。
    """
    
    def run(self, request: AgenticEditRequest) -> None:
        """
        Runs the agentic edit process, converting internal events to the
        standard event system format and writing them using the event manager.
        """
        event_manager = get_event_manager(self.args.event_file)
        self.apply_pre_changes()              

        try:
            event_stream = self.analyze(request)
            for agent_event in event_stream:
                content = None
                metadata = EventMetadata(
                    action_file=self.args.file,
                    is_streaming=False,
                    stream_out_type="/agent/edit")
                
                if isinstance(agent_event, LLMThinkingEvent):
                    content = EventContentCreator.create_stream_thinking(
                        content=agent_event.text)
                    metadata.is_streaming = True
                    metadata.path = "/agent/edit/thinking"
                    event_manager.write_stream(
                        content=content.to_dict(), metadata=metadata.to_dict())
                elif isinstance(agent_event, LLMOutputEvent):
                    content = EventContentCreator.create_stream_content(
                        content=agent_event.text)
                    metadata.is_streaming = True
                    metadata.path = "/agent/edit/output"
                    event_manager.write_stream(content=content.to_dict(),
                                            metadata=metadata.to_dict())
                
                elif isinstance(agent_event, ToolCallEvent):
                    tool_name = type(agent_event.tool).__name__
                    metadata.path = "/agent/edit/tool/call"
                    content = EventContentCreator.create_result(
                        content={
                            "tool_name": tool_name,
                            **agent_event.tool.model_dump()
                        },
                        metadata={}
                    )
                    event_manager.write_result(
                        content=content.to_dict(), metadata=metadata.to_dict())
                elif isinstance(agent_event, ToolResultEvent):
                    metadata.path = "/agent/edit/tool/result"
                    content = EventContentCreator.create_result(
                        content={
                            "tool_name": agent_event.tool_name,
                            **agent_event.result.model_dump()
                        },
                        metadata={}
                    )
                    event_manager.write_result(
                        content=content.to_dict(), metadata=metadata.to_dict())
                
                elif isinstance(agent_event, PlanModeRespondEvent):
                    metadata.path = "/agent/edit/plan_mode_respond"
                    content = EventContentCreator.create_markdown_result(
                        content=agent_event.completion.response,
                        metadata={}
                    )
                    event_manager.write_result(
                        content=content.to_dict(), metadata=metadata.to_dict())

                elif isinstance(agent_event, TokenUsageEvent):
                    last_meta: SingleOutputMeta = agent_event.usage
                    # Get model info for pricing
                    from autocoder.utils import llms as llm_utils
                    model_name = ",".join(llm_utils.get_llm_names(self.llm))
                    model_info = llm_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                    input_price = model_info.get(
                        "input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get(
                        "output_price", 0.0) if model_info else 0.0

                    # Calculate costs
                    input_cost = (last_meta.input_tokens_count *
                                input_price) / 1000000  # Convert to millions
                    # Convert to millions
                    output_cost = (
                        last_meta.generated_tokens_count * output_price) / 1000000

                    # 添加日志记录
                    logger.info(f"Token Usage Details: Model={model_name}, Input Tokens={last_meta.input_tokens_count}, Output Tokens={last_meta.generated_tokens_count}, Input Cost=${input_cost:.6f}, Output Cost=${output_cost:.6f}")
                    
                    # 直接将每次的 TokenUsageEvent 写入到事件中
                    metadata.path = "/agent/edit/token_usage"
                    content = EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                        model_name=model_name,
                        elapsed_time=0.0,
                        first_token_time=last_meta.first_token_time,
                        input_tokens=last_meta.input_tokens_count,
                        output_tokens=last_meta.generated_tokens_count,
                        input_cost=input_cost,
                        output_cost=output_cost
                    ).to_dict())
                    event_manager.write_result(content=content.to_dict(), metadata=metadata.to_dict())
                
                elif isinstance(agent_event, CompletionEvent):
                    # 在这里完成实际合并
                    try:
                        self.apply_changes()
                    except Exception as e:
                        logger.exception(
                            f"Error merging shadow changes to project: {e}")                                        

                    metadata.path = "/agent/edit/completion"
                    content = EventContentCreator.create_completion(
                        success_code="AGENT_COMPLETE",
                        success_message="Agent attempted task completion.",
                        result={
                            "response": agent_event.completion.result
                        }
                    )
                    event_manager.write_completion(
                        content=content.to_dict(), metadata=metadata.to_dict())
                elif isinstance(agent_event, WindowLengthChangeEvent):
                    # 处理窗口长度变化事件
                    metadata.path = "/agent/edit/window_length_change"
                    content = EventContentCreator.create_result(
                        content={
                            "tokens_used": agent_event.tokens_used
                        },
                        metadata={}
                    )
                    event_manager.write_result(
                        content=content.to_dict(), metadata=metadata.to_dict())
                    
                    # 记录日志
                    logger.info(f"当前会话总 tokens: {agent_event.tokens_used}")

                elif isinstance(agent_event, ConversationIdEvent):
                    metadata.path = "/agent/edit/conversation_id"
                    content = EventContentCreator.create_result(
                        content={
                            "conversation_id": agent_event.conversation_id
                        },
                        metadata={}
                    )
                    event_manager.write_result(content=content.to_dict(), metadata=metadata.to_dict())    
                    
                elif isinstance(agent_event, ErrorEvent):                                        
                    metadata.path = "/agent/edit/error"
                    content = EventContentCreator.create_error(
                        error_code="AGENT_ERROR",
                        error_message=agent_event.message,
                        details={"agent_event_type": "ErrorEvent"}
                    )
                    event_manager.write_error(
                        content=content.to_dict(), metadata=metadata.to_dict())
                else:
                    metadata.path = "/agent/edit/error"
                    logger.warning(
                        f"Unhandled agent event type: {type(agent_event)}")
                    content = EventContentCreator.create_error(
                        error_code="AGENT_ERROR",
                        error_message=f"Unhandled agent event type: {type(agent_event)}",
                        details={"agent_event_type": type(
                            agent_event).__name__}
                    )
                    event_manager.write_error(
                        content=content.to_dict(), metadata=metadata.to_dict())

        except Exception as e:
            logger.exception(
                "An unexpected error occurred during agent execution:")
            metadata = EventMetadata(
                action_file=self.args.file,
                is_streaming=False,
                stream_out_type="/agent/edit/error")
                
            # 发送累计的TokenUsageEvent数据（在错误情况下也需要发送）            
                
            error_content = EventContentCreator.create_error(
                error_code="AGENT_FATAL_ERROR",
                error_message=f"An unexpected error occurred: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
            event_manager.write_error(
                content=error_content.to_dict(), metadata=metadata.to_dict())
            # Re-raise the exception if needed, or handle appropriately
            raise e
