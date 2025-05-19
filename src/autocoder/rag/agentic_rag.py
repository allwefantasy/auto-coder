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
from autocoder.utils.llms import get_single_llm
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
        self.llm = llm 
        self.default_llm = self.llm
        self.context_prune_llm = self.default_llm
        if self.default_llm.get_sub_client("context_prune_model"):
            self.context_prune_llm = self.default_llm.get_sub_client("context_prune_model")

        self.llm = self.default_llm
        if self.default_llm.get_sub_client("agentic_model"):
            self.llm = self.default_llm.get_sub_client("agentic_model")
        
        self.rag = rag        
        super().__init__(name, self.llm, files, args, conversation_history, default_tools_list=["read_file"])        
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

    @byzerllm.prompt()
    def system_prompt(self):
        '''
        你是一个基于知识库的智能助手，我的核心能力是通过检索增强生成（RAG）技术来回答用户问题。

        你的工作流程如下：
        1. 当用户提出问题时，你首先理解问题的核心意图和关键信息需求
        2. 你会从多个角度分析问题，确定最佳的检索策略和关键词，然后召回工具 recall 获取与问题最相关的详细内容，只有在特别有必要的情况下，你才回使用 read_file 来获得相关文件更详细的信息。
        5. 如果获得的信息足够回答用户问题，你会直接生成回答。
        6. 如果获得的信息不足以回答用户问题，你会继续使用 recall 工具，直到你确信已经获取了足够的信息来回答用户问题。
        7. 有的问题可能需要拆解成多个问题，分别进行recall,然后最终得到的结果才是完整信息，最后才能进行回答。                
        8. 当你遇到图片的时候，请根据图片前后文本内容推测改图片与问题的相关性，有相关性则在回答中使用 ![]()格式输出该Markdown图片路径，否则不输出。        
        {% if local_image_host %}
        9. 图片路径处理
        - 图片地址需返回绝对路径, 
        - 对于Windows风格的路径，需要转换为Linux风格， 例如：![image](C:\\Users\\user\\Desktop\\image.png) 转换为 ![image](C:/Users/user/Desktop/image.png)
        - 为请求图片资源 需增加 http://{{ local_image_host }}/static/ 作为前缀
        举个例子：![image](/path/to/images/image.png)， 返回 ![image](http://{{ local_image_host }}/static/path/to/images/image.png)
        {% endif %} 
        '''    
        return {
            "local_image_host": self.args.local_image_host
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
                           
            recall_request = AgentRequest(user_input=self.conversation_to_query.prompt(conversations))              
            rag_agent = RAGAgent(
                name="RAGAgent",
                llm=self.llm,
                files=SourceCodeList(sources=[]),
                args=self.args,
                rag=self.rag,
                conversation_history=[]
            ) 

            rag_agent.who_am_i(self.system_prompt.prompt())
                                     
            events =rag_agent.run_with_generator(recall_request)
            for (t,content) in events:    
                if t == "thinking":                          
                    yield ("", SingleOutputMeta(
                    generated_tokens_count=0,
                    input_tokens_count=0,
                    reasoning_content=content,                    
                ))
                else:
                    yield (content, SingleOutputMeta(
                        generated_tokens_count=0,
                        input_tokens_count=0,
                        reasoning_content="",                    
                    ))

        return _generate_sream(), context

        

    
