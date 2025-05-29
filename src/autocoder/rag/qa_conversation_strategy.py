from abc import ABC, abstractmethod
from typing import List, Dict, Any, Generator
import byzerllm
from autocoder.common import AutoCoderArgs
from autocoder.common.rulefiles.autocoderrules_utils import get_rules

class QAConversationStrategy(ABC):
    """
    Abstract base class for conversation strategies.
    Different strategies organize documents and conversations differently.
    """
    @abstractmethod
    def create_conversation(self, documents: List[Any], conversations: List[Dict[str,str]], local_image_host: str) -> List[Dict]:
        """
        Create a conversation structure based on documents and history
        
        Args:
            documents: List of retrieved documents
            conversations: conversation turns
            
        Returns:
            List of message dictionaries representing the conversation to send to the model
        """
        pass

class MultiRoundStrategy(QAConversationStrategy):
    """
    Multi-round strategy: First let the model read documents, then do Q&A.
    Creates multiple conversation turns.
    """
    def __init__(self, args: AutoCoderArgs):
        self.args = args

    def create_conversation(self, documents: List[Any], conversations: List[Dict[str,str]], local_image_host: str) -> List[Dict]:
        messages = []    
        messages.extend([
            {"role": "user", "content": self._read_docs_prompt.prompt(documents, local_image_host)},
            {"role": "assistant", "content": "好的"}
        ]) 
        messages.extend(conversations)
        return messages
    
    @byzerllm.prompt()
    def _read_docs_prompt_old(
        self, relevant_docs: List[str], local_image_host: str
    ) -> Generator[str, None, None]:
        """        
        请阅读以下：
        <documents>
        {% for doc in relevant_docs %}
        {{ doc }}
        {% endfor %}
        </documents>

        阅读完成后，使用以上文档来回答用户的问题。回答要求：

        1. 严格基于文档内容回答        
        - 如果文档提供的信息无法回答问题,请明确回复:"抱歉,文档中没有足够的信息来回答这个问题。" 
        - 不要添加、推测或扩展文档未提及的信息

        2. 格式如 ![image](/path/to/images/path.png) 的 Markdown 图片处理
        - 根据Markdown 图片前后文本内容推测改图片与问题的相关性，有相关性则在回答中输出该Markdown图片路径
        - 根据相关图片在文档中的位置，自然融入答复内容,保持上下文连贯
        - 完整保留原始图片路径,不省略任何部分

        3. 回答格式要求
        - 使用markdown格式提升可读性        
        {% if local_image_host %}
        4. 图片路径处理
        - 图片地址需返回绝对路径, 
        - 对于Windows风格的路径，需要转换为Linux风格， 例如：C:\\Users\\user\\Desktop\\image.png 转换为 C:/Users/user/Desktop/image.png
        - 为请求图片资源 需增加 http://{{ local_image_host }}/static/ 作为前缀
        例如：/path/to/images/image.png， 返回 http://{{ local_image_host }}/static/path/to/images/image.png
        {% endif %}
        """
    
    @byzerllm.prompt()
    def _read_docs_prompt(
        self, relevant_docs: List[str], local_image_host: str
    ) -> Generator[str, None, None]:
        """
        You are a knowledgeable assistant capable of answering any user question strictly based on the retrieved documents.

        ====

        FILES CONTEXT

        The following files are provided to you as context for the user's task. Use these files to understand the project and answer questions strictly based on their content.

        <documents>
        {% for doc in relevant_docs %}
        {{ doc }}
        {% endfor %}
        </documents>

        ====        

        INSTRUCTIONS

        - Use ONLY the information from the provided documents and extension docs.
        - If the documents do not contain enough information to answer, reply: "抱歉,文档中没有足够的信息来回答这个问题。"
        - Do NOT invent, guess, or add information beyond what is provided.

        - For Markdown images like ![image](/path/to/image.png):
          - Analyze surrounding text to determine relevance.
          - Include relevant images naturally in your answer, preserving image paths.
          - Convert Windows paths to Linux style (e.g., C:\\path\\to\\img.png -> C:/path/to/img.png)
          {% if local_image_host %}
          - Prefix image URLs with http://{{ local_image_host }}/static/
          {% endif %}

        - Format your answer with Markdown for readability.                
        - Always use the language used by the user in their question.

        {% if extra_docs %}
        ====

        RULES PROVIDED BY USER

        The following rules are provided by the user, and you must follow them strictly.

        {% for key, value in extra_docs.items() %}
        ### {{ key }}
        {{ value }}
        {% endfor %}        
        {% endif %}

        """        
        extra_docs = get_rules()               
        return {"extra_docs": extra_docs}

