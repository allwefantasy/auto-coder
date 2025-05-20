from datetime import datetime
import json
import os
import threading
import time
import re
import xml.sax.saxutils
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Union, Optional, Tuple, Type, Generator, Iterator
from rich.console import Console
from rich.panel import Panel
from loguru import logger
import byzerllm
from pydantic import BaseModel

from autocoder.common import AutoCoderArgs, git_utils, SourceCodeList, SourceCode
from autocoder.common.global_cancel import global_cancel
from autocoder.rag.variable_holder import VariableHolder
from autocoder.utils import llms as llms_utils
from autocoder.common.global_cancel import global_cancel
from autocoder.common import detect_env
from autocoder.common import shells
from autocoder.common.printer import Printer
from autocoder.utils.auto_project_type import ProjectTypeAnalyzer
from autocoder.common.mcp_server import get_mcp_server, McpServerInfoRequest
from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_required_and_index_rules
from autocoder.auto_coder_runner import load_tokenizer
from autocoder.linters.shadow_linter import ShadowLinter
from autocoder.compilers.shadow_compiler import ShadowCompiler
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events.event_types import Event, EventType, EventMetadata
from autocoder.events import event_content as EventContentCreator
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common.file_checkpoint.models import FileChange as CheckpointFileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager as CheckpointFileChangeManager
from autocoder.linters.normal_linter import NormalLinter
from autocoder.compilers.normal_compiler import NormalCompiler

from .types import (
    BaseTool, ToolResult, AgentRequest, FileChangeEntry,
    LLMOutputEvent, LLMThinkingEvent, ToolCallEvent, ToolResultEvent, 
    CompletionEvent, ErrorEvent, TokenUsageEvent, AttemptCompletionTool,    
    PlanModeRespondTool,Message,ReplyDecision, PlanModeRespondEvent
)
from .tool_registry import ToolRegistry
from .tools.base_tool_resolver import BaseToolResolver
from .agent_hub import AgentHub, Group, GroupMembership
from .utils import GroupUtils,GroupMemberResponse
from .default_tools import register_default_tools
from .agentic_tool_display import get_tool_display_message
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from autocoder.common.save_formatted_log import save_formatted_log
from . import agentic_lang

