from enum import Enum
import json
import os
import time
from pydantic import BaseModel, Field, SkipValidation
import byzerllm
from typing import List, Dict, Any, Union, Callable, Optional
from autocoder.common.printer import Printer
from autocoder.common.result_manager import ResultManager
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from byzerllm.utils.str2model import to_model
from autocoder.common import git_utils
from autocoder.common import detect_env
from autocoder.common import shells
from loguru import logger
from autocoder.utils import llms as llms_utils
from autocoder.rag.token_counter import count_tokens
from autocoder.common.stream_out_type import AutoCommandStreamOutType
from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
from autocoder.common.global_cancel import global_cancel

class AgenticFilterRequest(BaseModel):
    user_input: str

class FileOperation(BaseModel):
    path: str
    operation: str  # e.g., "MODIFY", "REFERENCE", "ADD", "REMOVE"

class AgenticFilterResponse(BaseModel):
    files: List[FileOperation]  # 文件列表，包含path和operation字段
    reasoning: str  # 决策过程说明

class AgenticFilterConfig(BaseModel):
    get_project_structure: SkipValidation[Callable]
    get_project_map: SkipValidation[Callable]
    read_files: SkipValidation[Callable]
    find_files_by_name: SkipValidation[Callable]
    find_files_by_content: SkipValidation[Callable]
    run_python: SkipValidation[Callable]
    execute_shell_command: SkipValidation[Callable]
    response_user: SkipValidation[Callable]

