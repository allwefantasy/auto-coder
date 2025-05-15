from typing import Any, Dict, List, Optional, Union, Callable
from byzerllm.utils.client.types import (
    LLMFunctionCallResponse,
    LLMClassResponse, LLMResponse
)
import pydantic
from byzerllm import ByzerLLM
from byzerllm.utils.client import LLMResponse
from byzerllm.utils.types import SingleOutputMeta
from autocoder.rag.long_context_rag import LongContextRAG
from loguru import logger
from byzerllm.utils.langutil import asyncfy_with_semaphore


class LLWrapper:

    def __init__(self, llm: ByzerLLM, rag: Union[LongContextRAG]):
        self.llm = llm
        self.rag = rag

    def chat_oai(self,
                 conversations,
                 tools: List[Union[Callable, str]] = [],
                 tool_choice: Optional[Union[Callable, str]] = None,
                 execute_tool: bool = False,
                 impl_func: Optional[Callable] = None,
                 execute_impl_func: bool = False,
                 impl_func_params: Optional[Dict[str, Any]] = None,
                 func_params: Optional[Dict[str, Any]] = None,
                 response_class: Optional[Union[pydantic.BaseModel, str]] = None,
                 response_after_chat: Optional[Union[pydantic.BaseModel, str]] = False,
                 enable_default_sys_message: bool = True,
                 model: Optional[str] = None,
                 role_mapping=None,
                 llm_config: Dict[str, Any] = {},
                 only_return_prompt: bool = False,
                 extra_request_params: Dict[str, Any] = {}
                 ) -> Union[List[LLMResponse], List[LLMFunctionCallResponse], List[LLMClassResponse]]:
        res, contexts = self.rag.stream_chat_oai(
            conversations, llm_config=llm_config, extra_request_params=extra_request_params)
        metadata = {"request_id":""}
        output = ""
        for chunk in res:
            output += chunk[0]
            metadata["input_tokens_count"] = chunk[1].input_tokens_count
            metadata["generated_tokens_count"] = chunk[1].generated_tokens_count
            metadata["reasoning_content"] = chunk[1].reasoning_content
            metadata["finish_reason"] = chunk[1].finish_reason
            metadata["first_token_time"] = chunk[1].first_token_time
            
        return [LLMResponse(output=output, metadata=metadata, input="")]

    def stream_chat_oai(self, conversations,
                        model: Optional[str] = None,
                        role_mapping=None,
                        delta_mode=False,
                        llm_config: Dict[str, Any] = {},
                        extra_request_params: Dict[str, Any] = {}
                        ):
        res, contexts = self.rag.stream_chat_oai(
                conversations, llm_config=llm_config, extra_request_params=extra_request_params)

        if isinstance(res, tuple):
            for (t, metadata) in res:
                yield (t, SingleOutputMeta(
                    input_tokens_count=metadata.get("input_tokens_count", 0),
                    generated_tokens_count=metadata.get(
                        "generated_tokens_count", 0),
                    reasoning_content=metadata.get("reasoning_content", ""),
                    finish_reason=metadata.get("finish_reason", "stop"),
                    first_token_time=metadata.get("first_token_time", 0)
                ))
        else:
            for t in res:
                yield (t, SingleOutputMeta(0, 0))

    async def async_stream_chat_oai(self, conversations,
                                    model: Optional[str] = None,
                                    role_mapping=None,
                                    delta_mode=False,
                                    llm_config: Dict[str, Any] = {},
                                    extra_request_params: Dict[str, Any] = {}
                                    ):
        res, contexts = await asyncfy_with_semaphore(lambda: self.rag.stream_chat_oai(conversations, llm_config=llm_config, extra_request_params=extra_request_params))()
        # res,contexts = await self.llm.async_stream_chat_oai(conversations,llm_config=llm_config)
        for t in res:
            yield t

    def __getattr__(self, name):
        return getattr(self.llm, name)
