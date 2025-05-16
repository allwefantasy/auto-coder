import json
import os
import time
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import pathspec
from byzerllm import ByzerLLM
import byzerllm
from loguru import logger
import traceback

from autocoder.common import AutoCoderArgs, SourceCode
from importlib.metadata import version
from pydantic import BaseModel
from autocoder.common import openai_content as OpenAIContentProcessor
from autocoder.rag.long_context_rag import LongContextRAG
import json, os
from autocoder.agent.base_agentic.base_agent import BaseAgent
from autocoder.agent.base_agentic.types import AgentRequest
from autocoder.common import SourceCodeList
from autocoder.rag.tools import register_search_tool, register_recall_tool
from byzerllm.utils.types import SingleOutputMeta
try:
    from autocoder_pro.rag.llm_compute import LLMComputeEngine
    pro_version = version("auto-coder-pro")
    autocoder_version = version("auto-coder")
    logger.warning(
        f"auto-coder-pro({pro_version}) plugin is enabled in auto-coder.rag({autocoder_version})")
except ImportError:
    logger.warning(
        "Please install auto-coder-pro to enhance llm compute ability")
    LLMComputeEngine = None


class RAGAgent(BaseAgent):    
    def __init__(self, name: str, 
        llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], 
        files: SourceCodeList, 
        args: AutoCoderArgs, 
        rag: LongContextRAG,
        conversation_history: Optional[List[Dict[str, Any]]] = None):
        super().__init__(name, llm, files, args, conversation_history, default_tools_list=["read_file"])        
        # 注册RAG工具
        # register_search_tool()
        register_recall_tool()

class AgenticRAG:
    def __init__(
        self,
        llm: ByzerLLM,
        args: AutoCoderArgs,
        path: str,
        tokenizer_path: Optional[str] = None,
    ) -> None:
       self.llm = llm
       self.args = args
       self.path = path
       self.tokenizer_path = tokenizer_path
       self.rag = LongContextRAG(llm=self.llm, args=self.args, path=self.path, tokenizer_path=self.tokenizer_path) 


    def build(self):
        pass

    def search(self, query: str) -> List[SourceCode]:
        return []
    

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
        extra_request_params: Dict[str, Any] = {}
    ):        
        try:
            return self._stream_chat_oai(
                conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
                extra_request_params=extra_request_params
            )
        except Exception as e:
            logger.error(f"Error in stream_chat_oai: {str(e)}")
            traceback.print_exc()
            return ["出现错误，请稍后再试。"], []

    @byzerllm.prompt()
    def conversation_to_query(self,messages: List[Dict[str, Any]]):
        '''        
        【历史对话】按时间顺序排列，从旧到新：
        {% for message in messages %}
        <message>
        {% if message.role == "user" %}【用户】{% else %}【助手】{% endif %}    
        <content>
        {{ message.content }}
        </content>
        </message>
        {% endfor %}
        
        【当前问题】用户的最新需求如下:
        <current_query>
        {{ query }}
        </current_query>            
        ''' 
        temp_messages = messages[0:-1]
        message = messages[-1]

        return {
            "messages": temp_messages,
            "query":message["content"]
        }

    
    def _stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
        extra_request_params: Dict[str, Any] = {}
    ):
        if not llm_config:
            llm_config = {}
        
        if extra_request_params:
            llm_config.update(extra_request_params)
        
        conversations = OpenAIContentProcessor.process_conversations(conversations)                

        context = []

        def _generate_sream():
                           
            recall_request = AgentRequest(self.conversation_to_query(conversations))              
            rag_agent = RAGAgent(
                name="RAGAgent",
                llm=self.llm,
                files=SourceCodeList(sources=[]),
                args=self.args,
                rag=self.rag,
                conversation_history=[]
            ) 

            rag_agent.who_am_i('''
                我是一个基于知识库的智能助手，我的核心能力是通过检索增强生成（RAG）技术来回答用户问题。

                我的工作流程如下：
                1. 当用户提出问题时，我会首先理解问题的核心意图和关键信息需求
                2. 我会从多个角度分析问题，确定最佳的检索策略和关键词    
                4. 我会多次使用召回工具 recall 获取与问题最相关的详细内容，如果有必要我可能还会使用 read_file 来获得更完整的细信息，直到我觉得信息已经足够回答用户了。
                5. 我会综合分析检索到的信息，确保信息的完整性和相关性
                6. 我会持续从不同角度进行搜索和召回，直到我确信已经获取了足够的信息来回答用户问题
                7. 我会基于检索到的信息生成准确、全面且有条理的回答

                我的优势：
                - 我不依赖于预训练知识，而是直接从最新的知识库中获取信息
                - 我能够提供基于事实的、有出处的回答，并且可以引用源代码和文档
                - 我能够处理复杂的技术问题，特别是与代码实现相关的问题
                - 我会清晰地区分哪些信息来自知识库，哪些是我的推理或建议

                在回答问题时，我会：
                - 明确指出信息的来源（如文件路径等）
                - 优先使用知识库中的信息，避免生成可能不准确的内容
                - 当知识库中没有足够信息时，我会坦诚告知用户，并提供基于已有信息的最佳建议
                - 提供有条理、易于理解的回答，必要时使用代码示例、列表或表格增强可读性    
                ''')
                                     
            events =rag_agent.run_with_events(recall_request)
            for event in events:
                content = event.content
                if not isinstance(event.content, str):
                    content = json.dumps(event.content,ensure_ascii=False)
                yield (content, SingleOutputMeta(
                    generated_tokens_count=0,
                    reasoning_content=0,
                    model=""
                ))

        return _generate_sream(), context

        

    