class AgenticFilter:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.printer = Printer()
        self.tools = AutoCommandTools(args=args, llm=self.llm)
        self.result_manager = ResultManager(source_dir=args.source_dir)
        self.max_iterations = args.auto_command_max_iterations # Use existing args for max iterations

    @byzerllm.prompt()
    def _analyze_prompt(self, request: AgenticFilterRequest, conversation_history: List[Dict[str, str]]) -> str:
        """
        ## 目标
        根据用户需求识别需要操作的文件，最终返回JSON格式的文件列表。你需要通过组合使用可用工具来达成这个目标。

        ## 可用工具
        1.  **get_project_structure**: 获取项目根目录下的目录结构树。
        2.  **get_project_map(file_paths: Optional[str] = None)**: 获取项目中指定文件（或所有已索引文件）的符号信息、用途、tokens数等。`file_paths` 是逗号分隔的路径字符串。
        3.  **find_files_by_name(keyword: str)**: 根据文件名中的关键字搜索文件。
        4.  **find_files_by_content(keyword: str)**: 根据文件内容中的关键字搜索文件。
        5.  **read_files(paths: str, line_ranges: Optional[str] = None)**: 读取指定文件的内容，支持指定行范围。`paths` 是逗号分隔的文件路径，`line_ranges` 是可选的行范围字符串。
        6.  **run_python(code: str)**: 执行Python脚本。
        7.  **execute_shell_command(command: str)**: 执行Shell命令（禁止使用rm）。
        8.  **response_user(response: str)**: 当你认为已经收集到足够信息并能确定最终文件列表时，调用此工具返回最终结果。

        ## 操作流程建议
        1.  **理解需求**: 分析用户输入 `{{ user_input }}`。
        2.  **探索项目**:
            *   使用 `get_project_structure` 了解项目结构。
            *   根据初步理解，使用 `find_files_by_name` 或 `find_files_by_content` 定位可能相关的文件。
            *   使用 `get_project_map` 获取候选文件的详细信息（如符号）。
        3.  **深入分析**:
            *   使用 `read_files` 读取关键文件的内容进行确认。如果文件过大，使用 `line_ranges` 参数分段读取。
            *   如有必要，使用 `run_python` 或 `execute_shell_command` 执行代码或命令进行更复杂的分析。
        4.  **迭代决策**: 根据工具的返回结果，你可能需要多次调用不同的工具来逐步缩小范围或获取更多信息。
        5.  **最终响应**: 当你确定了所有需要参考和修改的文件后，**必须**调用 `response_user` 工具，并提供符合下面格式的JSON字符串作为其 `response` 参数。

        ## 对话历史
        <conversation_history>
        {% for msg in conversation_history %}
        **{{ msg.role }}**: {{ msg.content }}
        {% endfor %}
        </conversation_history>

        ## 当前项目根目录
        {{ project_root }}

        ## Token 安全区
        对话和文件内容的总Token数不应超过 {{ conversation_safe_zone_tokens }}。请谨慎读取大文件。

        ## 最终输出要求 (通过 response_user 工具返回)
        返回的JSON字符串必须严格符合以下格式:
        ```json
        {
            "files": [
                {"path": "/path/to/file1.py", "operation": "MODIFY"},
                {"path": "/path/to/file2.md", "operation": "REFERENCE"},
                {"path": "/path/to/new_file.txt", "operation": "ADD"},
                {"path": "/path/to/old_file.log", "operation": "REMOVE"}
            ],
            "reasoning": "详细说明你是如何通过分析和使用工具得出这个文件列表的。"
        }
        ```
        其中 `operation` 可以是 "MODIFY", "REFERENCE", "ADD", "REMOVE" 等。

        ## 当前任务
        现在，请根据用户需求 `{{ user_input }}` 和以上信息，决定调用哪个工具以及相应的参数。返回一个JSON对象，包含 `tool_name` 和 `parameters` 字段。例如:
        ```json
        {"tool_name": "get_project_structure", "parameters": {}}
        ```
        或者
        ```json
        {"tool_name": "read_files", "parameters": {"paths": "src/main.py", "line_ranges": "1-50"}}
        ```
        如果你认为已经完成任务，请返回调用 `response_user` 的JSON。
        """
        return {
            "user_input": request.user_input,
            "project_root": os.path.abspath(self.args.source_dir),
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
            "conversation_history": conversation_history,
        }

    @byzerllm.prompt()
    def _tool_result_prompt(self, tool_name: str, tool_result: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        ## 任务
        你正在分析用户需求以确定需要操作的文件列表。上一步你调用了工具 `{{ tool_name }}`，结果如下：

        <tool_result>
        {{ tool_result }}
        </tool_result>

        ## 对话历史
        <conversation_history>
        {% for msg in conversation_history %}
        **{{ msg.role }}**: {{ msg.content }}
        {% endfor %}
        </conversation_history>

        ## 可用工具
        1.  get_project_structure
        2.  get_project_map(file_paths: Optional[str] = None)
        3.  find_files_by_name(keyword: str)
        4.  find_files_by_content(keyword: str)
        5.  read_files(paths: str, line_ranges: Optional[str] = None)
        6.  run_python(code: str)
        7.  execute_shell_command(command: str)
        8.  response_user(response: str)

        ## 当前任务
        请根据上一步工具的执行结果和对话历史，决定下一步调用哪个工具（或者调用 `response_user` 返回最终结果）。返回包含 `tool_name` 和 `parameters` 的JSON对象。

        **重要提示**: 如果你认为已经收集到足够信息来确定最终的文件列表，请务必调用 `response_user` 并提供符合要求的JSON字符串作为 `response` 参数。最多允许 {{ max_iterations }} 次工具调用。
        """
        return {
            "tool_name": tool_name,
            "tool_result": tool_result,
            "conversation_history": conversation_history,
            "max_iterations": self.max_iterations,
        }

    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """执行指定工具并记录结果"""
        tool_map = {
            "get_project_structure": self.tools.get_project_structure,
            "get_project_map": self.tools.get_project_map,
            "read_files": self.tools.read_files,
            "find_files_by_name": self.tools.find_files_by_name,
            "find_files_by_content": self.tools.find_files_by_content,
            "run_python": self.tools.run_python_code,
            "execute_shell_command": self.tools.run_shell_code, # Use run_shell_code for safety check
            "response_user": self.tools.response_user # response_user is handled specially later
        }

        if tool_name not in tool_map:
            result = f"Error: Invalid tool name '{tool_name}'."
            self.result_manager.append(content=result, meta={
                "action": "error",
                "tool_name": tool_name,
                "params": parameters,
            })
            return result

        try:
            # Special handling for response_user
            if tool_name == "response_user":
                 # We just need the response content, the tool itself doesn't return anything meaningful here
                 # The actual response sending happens outside the loop
                 response_content = parameters.get("response", "")
                 self.result_manager.append(content=response_content, meta={
                     "action": tool_name,
                     "params": parameters,
                     "is_final": True # Mark this as the final response
                 })
                 return response_content # Return the intended response for history

            # Execute other tools
            result = tool_map[tool_name](**parameters)
            # Ensure result is a string
            if not isinstance(result, str):
                result = json.dumps(result) if result is not None else ""

            self.result_manager.append(content=result, meta={
                "action": tool_name,
                "params": parameters,
            })
            # Limit result size to avoid excessive token usage in history
            max_result_length = 2000 # Limit result length in history
            if len(result) > max_result_length:
                result = result[:max_result_length] + "\n... (result truncated)"
            return result
        except Exception as e:
            error_message = f"Error executing tool {tool_name} with params {parameters}: {str(e)}"
            logger.error(error_message)
            self.result_manager.append(content=error_message, meta={
                "action": "error",
                "tool_name": tool_name,
                "params": parameters,
            })
            return error_message


    def analyze(self, request: AgenticFilterRequest) -> Optional[AgenticFilterResponse]:
        conversations = []
        current_iteration = 0

        # Initial prompt
        initial_prompt_str = self._analyze_prompt(request, conversations)
        conversations.append({"role": "user", "content": initial_prompt_str})

        while current_iteration < self.max_iterations:
            global_cancel.check_and_raise()
            current_iteration += 1
            logger.info(f"AgenticFilter Iteration: {current_iteration}/{self.max_iterations}")

            # Get LLM suggestion for the next tool
            model_name = ",".join(llms_utils.get_llm_names(self.llm))
            title = self.printer.get_message_from_key_with_format("agentic_filter_analyzing", current_iteration=current_iteration, max_iterations=self.max_iterations)
            final_title = self.printer.get_message_from_key("agentic_filter_analyzed")

            def extract_tool_suggestion(content: str) -> str:
                try:
                    tool_call = json.loads(content)
                    tool_name = tool_call.get("tool_name")
                    params = tool_call.get("parameters", {})
                    if params:
                         params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                         return f"Tool: {tool_name}({params_str})"
                    else:
                         return f"Tool: {tool_name}()"
                except Exception:
                    return content # Return raw content if not valid JSON

            llm_output, _ = stream_out(
                self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
                model_name=model_name,
                title=title,
                final_title=final_title,
                display_func=extract_tool_suggestion,
                args=self.args,
                extra_meta={
                    "stream_out_type": AutoCommandStreamOutType.COMMAND_SUGGESTION.value
                }
            )
            conversations.append({"role": "assistant", "content": llm_output})

            # Parse the suggested tool call
            try:
                tool_call = json.loads(llm_output)
                tool_name = tool_call.get("tool_name")
                parameters = tool_call.get("parameters", {})

                if not tool_name:
                    logger.warning("LLM did not suggest a tool name. Ending analysis.")
                    self.printer.print_in_terminal("agentic_filter_no_tool", style="yellow")
                    return None

            except json.JSONDecodeError:
                logger.warning(f"LLM output is not valid JSON: {llm_output}. Ending analysis.")
                self.printer.print_in_terminal("agentic_filter_invalid_json", style="yellow")
                return None

            # Execute the tool
            self.printer.print_in_terminal(f"Executing tool: {tool_name} with params: {parameters}", style="blue")
            tool_result = self.execute_tool(tool_name, parameters)
            self.printer.print_in_terminal(f"Tool Result (truncated): {tool_result[:200]}...", style="dim")


            # Check if the final response tool was called
            last_result_item = self.result_manager.get_last()
            if last_result_item and last_result_item.meta.get("is_final"):
                try:
                    # The content of the last result IS the JSON response string
                    final_response_json = last_result_item.content
                    final_response = AgenticFilterResponse.model_validate_json(final_response_json)
                    self.printer.print_in_terminal("agentic_filter_completed", style="green")
                    # The response_user tool already printed the result via ResultManager
                    # self.tools.response_user(final_response.model_dump_json(indent=2)) # Ensure final output
                    return final_response
                except Exception as e:
                    logger.error(f"Failed to parse final response from response_user tool: {e}")
                    self.printer.print_in_terminal("agentic_filter_final_parse_error", style="red", error=str(e))
                    return None

            # Prepare for the next iteration
            tool_result_prompt_str = self._tool_result_prompt(tool_name, tool_result, conversations)
            conversations.append({"role": "user", "content": tool_result_prompt_str})

            # Prune conversation if necessary (optional, depends on token limits)
            # total_tokens = count_tokens(json.dumps(conversations))
            # if total_tokens > self.args.conversation_prune_safe_zone_tokens:
            #     # Implement pruning logic here if needed
            #     logger.warning("Conversation pruning not yet implemented for AgenticFilter")
            #     pass


        logger.warning(f"AgenticFilter reached max iterations ({self.max_iterations}) without calling response_user.")
        self.printer.print_in_terminal("agentic_filter_max_iterations", style="yellow", max_iterations=self.max_iterations)
        return None