class SingleRoundStrategy(QAConversationStrategy):
    """
    Single-round strategy: Put documents and conversation history in a single round.
    """
    def create_conversation(self, documents: List[Any], conversations: List[Dict[str,str]], local_image_host: str) -> List[Dict]:
        messages = []                
        messages.extend([
            {"role": "user", "content": self._single_round_answer_question.prompt(documents, conversations, local_image_host)}
        ])         
        return messages
    
    @byzerllm.prompt()
    def _single_round_answer_question_old(
        self, relevant_docs: List[str], conversations: List[Dict[str, str]], local_image_host: str
    ) -> Generator[str, None, None]:
        """        
        文档：
        <documents>
        {% for doc in relevant_docs %}
        {{ doc }}
        {% endfor %}
        </documents>

        用户历史对话：
        <conversations>
        {% for msg in conversations %}
        <{{ msg.role }}>: {{ msg.content }}
        {% endfor %}
        </conversations>

        使用以上文档来回答用户最后的问题。回答要求：

        1. 严格基于文档内容回答        
        - 如果文档提供的信息无法回答问题,请明确回复:"抱歉,文档中没有足够的信息来回答这个问题。" 
        - 不要添加、推测或扩展文档未提及的信息

        2. 格式如 ![image](/path/to/images/path.png) 的 Markdown 图片处理
        - 根据Markdown 图片前后文本内容推测改图片与问题的相关性，有相关性则在回答中输出该Markdown图片路径
        - 根据相关图片在文档中的位置，自然融入答复内容,保持上下文连贯
        - 完整保留原始图片路径,不省略任何部分

        3. 回答格式要求
        - 使用markdown格式提升可读性
        {% if local_image_host %}
        4. 图片路径处理
        - 图片地址需返回绝对路径, 
        - 对于Windows风格的路径，需要转换为Linux风格， 例如：C:\\Users\\user\\Desktop\\image.png 转换为 C:/Users/user/Desktop/image.png
        - 为请求图片资源 需增加 http://{{ local_image_host }}/static/ 作为前缀
        例如：/path/to/images/image.png， 返回 http://{{ local_image_host }}/static/path/to/images/image.png
        {% endif %}
        """
    
    @byzerllm.prompt()
    def _single_round_answer_question(
        self, relevant_docs: List[str], conversations: List[Dict[str, str]], local_image_host: str
    ) -> Generator[str, None, None]:
        """
        You are a knowledgeable assistant capable of answering any user question strictly based on the retrieved documents.

        ====

        FILES CONTEXT

        The following files are provided to you as context for the user's task. Use these files to understand the project and answer questions strictly based on their content.

        <documents>
        {% for doc in relevant_docs %}
        {{ doc }}
        {% endfor %}
        </documents>

        ====        

        USER CONVERSATION HISTORY

        {% for msg in conversations %}
        <{{ msg.role }}>: {{ msg.content }}
        {% endfor %}

        ====

        INSTRUCTIONS

        - Use ONLY the information from the provided documents and extension docs.
        - If the documents do not contain enough information to answer, reply: "抱歉,文档中没有足够的信息来回答这个问题。"
        - Do NOT invent, guess, or add information beyond what is provided.

        
        {% if local_image_host %}
        - For Markdown images like ![image](/path/to/image.png):
          - Analyze surrounding text to determine relevance.
          - Include relevant images naturally in your answer, preserving image paths.
          - Convert Windows paths to Linux style (e.g., C:\\path\\to\\img.png -> C:/path/to/img.png)  
          - Prefix image URLs with http://{{ local_image_host }}/static/
          for example: ![image](/path/to/image.png), return ![image](http://{{ local_image_host }}/static/path/to/image.png)
        {% endif %}

        - Format your answer with Markdown for readability.        
        - Always use the language used by the user in their question.

        {% if extra_docs %}
        ====

        RULES PROVIDED BY USER

        The following rules are provided by the user, and you must follow them strictly.

        {% for key, value in extra_docs.items() %}
        ### {{ key }}
        {{ value }}
        {% endfor %}        
        {% endif %}

        """        
        extra_docs = extra_docs = get_rules()
        return {"extra_docs": extra_docs}

def get_qa_strategy(args: AutoCoderArgs) -> QAConversationStrategy:
    """
    Factory method to get the appropriate conversation strategy based on AutoCoderArgs

    Args:
        args: AutoCoderArgs instance containing configuration, including strategy name in `rag_qa_conversation_strategy`

    Returns:
        An instance of the requested strategy

    Raises:
        ValueError: If the requested strategy doesn't exist
    """
    strategy_name = getattr(args, 'rag_qa_conversation_strategy', None) or "multi_round"

    strategies = {
        "multi_round": MultiRoundStrategy,
        "single_round": SingleRoundStrategy,
    }

    if strategy_name not in strategies:
        raise ValueError(f"Unknown strategy: {strategy_name}. Available strategies: {list(strategies.keys())}")

    return strategies[strategy_name](args)
