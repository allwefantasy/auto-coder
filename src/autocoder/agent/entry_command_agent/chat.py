
import os
import time
import json
from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText
from loguru import logger
import byzerllm

from autocoder.common.auto_coder_lang import get_message
from autocoder.common.memory_manager import save_to_memory_file
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.common.result_manager import ResultManager
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.events.event_types import EventMetadata
from autocoder.common.mcp_server import get_mcp_server
from autocoder.common.mcp_server_types import McpRequest
from autocoder.utils.llms import get_llm_names
from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    DefaultValue,
    RequestOption,
)
from autocoder.run_context import get_run_context, RunMode
from autocoder.common.action_yml_file_manager import ActionYmlFileManager


class ChatAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args
        self.console = Console()
        self.result_manager = ResultManager()

    def run(self):
        """执行 chat 命令的主要逻辑"""
        # 统一格式
        # {"command1": {"args": ["arg1", "arg2"], "kwargs": {"key1": "value1", "key2": "value2"}}}
        if isinstance(self.args.action, dict):
            commands_info = self.args.action
        else:
            commands_info = {}
            for command in self.args.action:
                commands_info[command] = {}

        memory_dir = os.path.join(self.args.source_dir, ".auto-coder", "memory")
        os.makedirs(memory_dir, exist_ok=True)
        memory_file = os.path.join(memory_dir, "chat_history.json")

        # 处理新会话
        if self.args.new_session:
            self._handle_new_session(memory_file)
            if not self.args.query or (self.args.query_prefix and self.args.query == self.args.query_prefix) or (self.args.query_suffix and self.args.query == self.args.query_suffix):
                return

        # 加载聊天历史
        chat_history = self._load_chat_history(memory_file)
        chat_history["ask_conversation"].append(
            {"role": "user", "content": self.args.query}
        )

        # 获取聊天模型
        if self.llm.get_sub_client("chat_model"):
            chat_llm = self.llm.get_sub_client("chat_model")
        else:
            chat_llm = self.llm

        # 构建对话上下文
        loaded_conversations = self._build_conversations(commands_info, chat_history)

        # 处理人工模型模式
        if get_run_context().mode != RunMode.WEB and self.args.human_as_model:
            return self._handle_human_as_model(loaded_conversations, chat_history, memory_file, commands_info)

        # 计算耗时
        start_time = time.time()
        commit_file_name = None

        # 根据命令类型处理不同的响应
        v = self._get_response(commands_info, loaded_conversations, chat_llm)
        if isinstance(v, tuple):
            v, commit_file_name = v

        # 输出响应
        model_name = ",".join(get_llm_names(chat_llm))
        assistant_response, last_meta = stream_out(
            v,
            request_id=self.args.request_id,
            console=self.console,
            model_name=model_name,
            args=self.args
        )

        self.result_manager.append(content=assistant_response, meta={
            "action": "chat",
            "input": {
                "query": self.args.query
            }
        })

        # 处理学习命令的特殊逻辑
        if "learn" in commands_info and commit_file_name:
            self._handle_learn_command(commit_file_name, assistant_response)

        # 打印统计信息
        if last_meta:
            self._print_stats(last_meta, start_time, model_name)

        # 更新聊天历史
        chat_history["ask_conversation"].append(
            {"role": "assistant", "content": assistant_response}
        )

        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False)

        # 处理后续命令
        self._handle_post_commands(commands_info, assistant_response, chat_history)

    def _handle_new_session(self, memory_file):
        """处理新会话逻辑"""
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                old_chat_history = json.load(f)
            if "conversation_history" not in old_chat_history:
                old_chat_history["conversation_history"] = []
            old_chat_history["conversation_history"].append(
                old_chat_history.get("ask_conversation", []))
            chat_history = {"ask_conversation": [],
                            "conversation_history": old_chat_history["conversation_history"]}
        else:
            chat_history = {"ask_conversation": [],
                            "conversation_history": []}
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False)

        self.result_manager.add_result(content=get_message("new_session_started"), meta={
            "action": "chat",
            "input": {
                "query": self.args.query
            }
        })
        self.console.print(
            Panel(
                get_message("new_session_started"),
                title="Session Status",
                expand=False,
                border_style="green",
            )
        )

    def _load_chat_history(self, memory_file):
        """加载聊天历史"""
        if os.path.exists(memory_file):
            with open(memory_file, "r", encoding="utf-8") as f:
                chat_history = json.load(f)
            if "conversation_history" not in chat_history:
                chat_history["conversation_history"] = []
        else:
            chat_history = {"ask_conversation": [],
                            "conversation_history": []}
        return chat_history

    def _build_conversations(self, commands_info, chat_history):
        """构建对话上下文"""
        source_count = 0
        pre_conversations = []
        context_content = self.args.context if self.args.context else ""
        
        if self.args.context:
            try:
                context = json.loads(self.args.context)
                if "file_content" in context:
                    context_content = context["file_content"]
            except:
                pass

            pre_conversations.append(
                {
                    "role": "user",
                    "content": f"请阅读下面的代码和文档：\n\n <files>\n{context_content}\n</files>",
                },
            )
            pre_conversations.append(
                {"role": "assistant", "content": "read"})
            source_count += 1

        # 构建索引和过滤文件
        if "no_context" not in commands_info:
            from autocoder.index.index import IndexManager
            from autocoder.index.entry import build_index_and_filter_files
            from autocoder.pyproject import PyProject
            from autocoder.tsproject import TSProject
            from autocoder.suffixproject import SuffixProject

            if self.args.project_type == "ts":
                pp = TSProject(args=self.args, llm=self.llm)
            elif self.args.project_type == "py":
                pp = PyProject(args=self.args, llm=self.llm)
            else:
                pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)
            pp.run()
            sources = pp.sources

            # 应用模型过滤器
            chat_llm = self.llm.get_sub_client("chat_model") or self.llm
            model_filter = ModelPathFilter.from_model_object(chat_llm, self.args)
            filtered_sources = []
            printer = Printer()
            for source in sources:
                if model_filter.is_accessible(source.module_name):
                    filtered_sources.append(source)
                else:
                    printer.print_in_terminal("index_file_filtered",
                                              style="yellow",
                                              file_path=source.module_name,
                                              model_name=",".join(get_llm_names(chat_llm)))

            s = build_index_and_filter_files(
                llm=self.llm, args=self.args, sources=filtered_sources).to_str()

            if s:
                pre_conversations.append(
                    {
                        "role": "user",
                        "content": f"请阅读下面的代码和文档：\n\n <files>\n{s}\n</files>",
                    }
                )
                pre_conversations.append(
                    {"role": "assistant", "content": "read"})
                source_count += 1

        loaded_conversations = pre_conversations + chat_history["ask_conversation"]
        return loaded_conversations

    def _handle_human_as_model(self, loaded_conversations, chat_history, memory_file, commands_info):
        """处理人工模型模式"""
        @byzerllm.prompt()
        def chat_with_human_as_model(
            source_codes, pre_conversations, last_conversation
        ):
            """                    
            {% if source_codes %}                    
            {{ source_codes }}
            {% endif %}                    

            {% if pre_conversations %}
            下面是我们之间的历史对话，假设我是A，你是B。
            <conversations>
            {% for conv in pre_conversations %}
            {{ "A" if conv.role == "user" else "B" }}: {{ conv.content }}
            {% endfor %}
            </conversations>
            {% endif %}


            参考上面的文件以及历史对话，回答用户的问题。
            用户的问题: {{ last_conversation.content }}
            """

        source_count = 0
        if self.args.context:
            source_count += 1
        if "no_context" not in commands_info:
            source_count += 1

        source_codes_conversations = loaded_conversations[0: source_count * 2]
        source_codes = ""
        for conv in source_codes_conversations:
            if conv["role"] == "user":
                source_codes += conv["content"]

        chat_content = chat_with_human_as_model.prompt(
            source_codes=source_codes,
            pre_conversations=loaded_conversations[source_count * 2: -1],
            last_conversation=loaded_conversations[-1],
        )

        with open(self.args.target_file, "w", encoding="utf-8") as f:
            f.write(chat_content)

        try:
            import pyperclip
            pyperclip.copy(chat_content)
            self.console.print(
                Panel(
                    get_message("chat_human_as_model_instructions"),
                    title="Instructions",
                    border_style="blue",
                    expand=False,
                )
            )
        except Exception:
            logger.warning(get_message("clipboard_not_supported"))
            self.console.print(
                Panel(
                    get_message("human_as_model_instructions_no_clipboard"),
                    title="Instructions",
                    border_style="blue",
                    expand=False,
                )
            )

        lines = []
        while True:
            line = prompt(FormattedText([("#00FF00", "> ")]), multiline=False)
            line_lower = line.strip().lower()
            if line_lower in ["eof", "/eof"]:
                break
            elif line_lower in ["/clear"]:
                lines = []
                print("\033[2J\033[H")  # Clear terminal screen
                continue
            elif line_lower in ["/break"]:
                raise Exception("User requested to break the operation.")
            lines.append(line)

        result = "\n".join(lines)

        self.result_manager.append(content=result,
                                   meta={"action": "chat", "input": {
                                       "query": self.args.query
                                   }})

        # Update chat history with user's response
        chat_history["ask_conversation"].append(
            {"role": "assistant", "content": result}
        )

        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False)

        if "save" in commands_info:
            save_to_memory_file(ask_conversation=chat_history["ask_conversation"],
                                query=self.args.query,
                                response=result)
            printer = Printer()
            printer.print_in_terminal("memory_save_success")
        return {}

    def _get_response(self, commands_info, loaded_conversations, chat_llm):
        """根据命令类型获取响应"""
        if "rag" in commands_info:
            from autocoder.rag.rag_entry import RAGFactory
            self.args.enable_rag_search = True
            self.args.enable_rag_context = False
            rag = RAGFactory.get_rag(llm=chat_llm, args=self.args, path="")
            response = rag.stream_chat_oai(conversations=loaded_conversations)[0]
            return (item for item in response)

        elif "mcp" in commands_info:
            mcp_server = get_mcp_server()
            pos_args = commands_info["mcp"].get("args", [])
            final_query = pos_args[0] if pos_args else self.args.query
            response = mcp_server.send_request(
                McpRequest(
                    query=final_query,
                    model=self.args.inference_model or self.args.model,
                    product_mode=self.args.product_mode
                )
            )
            return [[response.result, None]]

        elif "review" in commands_info:
            from autocoder.agent.auto_review_commit import AutoReviewCommit
            reviewer = AutoReviewCommit(llm=chat_llm, args=self.args)
            pos_args = commands_info["review"].get("args", [])
            final_query = pos_args[0] if pos_args else self.args.query
            kwargs = commands_info["review"].get("kwargs", {})
            commit_id = kwargs.get("commit", None)
            return reviewer.review_commit(query=final_query, conversations=loaded_conversations, commit_id=commit_id)

        elif "learn" in commands_info:
            from autocoder.agent.auto_learn_from_commit import AutoLearnFromCommit
            learner = AutoLearnFromCommit(llm=chat_llm, args=self.args)
            pos_args = commands_info["learn"].get("args", [])
            final_query = pos_args[0] if pos_args else self.args.query
            return learner.learn_from_commit(query=final_query, conversations=loaded_conversations)

        else:
            # 预估token数量
            dumped_conversations = json.dumps(loaded_conversations, ensure_ascii=False)
            estimated_input_tokens = count_tokens(dumped_conversations)
            printer = Printer()
            printer.print_in_terminal("estimated_chat_input_tokens", style="yellow",
                                      estimated_input_tokens=estimated_input_tokens)

            return stream_chat_with_continue(
                llm=chat_llm,
                conversations=loaded_conversations,
                llm_config={},
                args=self.args
            )

    def _handle_learn_command(self, commit_file_name, assistant_response):
        """处理学习命令的特殊逻辑"""
        if commit_file_name:
            # 使用 ActionYmlFileManager 更新 YAML 文件
            action_manager = ActionYmlFileManager(self.args.source_dir)
            if not action_manager.update_yaml_field(commit_file_name, 'how_to_reproduce', assistant_response):
                printer = Printer()
                printer.print_in_terminal("yaml_save_error", style="red", yaml_file=commit_file_name)

    def _print_stats(self, last_meta, start_time, model_name):
        """打印统计信息"""
        elapsed_time = time.time() - start_time
        printer = Printer()
        speed = last_meta.generated_tokens_count / elapsed_time

        # Get model info for pricing
        from autocoder.utils import llms as llm_utils
        model_info = llm_utils.get_model_info(model_name, self.args.product_mode) or {}
        input_price = model_info.get("input_price", 0.0) if model_info else 0.0
        output_price = model_info.get("output_price", 0.0) if model_info else 0.0

        # Calculate costs
        input_cost = (last_meta.input_tokens_count * input_price) / 1000000  # Convert to millions
        output_cost = (last_meta.generated_tokens_count * output_price) / 1000000  # Convert to millions

        printer.print_in_terminal("stream_out_stats",
                                  model_name=model_name,
                                  elapsed_time=elapsed_time,
                                  first_token_time=last_meta.first_token_time,
                                  input_tokens=last_meta.input_tokens_count,
                                  output_tokens=last_meta.generated_tokens_count,
                                  input_cost=round(input_cost, 4),
                                  output_cost=round(output_cost, 4),
                                  speed=round(speed, 2))
        
        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                model_name=model_name,
                elapsed_time=elapsed_time,
                input_tokens=last_meta.input_tokens_count,
                output_tokens=last_meta.generated_tokens_count,
                input_cost=round(input_cost, 4),
                output_cost=round(output_cost, 4),
                speed=round(speed, 2)
            )).to_dict(), metadata=EventMetadata(
                action_file=self.args.file
            ).to_dict())

    def _handle_post_commands(self, commands_info, assistant_response, chat_history):
        """处理后续命令"""
        if "copy" in commands_info:
            # copy assistant_response to clipboard
            import pyperclip
            try:
                pyperclip.copy(assistant_response)
            except:
                print("pyperclip not installed or clipboard is not supported, instruction will not be copied to clipboard.")

        if "save" in commands_info:
            tmp_dir = save_to_memory_file(ask_conversation=chat_history["ask_conversation"],
                                          query=self.args.query,
                                          response=assistant_response)
            printer = Printer()
            printer.print_in_terminal("memory_save_success", style="green", path=tmp_dir)

            if len(commands_info["save"]["args"]) > 0:
                # 保存到指定文件
                with open(commands_info["save"]["args"][0], "w", encoding="utf-8") as f:
                    f.write(assistant_response)