class BaseAgent(ABC):
    """
    基础代理类，所有的代理实现都应继承此类
    遵循初始化顺序规则，避免FileMonitor、token计数器等组件冲突
    """
    
    def __init__(
        self,
        name:str,
        llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
        files: SourceCodeList,
        args: AutoCoderArgs,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        default_tools_list: Optional[List[str]] = None
    ):
        """
        初始化代理

        Args:
            llm: 语言模型客户端
            files: 源码文件列表
            args: 配置参数
            conversation_history: 对话历史记录
        """
        # 1. 初始化FileMonitor（必须最先进行）
        try:
            monitor = FileMonitor(args.source_dir)
            if not monitor.is_running():
                monitor.start()
                logger.info(f"文件监控已启动: {args.source_dir}")
            else:
                logger.info(f"文件监控已在运行中: {monitor.root_dir}")
            
            # 2. 加载规则文件
            _ = get_rules(args.source_dir)
        except Exception as e:
            logger.error(f"初始化文件监控出错: {e}")

        # 3. 加载tokenizer (必须在前两步之后)
        if VariableHolder.TOKENIZER_PATH is None:
            load_tokenizer()
        
        # 4. 初始化基本组件
        self.llm = llm
        self.args = args
        self.files = files
        self.printer = Printer()
        self.conversation_history = conversation_history or []
               
        
        # 5. 初始化其他组件
        self.project_type_analyzer = ProjectTypeAnalyzer(args=args, llm=self.llm)        
       # self.shadow_manager = ShadowManager(
        #     args.source_dir, args.event_file, args.ignore_clean_shadows)
        self.shadow_manager = None
        # self.shadow_linter = ShadowLinter(self.shadow_manager, verbose=False)
        self.shadow_compiler = None
        # self.shadow_compiler = ShadowCompiler(self.shadow_manager, verbose=False)
        self.shadow_linter = None

        self.checkpoint_manager = CheckpointFileChangeManager(
            project_dir=args.source_dir,
            backup_dir=os.path.join(args.source_dir,".auto-coder","checkpoint"),
            store_dir=os.path.join(args.source_dir,".auto-coder","checkpoint_store"),
            max_history=50)
        self.linter = NormalLinter(args.source_dir,verbose=False)
        self.compiler = NormalCompiler(args.source_dir,verbose=False) 
        
        
        
        # MCP 服务信息
        self.mcp_server_info = ""
        try:
            self.mcp_server = get_mcp_server()
            mcp_server_info_response = self.mcp_server.send_request(
                McpServerInfoRequest(
                    model=args.inference_model or args.model,
                    product_mode=args.product_mode,
                )
            )
            self.mcp_server_info = mcp_server_info_response.result
        except Exception as e:
            logger.error(f"Error getting MCP server info: {str(e)}")
            
        # 变更跟踪信息
        # 格式: { file_path: FileChangeEntry(...) }
        self.file_changes: Dict[str, FileChangeEntry] = {}

        self.name = name        

        # 初始化群聊/私聊功能
        self.joined_groups: Dict[str, Group] = {}
        self.private_chats: Dict[str, List[Message]] = {}        
        self.agentic_conversations: List[Dict[str,Any]] = []
        self.custom_system_prompt = "You are a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices."
        self.refuse_reply_reason = ""
        self._group_lock = threading.RLock()  # 保护 joined_groups
        self._chat_lock = threading.RLock()   # 保护 private_chats
        # 自动注册到AgentHub
        AgentHub.register_agent(self)
        register_default_tools(params=self._render_context(), default_tools_list=default_tools_list)
        

    def who_am_i(self, role: str) -> 'BaseAgent':
        self.custom_system_prompt = role
        return self

    def when_to_refuse_reply(self, reason: str) -> 'BaseAgent':
        self.refuse_reply_reason = reason
        return self
    
    def introduce_myself(self) -> str:        
        return self.custom_system_prompt

        
    def join_group(self, group: Group) -> 'GroupMembership':
        if group.name not in self.joined_groups:
            self.joined_groups[group.name] = group            
            group.add_member(self)            
        return GroupMembership(self, group)    
    
    def talk_to_group(self, group: Group, content: str, mentions: List['BaseAgent'] = [], print_conversation: bool = False):
        message = Message(
            sender=self.name,
            content=content,
            is_group=True,
            group_name=group.name,
            mentions=[m.name for m in mentions]
        )
        group.broadcast(message, print_conversation)
        return self

    def choose_group(self,content:str)->List[GroupMemberResponse]:
        group_utils = GroupUtils(self.llm)
        v = group_utils.auto_select_group(content,self.joined_groups.values())
        return v
            
    def talk_to(self, other: Union['BaseAgent', Group], content: str, mentions: List['BaseAgent'] = [], print_conversation: bool = False):
        if isinstance(other, Group):
            return self.talk_to_group(other, content, mentions, print_conversation)
        
        message = Message(
            sender=self.name,
            content=content,
            is_group=False,
            mentions=[m.name for m in mentions]
        )
        if print_conversation:
            print(f"[Private Chat] {self.name} -> {other.name}: {content}")
            
        # 存储双向对话记录
        self._add_private_message(other.name, message)
        other._add_private_message(self.name, message)                
        
        response = other.generate_reply(message)                                
        
        if print_conversation:
            print(f">>> {other.name} reply to {self.name} with strategy: {response.strategy}, reason: {response.reason}")

        if response.strategy == "ignore":            
            return
        elif response.strategy == "private":            
            mentions = [AgentHub.get_agent(m) for m in response.mentions]             
            other.talk_to(other=self, content=response.content, mentions=mentions, print_conversation=print_conversation)
        elif response.strategy == "broadcast":
            warning_msg = f"invalid strategy broadcast action in private chat:[{self.name}] 广播消息给群组 {other.name}: {response.content}"
            logger.warning(warning_msg)
            if print_conversation:
                print(f"[Private Chat Warning] {warning_msg}")
        return self
            
    
    def _add_private_message(self, other_name: str, message: Message):
        with self._chat_lock:
            if other_name not in self.private_chats:
                self.private_chats[other_name] = []
            self.private_chats[other_name].append(message)
    
    def threadsafe_receive(self, message: Message,print_conversation: bool = False):                
        self.receive_message(message,print_conversation=print_conversation)
        
    def receive_message(self, message: Message,print_conversation: bool = False):
        if message.is_group:
            prefix = f"[Group {message.group_name}]"
            if message.mentions and self.name in message.mentions:
                prefix += " @You"
            print(f"{prefix} {message.sender}: {message.content}")                        
            reply_decision = self.generate_reply(message)            
            print(f">>> {self.name} reply to {message.sender} with strategy: {reply_decision.strategy}, reason: {reply_decision.reason}")
            if reply_decision.strategy == "ignore":                
                return
            elif reply_decision.strategy == "private":                
                self.talk_to(other=AgentHub.get_agent(message.sender), content=reply_decision.content,print_conversation=print_conversation)
            elif reply_decision.strategy == "broadcast":
                self.joined_groups[message.group_name].broadcast(Message(
                    sender=self.name,
                    content=reply_decision.content,
                    is_group=True,
                    group_name=message.group_name,
                    mentions=reply_decision.mentions,
                    priority=reply_decision.priority
                ))
        else:
            print(f"[Private] {message.sender}: {message.content}")


    def generate_reply(self, message: Message) -> ReplyDecision:        
        user_input = self._generate_reply.prompt(message)
        events = self.agentic_run(AgentRequest(user_input=user_input))
        for event in events:
            if isinstance(event, CompletionEvent):
                from byzerllm.utils.str2model import to_model
                return to_model(ReplyDecision, event.result)
            elif isinstance(event, ErrorEvent):
                logger.error(f"Error generating reply: {event.error}")
                return ReplyDecision(strategy="ignore", content="", reason="Error generating reply")
        return None
    
    @byzerllm.prompt()
    def _generate_reply(self, message: Message) -> str:
        """
        你的名字是 {{ name }}
        {% if message.is_group %}
        当前群组是 {{ message.group_name }}
        {% endif %}
        当前时间: {{ time }}
        {% if role %}
        你对自己的描述是: 
        <who_are_you>
        {{ role }}
        </who_are_you>
        {% endif %}

        
        {{ message.sender }} 发送了一条{% if message.is_group %}群组消息{% else %}私聊消息{% endif %}：
        <message>
        {{ message.content }}
        </message>
        
        {% if message.mentions and message.mentions|length > 0 %}
        这条消息的发送者特别 @ 了用户：（{{ message.mentions|join(',') }}）。        
        {% endif %}
                
        {% if message.is_group %}
        群组对话上下文：
        <group_message_history>
        {% for msg in group_message_history %}
        {% if msg.sender == name %}
        <role>你/You</role>: <msg>{{ msg.content }}</msg>
        {% else %}
        <role>{{ msg.sender }}</role>: <msg>{{ msg.content }}</msg>
        {% endif %}
        {% endfor %}
        </group_message_history>
        {% else %}
        私聊对话上下文：
        <private_message_history>
        {% for msg in private_message_history %}
        {% if msg.sender == name %}
        <role>你/You</role>: <msg>{{ msg.content }}</msg>
        {% else %}
        <role>{{ msg.sender }}</role>: <msg>{{ msg.content }}</msg>
        {% endif %}
        {% endfor %}
        </private_message_history>
        {% endif %}

        请根据上面内容进行解答，在最后请务必使用 attempt_completion 工具，确保里面的 result 字段包含如下 Json 格式内容：

        ```json
        {
            "content": "回复内容",
            "strategy": "broadcast|private|ignore",
            "mentions": ["被提及的agent名称"],
            "priority": 优先级 0-100,
            "reason": "选择策略的原因"
        }
        ```
        ignore 表示用户发送的消息可以不进行回复,private 我们要回复用户，并且只回复给发送信息的用户，broadcast 表示要回复消息，并且回复给群组所有成员。
        *** 注意，阅读上面的所有内容，尤其关注 {% if message.is_group %}群组上下文{% else %}私聊上下文{% endif %}，判断是否使用 ignore 策略结束对话，避免无意义对话。一般在群组对话中，你没有被 @ 就无需回答，直接使用ignore策略结束对话。 ***
        {% if refuse_reply_reason %}
        当满足以下描述时，你应当拒绝回复：
        <when_to_refuse_reply>
        {{ refuse_reply_reason }}
        </when_to_refuse_reply>
        {% endif %}        
        """
        context = {
            "name": self.name,
            "role": self.custom_system_prompt,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "refuse_reply_reason": self.refuse_reply_reason
        }
        if message.is_group:
            group = self.joined_groups[message.group_name]
            context["group_message_history"] = group.history
        else:
            context["private_message_history"] = self.private_chats.get(message.sender, [])
            
        return context    
    
    def record_file_change(self, file_path: str, change_type: str, diff: Optional[str] = None, content: Optional[str] = None):
        """
        记录单个文件的变更信息。

        Args:
            file_path: 相对路径
            change_type: 'added' 或 'modified'
            diff: 对于 replace_in_file，传入 diff 内容
            content: 最新文件内容（可选，通常用于 write_to_file）
        """
        entry = self.file_changes.get(file_path)
        if entry is None:
            entry = FileChangeEntry(
                type=change_type, diffs=[], content=content)
            self.file_changes[file_path] = entry
        else:
            # 文件已经存在，可能之前是 added，现在又被 modified，或者多次 modified
            # 简单起见，type 用 added 优先，否则为 modified
            if entry.type != "added":
                entry.type = change_type

            # content 以最新为准
            if content is not None:
                entry.content = content

        if diff:
            entry.diffs.append(diff)
    
    def _get_all_file_changes(self) -> Dict[str, FileChangeEntry]:
        """
        获取当前记录的所有文件变更信息。

        Returns:
            字典，key 为文件路径，value 为变更详情
        """
        return self.file_changes
    
    def _get_changed_files_from_shadow(self) -> List[str]:
        """
        获取影子系统当前有哪些文件被修改或新增。

        Returns:
            变更的文件路径列表
        """
        changed_files = []
        shadow_root = self.shadow_manager.shadows_dir
        for root, dirs, files in os.walk(shadow_root):
            for fname in files:
                shadow_file_path = os.path.join(root, fname)
                try:
                    project_file_path = self.shadow_manager.from_shadow_path(
                        shadow_file_path)
                    rel_path = os.path.relpath(
                        project_file_path, self.args.source_dir)
                    changed_files.append(rel_path)
                except Exception:
                    # 非映射关系，忽略
                    continue
        return changed_files
    
    
    def _reconstruct_tool_xml(self, tool: BaseTool) -> str:
        """
        Reconstructs the XML representation of a tool call from its Pydantic model.
        """
        tool_tag = next(
            (tag for tag, model in ToolRegistry.get_tag_model_map().items() if isinstance(tool, model)), None)
        if not tool_tag:
            logger.error(
                f"Cannot find tag name for tool type {type(tool).__name__}")
            # Return a placeholder or raise? Let's return an error XML string.
            return f"<error>Could not find tag for tool {type(tool).__name__}</error>"

        xml_parts = [f"<{tool_tag}>"]
        for field_name, field_value in tool.model_dump(exclude_none=True).items():
            # Format value based on type, ensuring XML safety
            if isinstance(field_value, bool):
                value_str = str(field_value).lower()
            elif isinstance(field_value, (list, dict)):
                # Simple string representation for list/dict for now.
                # Consider JSON within the tag if needed and supported by the prompt/LLM.
                # Use JSON for structured data
                value_str = json.dumps(field_value, ensure_ascii=False)
            else:
                value_str = str(field_value)

            # Escape the value content
            escaped_value = xml.sax.saxutils.escape(value_str)

            # Handle multi-line content like 'content' or 'diff' - ensure newlines are preserved
            if '\n' in value_str:
                # Add newline before closing tag for readability if content spans multiple lines
                xml_parts.append(
                    f"<{field_name}>\n{escaped_value}\n</{field_name}>")
            else:
                xml_parts.append(
                    f"<{field_name}>{escaped_value}</{field_name}>")

        xml_parts.append(f"</{tool_tag}>")
        # Join with newline for readability, matching prompt examples
        return "\n".join(xml_parts)
    
    @byzerllm.prompt()
    def _system(self, request: AgentRequest) -> str:
        """        
        {{system_prompt}}

        ====        

        TOOL USE

        You have access to a set of tools that are executed upon the user's approval. You can use one tool per message, and will receive the result of that tool use in the user's response. You use tools step-by-step to accomplish a given task, with each tool use informed by the result of the previous tool use.

        # Tool Use Formatting

        Tool use is formatted using XML-style tags. The tool name is enclosed in opening and closing tags, and each parameter is similarly enclosed within its own set of tags. Here's the structure:

        <tool_name>
        <parameter1_name>value1</parameter1_name>
        <parameter2_name>value2</parameter2_name>
        ...
        </tool_name>

        For example:

        <read_file>
        <path>src/main.js</path>
        </read_file>

        Always adhere to this format for the tool use to ensure proper parsing and execution.


        # Tools

        {% for tool_tag, tool_description in tool_descriptions.items() %}
        ## {{ tool_tag }}
        {{ tool_description.description }}                
        {% endfor %}        

        {%if mcp_server_info %}
        ### MCP_SERVER_LIST
        {{mcp_server_info}}
        {%endif%}

        {%if agent_info %}                   
        ### AVAILABLE_AGENTS
        {{agent_info}}
        {%endif%}

        {%if group_info %}
        ### AVAILABLE_GROUPS
        {{group_info}}
        {%endif%}

        # Tool Use Examples
        {% set example_count = 0 %}
        {% for tool_tag, example in tool_examples.items() %}
        {% if example %}
        {% set example_count = example_count + 1 %}
        ## Example {{ example_count }}: {{ example.title }}
        {{ example.body }}
        {% endif %}
        {% endfor %}                                      

        
        # Tool Use Guidelines

        1. In <thinking> tags, assess what information you already have and what information you need to proceed with the task.
        2. Choose the most appropriate tool based on the task and the tool descriptions provided. Assess if you need additional information to proceed, and which of the available tools would be most effective for gathering this information. For example using the list_files tool is more effective than running a command like \`ls\` in the terminal. It's critical that you think about each available tool and use the one that best fits the current step in the task.
        3. If multiple actions are needed, use one tool at a time per message to accomplish the task iteratively, with each tool use being informed by the result of the previous tool use. Do not assume the outcome of any tool use. Each step must be informed by the previous step's result.
        4. Formulate your tool use using the XML format specified for each tool.
        5. After each tool use, the user will respond with the result of that tool use. This result will provide you with the necessary information to continue your task or make further decisions. This response may include:
        - Information about whether the tool succeeded or failed, along with any reasons for failure.
        - Linter errors that may have arisen due to the changes you made, which you'll need to address.
        - New terminal output in reaction to the changes, which you may need to consider or act upon.
        - Any other relevant feedback or information related to the tool use.
        6. ALWAYS wait for user confirmation after each tool use before proceeding. Never assume the success of a tool use without explicit confirmation of the result from the user.
        {% for tool_name, guideline in tool_guidelines.items() %}                
        {{ loop.index + 6 }}. **{{ tool_name }}**: {{ guideline }}
        {% endfor %}

        It is crucial to proceed step-by-step, waiting for the user's message after each tool use before moving forward with the task. This approach allows you to:
        1. Confirm the success of each step before proceeding.
        2. Address any issues or errors that arise immediately.
        3. Adapt your approach based on new information or unexpected results.
        4. Ensure that each action builds correctly on the previous ones.        
        

        By waiting for and carefully considering the user's response after each tool use, you can react accordingly and make informed decisions about how to proceed with the task. This iterative process helps ensure the overall success and accuracy of your work.
                
        {% for case_name, case_info in tool_case_docs.items() %}
        
        ====

        # {{ case_name | upper }}
        
        {{ case_info.doc }}
        {% endfor %}
        
        {% if enable_active_context_in_generate %}
        ====

        PROJECT PACKAGE CONTEXT

        Each directory can contain a short **`active.md`** summary file located under the mirrored path inside
        `{{ current_project }}/.auto-coder/active-context/`.

        * **Purpose** – captures only the files that have **recently changed** in that directory. It is *not* a full listing.
        * **Example** – for `{{ current_project }}/src/abc/bbc`, the summary is
          `{{ current_project }}/.auto-coder/active-context/src/abc/bbc/active.md`.

        **Reading a summary**

        ```xml
        <read_file>
        <path>.auto-coder/active-context/src/abc/bbc/active.md</path>
        </read_file>
        ```

        Use these summaries to quickly decide which files deserve a deeper look with tools like
        `read_file`, `search_files`, or `list_code_definition_names`.

        {% endif %}
        ====

        CAPABILITIES

        - You are a powerful deep research RAG system, specialized in collecting and synthesizing information to answer complex user queries.
        - You can execute commands, list files, perform regex searches, read file contents, ask follow-up questions, and more to help you thoroughly research any topic.
        - When a user presents a task, a list of file paths in the current working directory ('{{ current_project }}') is included in environment_details, providing an overview of the project structure.
        - You can use the search_files tool to perform regex searches in specified directories, with results including context. This is particularly useful for understanding code patterns, finding specific implementations, or identifying areas that need attention.
        - You can use the execute_command tool to run commands on the user's computer to perform specific system operations. Commands will be executed in the current working directory.
        - Remember, the write_to_file and replace_in_file tools are ONLY for creating and updating research plans, search strategies, or summarizing findings—never for modifying system files or operational code.

        ====

        RULES

        - Your current working directory is: {{current_project}}
        - You cannot \`cd\` into a different directory to complete a task. You are stuck operating from '{{ current_project }}', so be sure to pass in the correct 'path' parameter when using tools that require a path.
        - Do not use the ~ character or $HOME to refer to the home directory.
        - Before using the execute_command tool, you must first think about the SYSTEM INFORMATION context provided to understand the user's environment and tailor your commands to ensure they are compatible with their system. You must also consider if the command you need to run should be executed in a specific directory outside of the current working directory '{{ current_project }}', and if so prepend with \`cd\`'ing into that directory && then executing the command (as one command since you are stuck operating from '{{current_project}}'). For example, if you needed to run \`npm install\` in a project outside of '{{current_project}}', you would need to prepend with a \`cd\` i.e. pseudocode for this would be \`cd (path to project) && (command, in this case npm install)\`.
        - When using the search_files tool, craft your regex patterns carefully to balance specificity and flexibility. Based on the user's task you may use it to find code patterns, TODO comments, function definitions, or any text-based information across the project. The results include context, so analyze the surrounding code to better understand the matches. Leverage the search_files tool in combination with other tools for more comprehensive analysis. For example, use it to find specific code patterns, then use read_file to examine the full context of interesting matches.
        - The write_to_file and replace_in_file tools are ONLY to be used for creating and updating research plans, search strategies, or summarizing findings. They are NOT to be used for modifying system files or any operational code.
        - When making research plans, always consider the context and objectives clearly outlined by the user.
        - Do not ask for more information than necessary. Use the tools provided to accomplish the user's request efficiently and effectively. When you've completed your task, you must use the attempt_completion tool to present the result to the user. The user may provide feedback, which you can use to make improvements and try again.
        {% if enable_tool_ask_followup_question %}
        - You are only allowed to ask the user questions using the ask_followup_question tool. Use this tool only when you need additional details to complete a task, and be sure to use a clear and concise question that will help you move forward with the task. However if you can use the available tools to avoid having to ask the user questions, you should do so. For example, if the user mentions a file that may be in an outside directory like the Desktop, you should use the list_files tool to list the files in the Desktop and check if the file they are talking about is there, rather than asking the user to provide the file path themselves.
        - When executing commands, if you don't see the expected output, assume the terminal executed the command successfully and proceed with the task. The user's terminal may be unable to stream the output back properly. If you absolutely need to see the actual terminal output, use the ask_followup_question tool to request the user to copy and paste it back to you.
        {% endif %}
        - The user may provide a file's contents directly in their message, in which case you shouldn't use the read_file tool to get the file contents again since you already have it.
        - Your goal is to try to accomplish the user's task, NOT engage in a back and forth conversation.
        - NEVER end attempt_completion result with a question or request to engage in further conversation! Formulate the end of your result in a way that is final and does not require further input from the user.
        - You are STRICTLY FORBIDDEN from starting your messages with "Great", "Certainly", "Okay", "Sure". You should NOT be conversational in your responses, but rather direct and to the point. For example you should NOT say "Great, I've updated the CSS" but instead something like "I've updated the research findings". It is important you be clear and technical in your messages.
        - When presented with images, utilize your vision capabilities to thoroughly examine them and extract meaningful information. Incorporate these insights into your thought process as you accomplish the user's task.
        - At the end of each user message, you will automatically receive environment_details. This information is not written by the user themselves, but is auto-generated to provide potentially relevant context about the project structure and environment. While this information can be valuable for understanding the project context, do not treat it as a direct part of the user's request or response. Use it to inform your actions and decisions, but don't assume the user is explicitly asking about or referring to this information unless they clearly do so in their message. When using environment_details, explain your actions clearly to ensure the user understands, as they may not be aware of these details.
        - Before executing commands, check the "Actively Running Terminals" section in environment_details. If present, consider how these active processes might impact your task. For example, if a local development server is already running, you wouldn't need to start it again. If no active terminals are listed, proceed with command execution as normal.
        - When using the replace_in_file tool, you must include complete lines in your SEARCH blocks, not partial lines. The system requires exact line matches and cannot match partial lines. For example, if you want to match a line containing "const x = 5;", your SEARCH block must include the entire line, not just "x = 5" or other fragments.
        - When using the replace_in_file tool, if you use multiple SEARCH/REPLACE blocks, list them in the order they appear in the file. For example if you need to make changes to both line 10 and line 50, first include the SEARCH/REPLACE block for line 10, followed by the SEARCH/REPLACE block for line 50.
        - It is critical you wait for the user's response after each tool use, in order to confirm the success of the tool use.        
        - To display LaTeX formulas, use a single dollar sign to wrap inline formulas, like `$E=mc^2$`, and double dollar signs to wrap block-level formulas, like `$$\frac{d}{dx}e^x = e^x$$`.
        - To include flowcharts or diagrams, you can use Mermaid syntax.
        
        {% if extra_docs %}  
        ====
      
        RULES OR  DOCUMENTS PROVIDED BY USER

        The following rules are provided by the user, and you must follow them strictly.

        <user_rule_or_document_files>
        {% for key, value in extra_docs.items() %}
        <user_rule_or_document_file>
        ##File: {{ key }}
        {{ value }}
        </user_rule_or_document_file>
        {% endfor %}  
        </user_rule_or_document_files>              
        
        Make sure you always start your task by using the read_file tool to get the relevant RULE files listed in index.md based on the user's specific requirements.        
        {% endif %}

        ====

        SYSTEM INFORMATION

        Operating System: {{os_distribution}}
        Default Shell: {{shell_type}}
        Home Directory: {{home_dir}}
        Current Working Directory: {{current_project}}

        ====

        OBJECTIVE

        You accomplish a given task iteratively, breaking it down into clear steps and working through them methodically.

        1. Analyze the user's query and identify clear, achievable research objectives. Prioritize these objectives in a logical order.
        2. Sequentially use available tools to gather information, using only one tool at a time. Each objective should correspond to a distinct step in your problem-solving process.
        3. Before using tools, analyze within <thinking></thinking> tags. First examine the file structure in environment_details for context, consider which tool is most relevant, then analyze whether you have enough information for each required parameter. If all required parameters exist or can be reasonably inferred, close the thinking tag and proceed with the tool. If a required parameter value is missing, don't call the tool but instead use ask_followup_question to request information from the user.
        4. After completing the task, use the attempt_completion tool to present your results to the user.
        5. The user may provide feedback for improvements. Avoid pointless back-and-forth conversations; don't end responses with questions or offers of further assistance.
        
        {% if file_paths_str %}
        ====
        The following are files that the user is currently focusing on. 
        Make sure you always start your analysis by using the read_file tool to get the content of the files.
        <files>
        {{file_paths_str}}
        </files>
        {% endif %}
        """
        return self._render_context()
        
    
    def _render_context(self):                
        # 获取工具描述和示例
        tool_descriptions = ToolRegistry.get_all_tool_descriptions()
        tool_examples = ToolRegistry.get_all_tool_examples()
        tool_case_docs = ToolRegistry.get_all_tools_case_docs()
        tool_guidelines = ToolRegistry.get_all_tool_use_guidelines()
        
        extra_docs = get_required_and_index_rules()  
        
        env_info = detect_env()
        shell_type = "bash"
        if shells.is_running_in_cmd():
            shell_type = "cmd"
        elif shells.is_running_in_powershell():
            shell_type = "powershell"

        file_paths_str = "\n".join([file_source.module_name for file_source in self.files.sources])
        
        # 获取代理信息
        agent_info = ""
        agent_names = AgentHub.list_agents()
        if agent_names:
            agent_info = "Available Agents:\n"
            for name in agent_names:                
                agent = AgentHub.get_agent(name)
                if agent:
                    role = getattr(agent, "custom_system_prompt", "No description")
                    if name == self.name:
                        agent_info += f"- {name} (This is you, do not talk to yourself): {role[:100]}{'...' if len(role) > 100 else ''}\n"
                    else:
                        agent_info += f"- {name}: {role[:100]}{'...' if len(role) > 100 else ''}\n"
        
        # 获取群组信息
        group_info = ""
        groups = AgentHub.get_all_groups()
        if groups:
            group_info = "Available Groups:\n"
            for group in groups:
                members = []
                with group._members_lock:
                    members = [member.name for member in group.members]
                group_info += f"- {group.name}: {len(members)} members ({', '.join(members)})\n"
        
        return {
            "conversation_history": self.conversation_history,
            "env_info": env_info,
            "shell_type": shell_type,
            "shell_encoding": shells.get_terminal_encoding(),
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
            "os_distribution": shells.get_os_distribution(),
            "current_user": shells.get_current_username(),
            "current_project": os.path.abspath(self.args.source_dir),
            "home_dir": os.path.expanduser("~"),
            "files": self.files.to_str(),
            "mcp_server_info": self.mcp_server_info,
            "agent_info": agent_info,
            "group_info": group_info,
            "enable_active_context_in_generate": self.args.enable_active_context_in_generate,
            "extra_docs": extra_docs,
            "file_paths_str": file_paths_str,            
            "tool_descriptions": tool_descriptions,
            "tool_examples": tool_examples,
            "tool_case_docs": tool_case_docs,
            "tool_guidelines": tool_guidelines,
            "system_prompt": self.custom_system_prompt,
            "name": self.name
        }
    
    def agentic_run(self, request: AgentRequest) -> Generator[Union[LLMOutputEvent, LLMThinkingEvent, ToolCallEvent, ToolResultEvent, CompletionEvent, ErrorEvent], None, None]:
        """
        Analyzes the user request, interacts with the LLM, parses responses,
        executes tools, and yields structured events for visualization until completion or error.
        """
        logger.info(f"Starting analyze method with user input: {request.user_input[:50]}...")
        system_prompt = self._system.prompt(request)
        logger.info(f"Generated system prompt with length: {len(system_prompt)}")
        
        # print(system_prompt)
        self.agentic_conversations.clear()
        conversations = self.agentic_conversations
        conversations = [
            {"role": "system", "content": system_prompt},
        ] 
                                
        conversations.append({
            "role": "user", "content": request.user_input
        })        
        
        logger.info(
            f"Initial conversation history size: {len(conversations)}")
        
        logger.info(f"Conversation history: {json.dumps(conversations, indent=2,ensure_ascii=False)}")

        iteration_count = 0
        tool_executed = False
        
        should_yield_completion_event = False   
        completion_event = None    

        while True:
            iteration_count += 1            
            logger.info(f"Starting LLM interaction cycle #{iteration_count}")
            global_cancel.check_and_raise(token=self.args.event_file)
            last_message = conversations[-1]
            if last_message["role"] == "assistant":
                logger.info(f"Last message is assistant, skipping LLM interaction cycle")
                if should_yield_completion_event:
                    if completion_event is None:
                        yield CompletionEvent(completion=AttemptCompletionTool(
                            result=last_message["content"],
                            command=""
                        ), completion_xml="")  
                    else:
                        yield completion_event 
                break
            logger.info(
                f"Starting LLM interaction cycle. History size: {len(conversations)}")

            assistant_buffer = ""
            logger.info("Initializing stream chat with LLM")

            ## 实际请求大模型
            llm_response_gen = stream_chat_with_continue(
                llm=self.llm,
                conversations=conversations,
                llm_config={},  # Placeholder for future LLM configs
                args=self.args
            )
            
            logger.info("Starting to parse LLM response stream")
            parsed_events = self.stream_and_parse_llm_response(
                llm_response_gen)

            event_count = 0
            mark_event_should_finish = False
            for event in parsed_events:
                event_count += 1
                logger.info(f"Processing event #{event_count}: {type(event).__name__}")
                global_cancel.check_and_raise(token=self.args.event_file)

                if mark_event_should_finish:
                    if isinstance(event, TokenUsageEvent):
                        logger.info("Yielding token usage event")
                        yield event
                    continue

                if isinstance(event, (LLMOutputEvent, LLMThinkingEvent)):
                    assistant_buffer += event.text
                    logger.debug(f"Accumulated {len(assistant_buffer)} chars in assistant buffer")
                    yield event  # Yield text/thinking immediately for display                    

                elif isinstance(event, ToolCallEvent):
                    tool_executed = True
                    tool_obj = event.tool
                    tool_name = type(tool_obj).__name__
                    logger.info(f"Tool call detected: {tool_name}")
                    tool_xml = event.tool_xml  # Already reconstructed by parser

                    # Append assistant's thoughts and the tool call to history
                    logger.info(f"Adding assistant message with tool call to conversation history")
                    conversations.append({
                        "role": "assistant",
                        "content": assistant_buffer + tool_xml
                    })                    
                    assistant_buffer = ""  # Reset buffer after tool call

                    yield event  # Yield the ToolCallEvent for display
                    logger.info("Yielded ToolCallEvent")

                    # Handle AttemptCompletion separately as it ends the loop
                    if isinstance(tool_obj, AttemptCompletionTool):
                        logger.info(
                            "AttemptCompletionTool received. Finalizing session.")
                        logger.info(f"Completion result: {tool_obj.result[:50]}...")
                        completion_event = CompletionEvent(completion=tool_obj, completion_xml=tool_xml)
                        logger.info(
                            "AgenticEdit analyze loop finished due to AttemptCompletion.")
                        save_formatted_log(self.args.source_dir, json.dumps(conversations, ensure_ascii=False), "agentic_conversation")    
                        mark_event_should_finish = True
                        should_yield_completion_event = True
                        continue

                    if isinstance(tool_obj, PlanModeRespondTool):
                        logger.info(
                            "PlanModeRespondTool received. Finalizing session.")
                        logger.info(f"Plan mode response: {tool_obj.response[:50]}...")
                        yield PlanModeRespondEvent(completion=tool_obj, completion_xml=tool_xml)
                        logger.info(
                            "AgenticEdit analyze loop finished due to PlanModeRespond.")
                        save_formatted_log(self.args.source_dir, json.dumps(conversations, ensure_ascii=False), "agentic_conversation")    
                        continue

                    # Resolve the tool
                    resolver_cls = ToolRegistry.get_resolver_for_tool(tool_obj)
                    if not resolver_cls:
                        logger.error(
                            f"No resolver implemented for tool {type(tool_obj).__name__}")
                        tool_result = ToolResult(
                            success=False, message="Error: Tool resolver not implemented.", content=None)
                        result_event = ToolResultEvent(tool_name=type(
                            tool_obj).__name__, result=tool_result)
                        error_xml = f"<tool_result tool_name='{type(tool_obj).__name__}' success='false'><message>Error: Tool resolver not implemented.</message><content></content></tool_result>"
                    else:
                        try:
                            logger.info(f"Creating resolver for tool: {tool_name}")
                            resolver = resolver_cls(
                                agent=self, tool=tool_obj, args=self.args)
                            logger.info(
                                f"Executing tool: {type(tool_obj).__name__} with params: {tool_obj.model_dump()}")
                            tool_result: ToolResult = resolver.resolve()
                            logger.info(
                                f"Tool Result: Success={tool_result.success}, Message='{tool_result.message}'")
                            result_event = ToolResultEvent(tool_name=type(
                                tool_obj).__name__, result=tool_result)

                            # Prepare XML for conversation history
                            logger.info("Preparing XML for conversation history")
                            escaped_message = xml.sax.saxutils.escape(
                                tool_result.message)
                            content_str = str(
                                tool_result.content) if tool_result.content is not None else ""
                            escaped_content = xml.sax.saxutils.escape(
                                content_str)
                            error_xml = (
                                f"<tool_result tool_name='{type(tool_obj).__name__}' success='{str(tool_result.success).lower()}'>"
                                f"<message>{escaped_message}</message>"
                                f"<content>{escaped_content}</content>"
                                f"</tool_result>"
                            )
                        except Exception as e:
                            logger.exception(
                                f"Error resolving tool {type(tool_obj).__name__}: {e}")
                            error_message = f"Critical Error during tool execution: {e}"
                            tool_result = ToolResult(
                                success=False, message=error_message, content=None)
                            result_event = ToolResultEvent(tool_name=type(
                                tool_obj).__name__, result=tool_result)
                            escaped_error = xml.sax.saxutils.escape(
                                error_message)
                            error_xml = f"<tool_result tool_name='{type(tool_obj).__name__}' success='false'><message>{escaped_error}</message><content></content></tool_result>"

                    yield result_event  # Yield the ToolResultEvent for display    
                    logger.info("Yielded ToolResultEvent")

                    # Append the tool result (as user message) to history
                    logger.info("Adding tool result to conversation history")
                    conversations.append({
                        "role": "user",  # Simulating the user providing the tool result
                        "content": error_xml
                    })
                    logger.info(
                        f"Added tool result to conversations for tool {type(tool_obj).__name__}")
                    logger.info(f"Breaking LLM cycle after executing tool: {tool_name}")
                    
                    # 一次交互只能有一次工具，剩下的其实就没有用了，但是如果不让流式处理完，我们就无法获取服务端
                    # 返回的token消耗和计费，所以通过此标记来完成进入空转，直到流式走完，获取到最后的token消耗和计费
                    mark_event_should_finish = True
                    # break  # After tool execution and result, break to start a new LLM cycle

                elif isinstance(event, ErrorEvent):
                    logger.error(f"Error event occurred: {event.message}")
                    yield event  # Pass through errors
                    # Optionally stop the process on parsing errors
                    # logger.error("Stopping analyze loop due to parsing error.")
                    # return
                elif isinstance(event, TokenUsageEvent):
                    logger.info("Yielding token usage event")
                    yield event                
            
            if not tool_executed:
                # No tool executed in this LLM response cycle
                logger.info("LLM response finished without executing a tool.")                
                # Append any remaining assistant buffer to history if it wasn't followed by a tool
                if assistant_buffer:
                    logger.info(f"Appending assistant buffer to history: {len(assistant_buffer)} chars")
                    last_message = conversations[-1]
                    if last_message["role"] != "assistant":
                        logger.info("Adding new assistant message")
                        conversations.append(
                            {"role": "assistant", "content": assistant_buffer})
                    elif last_message["role"] == "assistant":
                        logger.info("Appending to existing assistant message")
                        last_message["content"] += assistant_buffer
                
                # 添加系统提示，要求LLM必须使用工具或明确结束，而不是直接退出
                logger.info("Adding system reminder to use tools or attempt completion")
                conversations.append({
                    "role": "user",
                    "content": "NOTE: You must use an appropriate tool (such as read_file, write_to_file, execute_command, etc.) or explicitly complete the task (using attempt_completion). Do not provide text responses without taking concrete actions. Please select a suitable tool to continue based on the user's task."
                })
                # 继续循环，让 LLM 再思考，而不是 break
                logger.info("Continuing the LLM interaction loop without breaking")
                continue
            
        logger.info(f"AgenticEdit analyze loop finished after {iteration_count} iterations.")
        save_formatted_log(self.args.source_dir, json.dumps(conversations, ensure_ascii=False), "agentic_conversation")        
    
    def stream_and_parse_llm_response(
        self, generator: Generator[Tuple[str, Any], None, None]
    ) -> Generator[Union[LLMOutputEvent, LLMThinkingEvent, ToolCallEvent, ErrorEvent], None, None]:
        """
        Streamingly parses the LLM response generator, distinguishing between
        plain text, thinking blocks, and tool usage blocks, yielding corresponding Event models.

        Args:
            generator: An iterator yielding (content, metadata) tuples from the LLM stream.

        Yields:
            Union[LLMOutputEvent, LLMThinkingEvent, ToolCallEvent, ErrorEvent]: Events representing
            different parts of the LLM's response.
        """
        buffer = ""
        in_tool_block = False
        in_thinking_block = False
        current_tool_tag = None
        tool_start_pattern = re.compile(
            r"<([a-zA-Z0-9_]+)>")  # Matches tool tags
        thinking_start_tag = "<thinking>"
        thinking_end_tag = "</thinking>"

        def parse_tool_xml(tool_xml: str, tool_tag: str) -> Optional[BaseTool]:
            """Minimal parser for tool XML string."""
            params = {}
            try:
                # Find content between <tool_tag> and </tool_tag>
                inner_xml_match = re.search(
                    rf"<{tool_tag}>(.*?)</{tool_tag}>", tool_xml, re.DOTALL)
                if not inner_xml_match:
                    logger.error(
                        f"Could not find content within <{tool_tag}>...</{tool_tag}>")
                    return None
                inner_xml = inner_xml_match.group(1).strip()

                # Find <param>value</param> pairs within the inner content
                pattern = re.compile(r"<([a-zA-Z0-9_]+)>(.*?)</\1>", re.DOTALL)
                for m in pattern.finditer(inner_xml):
                    key = m.group(1)
                    # Basic unescaping (might need more robust unescaping if complex values are used)
                    val = xml.sax.saxutils.unescape(m.group(2))
                    params[key] = val

                tool_cls = ToolRegistry.get_model_for_tag(tool_tag)
                if tool_cls:
                    # Attempt to handle boolean conversion specifically for requires_approval
                    if 'requires_approval' in params:
                        params['requires_approval'] = params['requires_approval'].lower(
                        ) == 'true'
                    # Attempt to handle JSON parsing for ask_followup_question_tool
                    if tool_tag == 'ask_followup_question' and 'options' in params:
                        try:
                            params['options'] = json.loads(
                                params['options'])
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Could not decode JSON options for ask_followup_question_tool: {params['options']}")
                            # Keep as string or handle error? Let's keep as string for now.
                            pass
                    if tool_tag == 'plan_mode_respond' and 'options' in params:
                        try:
                            params['options'] = json.loads(
                                params['options'])
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Could not decode JSON options for plan_mode_respond_tool: {params['options']}")
                    # Handle recursive for list_files
                    if tool_tag == 'list_files' and 'recursive' in params:
                        params['recursive'] = params['recursive'].lower() == 'true'
                    return tool_cls(**params)
                else:
                    logger.error(f"Tool class not found for tag: {tool_tag}")
                    return None
            except Exception as e:
                logger.exception(
                    f"Failed to parse tool XML for <{tool_tag}>: {e}\nXML:\n{tool_xml}")
                return None
        
        last_metadata = None      
        for content_chunk, metadata in generator:
            global_cancel.check_and_raise(token=self.args.event_file)                      
            if not content_chunk:
                last_metadata = metadata                
                continue
            
            last_metadata = metadata
            buffer += content_chunk  

            while True:
                # Check for transitions: thinking -> text, tool -> text, text -> thinking, text -> tool
                next_event_pos = len(buffer)
                found_event = False

                # 1. Check for </thinking> if inside thinking block
                if in_thinking_block:
                    end_think_pos = buffer.find(thinking_end_tag)
                    if end_think_pos != -1:
                        thinking_content = buffer[:end_think_pos]
                        yield LLMThinkingEvent(text=thinking_content)
                        buffer = buffer[end_think_pos + len(thinking_end_tag):]
                        in_thinking_block = False
                        found_event = True
                        continue  # Restart loop with updated buffer/state
                    else:
                        # Need more data to close thinking block
                        break

                # 2. Check for </tool_tag> if inside tool block
                elif in_tool_block:
                    end_tag = f"</{current_tool_tag}>"
                    end_tool_pos = buffer.find(end_tag)
                    if end_tool_pos != -1:
                        tool_block_end_index = end_tool_pos + len(end_tag)
                        tool_xml = buffer[:tool_block_end_index]
                        tool_obj = parse_tool_xml(tool_xml, current_tool_tag)

                        if tool_obj:
                            # Reconstruct the XML accurately here AFTER successful parsing
                            # This ensures the XML yielded matches what was parsed.
                            reconstructed_xml = self._reconstruct_tool_xml(
                                tool_obj)
                            if reconstructed_xml.startswith("<error>"):
                                yield ErrorEvent(message=f"Failed to reconstruct XML for tool {current_tool_tag}")
                            else:
                                yield ToolCallEvent(tool=tool_obj, tool_xml=reconstructed_xml)
                        else:
                            yield ErrorEvent(message=f"Failed to parse tool: <{current_tool_tag}>")
                            # Optionally yield the raw XML as plain text?
                            # yield LLMOutputEvent(text=tool_xml)

                        buffer = buffer[tool_block_end_index:]
                        in_tool_block = False
                        current_tool_tag = None
                        found_event = True
                        continue  # Restart loop
                    else:
                        # Need more data to close tool block
                        break

                # 3. Check for <thinking> or <tool_tag> if in plain text state
                else:
                    start_think_pos = buffer.find(thinking_start_tag)
                    tool_match = tool_start_pattern.search(buffer)
                    start_tool_pos = tool_match.start() if tool_match else -1
                    tool_name = tool_match.group(1) if tool_match else None

                    # Determine which tag comes first (if any)
                    first_tag_pos = -1
                    is_thinking = False
                    is_tool = False

                    if start_think_pos != -1 and (start_tool_pos == -1 or start_think_pos < start_tool_pos):
                        first_tag_pos = start_think_pos
                        is_thinking = True
                    elif start_tool_pos != -1 and (start_think_pos == -1 or start_tool_pos < start_think_pos):
                        # Check if it's a known tool
                        if tool_name in ToolRegistry.get_tag_model_map():
                            first_tag_pos = start_tool_pos
                            is_tool = True
                        else:
                            # Unknown tag, treat as text for now, let buffer grow
                            pass

                    if first_tag_pos != -1:  # Found either <thinking> or a known <tool>
                        # Yield preceding text if any
                        preceding_text = buffer[:first_tag_pos]
                        if preceding_text:
                            yield LLMOutputEvent(text=preceding_text)

                        # Transition state
                        if is_thinking:
                            buffer = buffer[first_tag_pos +
                                            len(thinking_start_tag):]
                            in_thinking_block = True
                        elif is_tool:
                            # Keep the starting tag
                            buffer = buffer[first_tag_pos:]
                            in_tool_block = True
                            current_tool_tag = tool_name

                        found_event = True
                        continue  # Restart loop

                    else:
                        # No tags found, or only unknown tags found. Need more data or end of stream.
                        # Yield text chunk but keep some buffer for potential tag start
                        # Keep last 100 chars
                        split_point = max(0, len(buffer) - 100)
                        text_to_yield = buffer[:split_point]
                        if text_to_yield:
                            yield LLMOutputEvent(text=text_to_yield)
                            buffer = buffer[split_point:]
                        break  # Need more data

                # If no event was processed in this iteration, break inner loop
                if not found_event:
                    break               

        # After generator exhausted, yield any remaining content
        if in_thinking_block:
            # Unterminated thinking block
            yield ErrorEvent(message="Stream ended with unterminated <thinking> block.")
            if buffer:
                # Yield remaining as thinking
                yield LLMThinkingEvent(text=buffer)
        elif in_tool_block:
            # Unterminated tool block
            yield ErrorEvent(message=f"Stream ended with unterminated <{current_tool_tag}> block.")
            if buffer:
                yield LLMOutputEvent(text=buffer)  # Yield remaining as text
        elif buffer:
            # Yield remaining plain text
            yield LLMOutputEvent(text=buffer)

        # 这个要放在最后，防止其他关联的多个事件的信息中断
        yield TokenUsageEvent(usage=last_metadata)     
    
    def run_with_events(self, request: AgentRequest):
        """
        运行代理过程，将内部事件转换为标准事件系统格式，并通过事件管理器写入

        Args:
            request: 代理请求
        """
        event_manager = get_event_manager(self.args.event_file)
        base_url = "/agent/base"

        try:
            event_stream = self.agentic_run(request)
            for agent_event in event_stream:
                content = None
                metadata = EventMetadata(
                    action_file=self.args.file,
                    is_streaming=False,
                    stream_out_type=base_url)

                if isinstance(agent_event, LLMThinkingEvent):
                    content = EventContentCreator.create_stream_thinking(
                        content=agent_event.text)
                    metadata.is_streaming = True
                    metadata.path = f"{base_url}/thinking"
                    event_manager.write_stream(
                        content=content.to_dict(), metadata=metadata.to_dict())
                elif isinstance(agent_event, LLMOutputEvent):
                    content = EventContentCreator.create_stream_content(
                        content=agent_event.text)
                    metadata.is_streaming = True
                    metadata.path = f"{base_url}/output"
                    event_manager.write_stream(content=content.to_dict(),
                                               metadata=metadata.to_dict())
                elif isinstance(agent_event, ToolCallEvent):
                    tool_name = type(agent_event.tool).__name__
                    metadata.path = f"{base_url}/tool/call"
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
                    metadata.path = f"{base_url}/tool/result"
                    content = EventContentCreator.create_result(
                        content={
                            "tool_name": agent_event.tool_name,
                            **agent_event.result.model_dump()
                        },
                        metadata={}
                    )
                    event_manager.write_result(
                        content=content.to_dict(), metadata=metadata.to_dict())
                elif isinstance(agent_event, TokenUsageEvent):
                    # 获取模型信息以计算价格
                    model_name = ",".join(llms_utils.get_llm_names(self.llm))
                    model_info = llms_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                    input_price = model_info.get("input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get("output_price", 0.0) if model_info else 0.0

                    # 计算成本
                    last_meta = agent_event.usage
                    input_cost = (last_meta.input_tokens_count * input_price) / 1000000  # 转换为百万
                    output_cost = (last_meta.generated_tokens_count * output_price) / 1000000

                    # 记录Token使用详情
                    logger.info(f"Token Usage Details: Model={model_name}, Input Tokens={last_meta.input_tokens_count}, Output Tokens={last_meta.generated_tokens_count}, Input Cost=${input_cost:.6f}, Output Cost=${output_cost:.6f}")

                    # 写入Token统计事件
                    get_event_manager(self.args.event_file).write_result(
                        EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                            model_name=model_name,
                            elapsed_time=0.0,
                            first_token_time=last_meta.first_token_time,
                            input_tokens=last_meta.input_tokens_count,
                            output_tokens=last_meta.generated_tokens_count,
                            input_cost=input_cost,
                            output_cost=output_cost
                        ).to_dict()), metadata=metadata.to_dict())

                elif isinstance(agent_event, CompletionEvent):
                    # 在这里完成实际合并
                    try:
                        self.apply_changes()
                    except Exception as e:
                        logger.exception(f"Error merging shadow changes to project: {e}")

                    metadata.path = f"{base_url}/completion"
                    content = EventContentCreator.create_completion(
                        success_code="AGENT_COMPLETE",
                        success_message="Agent attempted task completion.",
                        result={
                            "response": agent_event.completion.result
                        }
                    )
                    event_manager.write_completion(
                        content=content.to_dict(), metadata=metadata.to_dict())
                elif isinstance(agent_event, ErrorEvent):
                    metadata.path = f"{base_url}/error"
                    content = EventContentCreator.create_error(
                        error_code="AGENT_ERROR",
                        error_message=agent_event.message,
                        details={"agent_event_type": "ErrorEvent"}
                    )
                    event_manager.write_error(
                        content=content.to_dict(), metadata=metadata.to_dict())
                else:
                    metadata.path = f"{base_url}/error"
                    logger.warning(f"未处理的代理事件类型: {type(agent_event)}")
                    content = EventContentCreator.create_error(
                        error_code="AGENT_ERROR",
                        error_message=f"未处理的代理事件类型: {type(agent_event)}",
                        details={"agent_event_type": type(agent_event).__name__}
                    )
                    event_manager.write_error(
                        content=content.to_dict(), metadata=metadata.to_dict())

        except Exception as e:
            logger.exception("代理执行过程中发生意外错误:")
            metadata = EventMetadata(
                action_file=self.args.file,
                is_streaming=False,
                stream_out_type=f"{base_url}/error")
            error_content = EventContentCreator.create_error(
                error_code="AGENT_FATAL_ERROR",
                error_message=f"发生意外错误: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
            event_manager.write_error(
                content=error_content.to_dict(), metadata=metadata.to_dict())
            raise e

    def run_with_generator(self, request: AgentRequest):        
        start_time = time.time()             
        project_name = os.path.basename(os.path.abspath(self.args.source_dir))
        yield ("thinking",agentic_lang.get_message_with_format("agent_start", project_name=project_name))

        # 添加token累计变量
        total_input_tokens = 0
        total_output_tokens = 0
        total_input_cost = 0.0
        total_output_cost = 0.0
        model_name = ""

        try:
            event_stream = self.agentic_run(request)
            for event in event_stream:
                if isinstance(event, TokenUsageEvent):
                    # 获取模型信息以计算价格
                    from autocoder.utils import llms as llm_utils
                    model_name = ",".join(llm_utils.get_llm_names(self.llm))
                    model_info = llm_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                    input_price = model_info.get(
                        "input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get(
                        "output_price", 0.0) if model_info else 0.0

                    # 计算成本
                    last_meta = event.usage
                    input_cost = (last_meta.input_tokens_count *
                                 input_price) / 1000000  # 转换为百万
                    output_cost = (
                        last_meta.generated_tokens_count * output_price) / 1000000

                    # 累计token使用情况
                    total_input_tokens += last_meta.input_tokens_count
                    total_output_tokens += last_meta.generated_tokens_count
                    total_input_cost += input_cost
                    total_output_cost += output_cost

                    # 记录日志
                    logger.info(agentic_lang.get_message_with_format(
                        "token_usage_log", 
                        model=model_name, 
                        input_tokens=last_meta.input_tokens_count, 
                        output_tokens=last_meta.generated_tokens_count, 
                        input_cost=input_cost, 
                        output_cost=output_cost))
                    
                elif isinstance(event, LLMThinkingEvent):
                    # 以较不显眼的样式呈现思考内容
                    yield ("thinking",f"{event.text}")
                elif isinstance(event, LLMOutputEvent):
                    # 打印常规LLM输出
                    yield ("thinking",event.text)
                elif isinstance(event, ToolCallEvent):
                    # 跳过显示完成工具的调用
                    if hasattr(event.tool, "result") and hasattr(event.tool, "command"):
                        continue  # 不显示完成工具的调用

                    tool_name = type(event.tool).__name__
                    # 使用工具展示函数（需要自行实现）
                    display_content = get_tool_display_message(event.tool)                    
                    yield ("thinking", agentic_lang.get_message_with_format("tool_operation_title", tool_name=tool_name))
                    yield ("thinking",display_content)

                elif isinstance(event, ToolResultEvent):
                    # 跳过显示完成工具的结果
                    if event.tool_name == "AttemptCompletionTool":
                        continue

                    result = event.result 
                    success_status = agentic_lang.get_message("success_status") if result.success else agentic_lang.get_message("failure_status")                   
                    base_content = agentic_lang.get_message_with_format("status", status=success_status) + "\n"
                    base_content += agentic_lang.get_message_with_format("message", message=result.message) + "\n"

                    # 格式化内容函数
                    def _format_content(content):
                        if len(content) > 200:
                            return f"{content[:100]}\n...\n{content[-100:]}"
                        else:
                            return content

                    # 首先准备基本信息面板
                    panel_content = [base_content]
                    syntax_content = None

                    if result.content is not None:
                        content_str = ""
                        try:
                            if isinstance(result.content, (dict, list)):
                                import json
                                content_str = json.dumps(
                                    result.content, indent=2, ensure_ascii=False)
                                syntax_content = _format_content(content_str)                                    
                            elif isinstance(result.content, str) and ('\n' in result.content or result.content.strip().startswith('<')):                                                                
                                syntax_content = _format_content(result.content)
                            else:
                                content_str = str(result.content)
                                # 直接附加简单字符串内容
                                panel_content.append(
                                    _format_content(content_str))
                        except Exception as e:
                            logger.warning(agentic_lang.get_message_with_format("format_tool_error", error=str(e)))
                            panel_content.append(
                                # 备用
                                _format_content(str(result.content)))

                    # 打印基本信息面板
                    yield ("thinking",_format_content("\n".join(panel_content)))
                    # 单独打印语法高亮内容（如果存在）
                    if syntax_content:
                        yield ("thinking",syntax_content)

                elif isinstance(event, CompletionEvent):                    
                    yield ("result",event.completion.result)
                    if event.completion.command:
                        yield ("result", agentic_lang.get_message_with_format("suggested_command", command=event.completion.command))
                elif isinstance(event, ErrorEvent):
                    yield ("result", agentic_lang.get_message("error_title"))
                    yield ("result", agentic_lang.get_message_with_format("error_content", message=event.message))                    

                time.sleep(0.1)  # 小延迟以获得更好的视觉流

        except Exception as e:
            logger.exception(agentic_lang.get_message("unexpected_error"))
            yield ("result",agentic_lang.get_message("fatal_error_title"))
            yield ("result",agentic_lang.get_message_with_format("fatal_error_content", error=str(e)))
            raise e
        finally:
            # 在结束时打印累计的token使用情况
            duration = time.time() - start_time            
            yield ("result","\n" + self.printer.get_message_from_key_with_format("code_generation_complete",
                duration=duration,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                input_cost=total_input_cost,
                output_cost=total_output_cost,
                speed=0.0,
                model_names=model_name,
                sampling_count=1))
            yield ("result", "\n" + agentic_lang.get_message("agent_execution_complete"))
    
    def run_in_terminal(self, request: AgentRequest):
        """
        在终端中运行代理过程，使用Rich库流式显示交互

        Args:
            request: 代理请求
        """
        start_time = time.time()
        console = Console()        
        project_name = os.path.basename(os.path.abspath(self.args.source_dir))
        console.rule(agentic_lang.get_message_with_format("agent_start", project_name=project_name))
        console.print(Panel(
            agentic_lang.get_message_with_format("user_input", input=request.user_input), 
            title=agentic_lang.get_message("user_input_title"), 
            border_style="blue"))

        # 添加token累计变量
        total_input_tokens = 0
        total_output_tokens = 0
        total_input_cost = 0.0
        total_output_cost = 0.0
        model_name = ""

        try:
            event_stream = self.agentic_run(request)
            for event in event_stream:
                if isinstance(event, TokenUsageEvent):
                    # 获取模型信息以计算价格
                    from autocoder.utils import llms as llm_utils
                    model_name = ",".join(llm_utils.get_llm_names(self.llm))
                    model_info = llm_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                    input_price = model_info.get(
                        "input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get(
                        "output_price", 0.0) if model_info else 0.0

                    # 计算成本
                    last_meta = event.usage
                    input_cost = (last_meta.input_tokens_count *
                                 input_price) / 1000000  # 转换为百万
                    output_cost = (
                        last_meta.generated_tokens_count * output_price) / 1000000

                    # 累计token使用情况
                    total_input_tokens += last_meta.input_tokens_count
                    total_output_tokens += last_meta.generated_tokens_count
                    total_input_cost += input_cost
                    total_output_cost += output_cost

                    # 记录日志
                    logger.info(agentic_lang.get_message_with_format(
                        "token_usage_log", 
                        model=model_name, 
                        input_tokens=last_meta.input_tokens_count, 
                        output_tokens=last_meta.generated_tokens_count, 
                        input_cost=input_cost, 
                        output_cost=output_cost))
                    
                elif isinstance(event, LLMThinkingEvent):
                    # 以较不显眼的样式呈现思考内容
                    console.print(f"[grey50]{event.text}[/grey50]", end="")
                elif isinstance(event, LLMOutputEvent):
                    # 打印常规LLM输出
                    console.print(event.text, end="")
                elif isinstance(event, ToolCallEvent):
                    # 跳过显示完成工具的调用
                    if hasattr(event.tool, "result") and hasattr(event.tool, "command"):
                        continue  # 不显示完成工具的调用

                    tool_name = type(event.tool).__name__
                    # 使用工具展示函数（需要自行实现）
                    display_content = get_tool_display_message(event.tool)
                    console.print(Panel(
                        display_content, 
                        title=agentic_lang.get_message_with_format("tool_operation_title", tool_name=tool_name), 
                        border_style="blue", 
                        title_align="left"))

                elif isinstance(event, ToolResultEvent):
                    # 跳过显示完成工具的结果
                    if event.tool_name == "AttemptCompletionTool":
                        continue

                    result = event.result
                    title = agentic_lang.get_message_with_format("tool_result_success_title", tool_name=event.tool_name) if result.success else agentic_lang.get_message_with_format("tool_result_failure_title", tool_name=event.tool_name)
                    border_style = "green" if result.success else "red"
                    success_status = agentic_lang.get_message("success_status") if result.success else agentic_lang.get_message("failure_status")
                    base_content = agentic_lang.get_message_with_format("status", status=success_status) + "\n"
                    base_content += agentic_lang.get_message_with_format("message", message=result.message) + "\n"

                    # 格式化内容函数
                    def _format_content(content):
                        return content[:200]

                    # 首先准备基本信息面板
                    panel_content = [base_content]
                    syntax_content = None

                    if result.content is not None:
                        content_str = ""
                        try:
                            if isinstance(result.content, (dict, list)):
                                import json
                                content_str = json.dumps(
                                    result.content, indent=2, ensure_ascii=False)
                                from rich.syntax import Syntax
                                syntax_content = Syntax(
                                    content_str, "json", theme="default", line_numbers=False)
                            elif isinstance(result.content, str) and ('\n' in result.content or result.content.strip().startswith('<')):
                                # 代码或XML/HTML的启发式判断
                                from rich.syntax import Syntax
                                lexer = "python"  # 默认猜测
                                if event.tool_name == "ReadFileTool" and isinstance(event.result.message, str):
                                    # 尝试从消息中的文件扩展名猜测lexer
                                    if ".py" in event.result.message:
                                        lexer = "python"
                                    elif ".js" in event.result.message:
                                        lexer = "javascript"
                                    elif ".ts" in event.result.message:
                                        lexer = "typescript"
                                    elif ".html" in event.result.message:
                                        lexer = "html"
                                    elif ".css" in event.result.message:
                                        lexer = "css"
                                    elif ".json" in event.result.message:
                                        lexer = "json"
                                    elif ".xml" in event.result.message:
                                        lexer = "xml"
                                    elif ".md" in event.result.message:
                                        lexer = "markdown"
                                    else:
                                        lexer = "text"  # 备用lexer
                                elif event.tool_name == "ExecuteCommandTool":
                                    lexer = "shell"
                                else:
                                    lexer = "text"

                                syntax_content = Syntax(
                                    _format_content(result.content), lexer, theme="default", line_numbers=True)
                            else:
                                content_str = str(result.content)
                                # 直接附加简单字符串内容
                                panel_content.append(
                                    _format_content(content_str))
                        except Exception as e:
                            logger.warning(agentic_lang.get_message_with_format("format_tool_error", error=str(e)))
                            panel_content.append(
                                # 备用
                                _format_content(str(result.content)))

                    # 打印基本信息面板
                    console.print(Panel("\n".join(
                        panel_content), title=title, border_style=border_style, title_align="left"))
                    # 单独打印语法高亮内容（如果存在）
                    if syntax_content:
                        console.print(syntax_content)

                elif isinstance(event, CompletionEvent):
                    # 在这里完成实际合并
                    try:
                        self.apply_changes()
                    except Exception as e:
                        logger.exception(agentic_lang.get_message_with_format("shadow_merge_error", error=str(e)))

                    from rich.markdown import Markdown
                    console.print(Panel(Markdown(event.completion.result),
                                  title=agentic_lang.get_message("completion_title"), 
                                  border_style="green", title_align="left"))
                    if event.completion.command:
                        console.print(agentic_lang.get_message_with_format("suggested_command", command=event.completion.command))
                elif isinstance(event, ErrorEvent):
                    console.print(Panel(
                        agentic_lang.get_message_with_format("error_content", message=event.message), 
                        title=agentic_lang.get_message("error_title"), 
                        border_style="red", title_align="left"))

                time.sleep(0.1)  # 小延迟以获得更好的视觉流

        except Exception as e:
            logger.exception(agentic_lang.get_message("unexpected_error"))
            console.print(Panel(
                agentic_lang.get_message_with_format("fatal_error_content", error=str(e)), 
                title=agentic_lang.get_message("fatal_error_title"), 
                border_style="red"))
            raise e
        finally:
            # 在结束时打印累计的token使用情况
            duration = time.time() - start_time            
            self.printer.print_in_terminal(
                "code_generation_complete",
                duration=duration,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                input_cost=total_input_cost,
                output_cost=total_output_cost,
                speed=0.0,
                model_names=model_name,
                sampling_count=1
            )
            console.rule(agentic_lang.get_message("agent_execution_complete"))
    
    def apply_pre_changes(self):
        # get the file name
        file_name = os.path.basename(self.args.file)
        if not self.args.skip_commit:
            try:
                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        content=self.printer.get_message_from_key("/agent/edit/apply_pre_changes")), metadata=EventMetadata(
                        action_file=self.args.file,
                        is_streaming=False,
                        path="/agent/edit/apply_pre_changes",
                        stream_out_type="/agent/edit").to_dict())
                git_utils.commit_changes(
                    self.args.source_dir, f"auto_coder_pre_{file_name}")
            except Exception as e:
                self.printer.print_in_terminal("git_init_required",
                                               source_dir=self.args.source_dir, error=str(e))
                return

    def apply_changes(self):
        """
        Apply all tracked file changes to the original project directory.
        """
        for (file_path, change) in self.get_all_file_changes().items():
            # Ensure the directory exists before writing the file
            dir_path = os.path.dirname(file_path)
            if dir_path: # Ensure dir_path is not empty (for files in root)
                 os.makedirs(dir_path, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(change.content)

        if len(self.get_all_file_changes()) > 0:
            if not self.args.skip_commit:
                try:
                    file_name = os.path.basename(self.args.file)
                    commit_result = git_utils.commit_changes(
                        self.args.source_dir,
                        f"{self.args.query}\nauto_coder_{file_name}",
                    )

                    get_event_manager(self.args.event_file).write_result(
                        EventContentCreator.create_result(
                            content=self.printer.get_message_from_key("/agent/edit/apply_changes")), metadata=EventMetadata(
                            action_file=self.args.file,
                            is_streaming=False,
                            stream_out_type="/agent/edit").to_dict())
                    action_yml_file_manager = ActionYmlFileManager(
                        self.args.source_dir)
                    action_file_name = os.path.basename(self.args.file)
                    add_updated_urls = []
                    commit_result.changed_files
                    for file in commit_result.changed_files:
                        add_updated_urls.append(
                            os.path.join(self.args.source_dir, file))

                    self.args.add_updated_urls = add_updated_urls
                    update_yaml_success = action_yml_file_manager.update_yaml_field(
                        action_file_name, "add_updated_urls", add_updated_urls)
                    if not update_yaml_success:
                        self.printer.print_in_terminal(
                            "yaml_save_error", style="red", yaml_file=action_file_name)

                    if self.args.enable_active_context:
                        active_context_manager = ActiveContextManager(
                            self.llm, self.args.source_dir)
                        task_id = active_context_manager.process_changes(
                            self.args)
                        self.printer.print_in_terminal("active_context_background_task",
                                                       style="blue",
                                                       task_id=task_id)
                    git_utils.print_commit_info(commit_result=commit_result)
                except Exception as e:
                    self.printer.print_str_in_terminal(
                        self.git_require_msg(
                            source_dir=self.args.source_dir, error=str(e)),
                        style="red"
                    )
        else:
            self.printer.print_in_terminal("no_changes_made")
            
