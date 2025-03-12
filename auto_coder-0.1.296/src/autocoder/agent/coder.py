from autocoder.common import detect_env
from typing import Dict, List, Literal, Union, Tuple, Generator, AsyncGenerator
import pydantic
from enum import Enum
import os
import asyncio
import subprocess
import re
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit import PromptSession
import byzerllm


class TextContent(pydantic.BaseModel):
    type: Literal["text"]
    content: str
    partial: bool


class ToolUseName(str, Enum):
    execute_command = "execute_command"
    read_file = "read_file"
    write_to_file = "write_to_file"
    search_files = "search_files"
    list_files = "list_files"
    list_code_definition_names = "list_code_definition_names"
    browser_action = "browser_action"
    ask_followup_question = "ask_followup_question"
    attempt_completion = "attempt_completion"


class ToolParamName(str, Enum):
    command = "command"
    path = "path"
    content = "content"
    regex = "regex"
    file_pattern = "file_pattern"
    recursive = "recursive"
    action = "action"
    url = "url"
    coordinate = "coordinate"
    text = "text"
    question = "question"
    result = "result"


class BaseTool(pydantic.BaseModel):
    type: Literal["tool_use"]
    name: ToolUseName
    params: Dict[ToolParamName, str]
    partial: bool


class ExecuteCommandToolUse(BaseTool):
    name: Literal[ToolUseName.execute_command]
    params: Dict[Literal[ToolParamName.command], str]


class ReadFileToolUse(BaseTool):
    name: Literal[ToolUseName.read_file]
    params: Dict[Literal[ToolParamName.path], str]


class WriteToFileToolUse(BaseTool):
    name: Literal[ToolUseName.write_to_file]
    params: Dict[Union[Literal[ToolParamName.path],
                       Literal[ToolParamName.content]], str]


class SearchFilesToolUse(BaseTool):
    name: Literal[ToolUseName.search_files]
    params: Dict[Union[Literal[ToolParamName.path],
                       Literal[ToolParamName.regex], Literal[ToolParamName.file_pattern]], str]


class ListFilesToolUse(BaseTool):
    name: Literal[ToolUseName.list_files]
    params: Dict[Union[Literal[ToolParamName.path],
                       Literal[ToolParamName.recursive]], str]


class ListCodeDefinitionNamesToolUse(BaseTool):
    name: Literal[ToolUseName.list_code_definition_names]
    params: Dict[Literal[ToolParamName.path], str]


class BrowserActionToolUse(BaseTool):
    name: Literal[ToolUseName.browser_action]
    params: Dict[Union[Literal[ToolParamName.action], Literal[ToolParamName.url],
                       Literal[ToolParamName.coordinate], Literal[ToolParamName.text]], str]


class AskFollowupQuestionToolUse(BaseTool):
    name: Literal[ToolUseName.ask_followup_question]
    params: Dict[Literal[ToolParamName.question], str]


class AttemptCompletionToolUse(BaseTool):
    name: Literal[ToolUseName.attempt_completion]
    params: Dict[Union[Literal[ToolParamName.result],
                       Literal[ToolParamName.command]], str]


ToolUse = Union[
    ExecuteCommandToolUse,
    ReadFileToolUse,
    WriteToFileToolUse,
    SearchFilesToolUse,
    ListFilesToolUse,
    ListCodeDefinitionNamesToolUse,
    BrowserActionToolUse,
    AskFollowupQuestionToolUse,
    AttemptCompletionToolUse
]

AssistantMessageContent = Union[TextContent, ToolUse]


class Coder:
    def __init__(self, llm: byzerllm.ByzerLLM) -> None:
        self.llm = llm
        self.memory = []
        self.env = detect_env()
        self.current_streaming_content_index = 0
        self.assistant_message_content = []
        self.user_message_content = []
        self.user_message_content_ready = False
        self.did_reject_tool = False
        self.did_already_use_tool = False
        self.did_complete_reading_stream = False
        self.present_assistant_message_locked = False
        self.present_assistant_message_has_pending_updates = False
        self.consecutive_mistake_count = 0

    def format_response(self, content_type: str, text: str = None, images: List[str] = None):
        """Format responses similar to Cline.ts formatResponse"""
        if content_type == "tool_denied":
            return "The user denied this operation."
        elif content_type == "tool_denied_with_feedback":
            return f"The user denied this operation and provided the following feedback:\n<feedback>\n{text}\n</feedback>"
        elif content_type == "tool_error":
            return f"The tool execution failed with the following error:\n<error>\n{text}\n</error>"
        elif content_type == "no_tools_used":
            return "[ERROR] You did not use a tool in your previous response! Please retry with a tool use."
        elif content_type == "too_many_mistakes":
            return f"You seem to be having trouble proceeding. The user has provided the following feedback:\n<feedback>\n{text}\n</feedback>"

    def format_tool_result(self, text: str, images: List[str] = None):
        """Format tool execution results"""
        if images and len(images) > 0:
            return {"text": text, "images": images}
        return text

    def present_assistant_message(self):
        """Present and handle assistant messages and tool executions"""
        if self.present_assistant_message_locked:
            self.present_assistant_message_has_pending_updates = True
            return

        self.present_assistant_message_locked = True
        self.present_assistant_message_has_pending_updates = False

        if self.current_streaming_content_index >= len(self.assistant_message_content):
            if self.did_complete_reading_stream:
                self.user_message_content_ready = True
            self.present_assistant_message_locked = False
            return

        block = self.assistant_message_content[self.current_streaming_content_index]

        if block["type"] == "text":
            if not (self.did_reject_tool or self.did_already_use_tool):
                content = block.get("content", "")
                # Handle text content similar to Cline.ts
                # Remove thinking tags and format content
                if content:
                    content = re.sub(r'<thinking>\s?', '', content)
                    content = re.sub(r'\s?</thinking>', '', content)                    

        elif block["type"] == "tool_use":
            # Handle tool execution similar to Cline.ts
            # Execute appropriate tool and handle response
            if not self.did_reject_tool and not self.did_already_use_tool:
                tool_name = block.get("name")
                params = block.get("params", {})

                # Execute tool and handle response
                try:
                    result = self.execute_tool(tool_name, params)
                    self.user_message_content.append({
                        "type": "text",
                        "text": f"[{tool_name}] Result:\n{result}"
                    })
                    self.did_already_use_tool = True
                except Exception as e:
                    self.user_message_content.append({
                        "type": "text",
                        "text": self.format_response("tool_error", str(e))
                    })

        self.present_assistant_message_locked = False

        if not block.get("partial", False) or self.did_reject_tool or self.did_already_use_tool:
            if self.current_streaming_content_index == len(self.assistant_message_content) - 1:
                self.user_message_content_ready = True

            self.current_streaming_content_index += 1

            if self.current_streaming_content_index < len(self.assistant_message_content):
                self.present_assistant_message()

        if self.present_assistant_message_has_pending_updates:
            self.present_assistant_message()

    def parse_assistant_message(self, msg: str) -> List[Dict]:
        """Parse assistant message into content blocks similar to Cline.ts parseAssistantMessage"""
        content_blocks = []
        current_text_content = None
        current_text_content_start_index = 0
        current_tool_use = None
        current_tool_use_start_index = 0
        current_param_name = None
        current_param_value_start_index = 0
        accumulator = ""

        for i, char in enumerate(msg):
            accumulator += char

            # Handle param value if we're in a tool use and have a param name
            if current_tool_use is not None and current_param_name is not None:
                current_param_value = accumulator[current_param_value_start_index:]
                param_closing_tag = f"</{current_param_name}>"
                if current_param_value.endswith(param_closing_tag):
                    # End of param value
                    current_tool_use["params"][current_param_name] = current_param_value[:-len(
                        param_closing_tag)].strip()
                    current_param_name = None
                    continue

            # Handle tool use
            if current_tool_use is not None:
                current_tool_value = accumulator[current_tool_use_start_index:]
                tool_use_closing_tag = f"</{current_tool_use['name']}>"
                if current_tool_value.endswith(tool_use_closing_tag):
                    # End of tool use
                    current_tool_use["partial"] = False
                    content_blocks.append(current_tool_use)
                    current_tool_use = None
                    continue
                else:
                    # Check for param opening tags
                    for param_name in [p.value for p in ToolParamName]:
                        param_opening_tag = f"<{param_name}>"
                        if accumulator.endswith(param_opening_tag):
                            current_param_name = param_name
                            current_param_value_start_index = len(accumulator)
                            break

                    # Special case for write_to_file content param
                    if (current_tool_use["name"] == ToolUseName.write_to_file.value and
                            accumulator.endswith("</content>")):
                        tool_content = accumulator[current_tool_use_start_index:]
                        content_start_tag = "<content>"
                        content_end_tag = "</content>"
                        content_start_index = tool_content.find(
                            content_start_tag) + len(content_start_tag)
                        content_end_index = tool_content.rfind(content_end_tag)
                        if (content_start_index != -1 and content_end_index != -1
                                and content_end_index > content_start_index):
                            current_tool_use["params"]["content"] = tool_content[
                                content_start_index:content_end_index].strip()
                    continue

            # Check for start of new tool use
            did_start_tool_use = False
            for tool_name in [t.value for t in ToolUseName]:
                tool_use_opening_tag = f"<{tool_name}>"
                if accumulator.endswith(tool_use_opening_tag):
                    current_tool_use = {
                        "type": "tool_use",
                        "name": tool_name,
                        "params": {},
                        "partial": True
                    }
                    current_tool_use_start_index = len(accumulator)
                    if current_text_content is not None:
                        current_text_content["partial"] = False
                        current_text_content["content"] = current_text_content["content"][
                            :-len(tool_use_opening_tag[:-1])].strip()
                        content_blocks.append(current_text_content)
                        current_text_content = None
                    did_start_tool_use = True
                    break

            if not did_start_tool_use:
                if current_text_content is None:
                    current_text_content_start_index = i
                current_text_content = {
                    "type": "text",
                    "content": accumulator[current_text_content_start_index:].strip(),
                    "partial": True
                }

        # Handle any incomplete blocks
        if current_tool_use is not None:
            if current_param_name is not None:
                current_tool_use["params"][current_param_name] = accumulator[
                    current_param_value_start_index:].strip()
            content_blocks.append(current_tool_use)
        elif current_text_content is not None:
            content_blocks.append(current_text_content)

        return content_blocks

    def execute_tool(self, tool_name: str, params: Dict[str, str]) -> str:
        """Execute tools similar to Cline.ts tool execution"""
        try:
            if tool_name == ToolUseName.execute_command.value:
                command = params.get("command")
                if not command:
                    return self.format_response("tool_error", "Command parameter is required")
                # Execute command implementation
                return self.execute_command_tool(command)

            elif tool_name == ToolUseName.read_file.value:
                path = params.get("path")
                if not path:
                    return self.format_response("tool_error", "Path parameter is required")
                with open(os.path.join(self.env.cwd, path), 'r') as f:
                    return f.read()

            elif tool_name == ToolUseName.write_to_file.value:
                path = params.get("path")
                content = params.get("content")
                if not path or not content:
                    return self.format_response("tool_error",
                                                "Both path and content parameters are required")
                full_path = os.path.join(self.env.cwd, path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, 'w') as f:
                    f.write(content)
                return f"Content successfully written to {path}"

            elif tool_name == ToolUseName.search_files.value:
                path = params.get("path")
                regex = params.get("regex")
                if not path or not regex:
                    return self.format_response("tool_error",
                                                "Both path and regex parameters are required")
                # Implement search functionality
                return self.search_files_tool(path, regex)

            elif tool_name == ToolUseName.list_files.value:
                path = params.get("path")
                recursive = params.get("recursive", "false").lower() == "true"
                if not path:
                    return self.format_response("tool_error", "Path parameter is required")
                # Implement list files functionality
                return self.list_files_tool(path, recursive)

            elif tool_name == ToolUseName.attempt_completion.value:
                result = params.get("result")
                command = params.get("command")
                if not result:
                    return self.format_response("tool_error", "Result parameter is required")
                completion_response = self.attempt_completion_tool(
                    result, command)
                return completion_response

            else:
                return self.format_response("tool_error", f"Unknown tool: {tool_name}")

        except Exception as e:
            return self.format_response("tool_error", str(e))

    def execute_command_tool(self, command: str) -> str:
        """Execute command tool implementation with interactive support"""
        try:
            # Create rich console for pretty output
            console = Console()
            # Create prompt session for input
            session = PromptSession()

            # Create and configure the process
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=self.env.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                bufsize=1,
                universal_newlines=True
            )

            console.print(Panel(f"[bold blue]Executing command:[/] {command}"))

            # Initialize output buffer
            output = []

            while True:
                # Check for process completion
                if process.poll() is not None:
                    break

                # Read stdout
                stdout_line = process.stdout.readline()
                if stdout_line:
                    console.print(stdout_line.strip())
                    output.append(stdout_line)

                # Read stderr
                stderr_line = process.stderr.readline()
                if stderr_line:
                    console.print(f"[red]{stderr_line.strip()}[/]")
                    output.append(stderr_line)

                # Check if process is waiting for input
                if not stdout_line and not stderr_line and process.poll() is None:
                    try:
                        # Get user input
                        user_input = session.prompt("» ")
                        # Send input to process
                        process.stdin.write(f"{user_input}\n")
                        process.stdin.flush()
                        output.append(f"Input: {user_input}\n")
                    except (EOFError, KeyboardInterrupt):
                        process.terminate()
                        break

            # Get any remaining output
            remaining_stdout, remaining_stderr = process.communicate()
            if remaining_stdout:
                console.print(remaining_stdout)
                output.append(remaining_stdout)
            if remaining_stderr:
                console.print(f"[red]{remaining_stderr}[/]")
                output.append(remaining_stderr)

            if process.returncode == 0:
                return "".join(output)
            else:
                return self.format_response("tool_error", "".join(output))

        except Exception as e:
            return self.format_response("tool_error", str(e))

    def search_files_tool(self, path: str, regex: str) -> str:
        """Search files tool implementation"""
        results = []
        full_path = os.path.join(self.env.cwd, path)
        pattern = re.compile(regex)

        for root, _, files in os.walk(full_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r') as f:
                        for i, line in enumerate(f, 1):
                            if pattern.search(line):
                                rel_path = os.path.relpath(
                                    file_path, self.env.cwd)
                                results.append(
                                    f"{rel_path}:{i}: {line.strip()}")
                except Exception:
                    continue

        return "\n".join(results) if results else "No matches found"

    def list_files_tool(self, path: str, recursive: bool) -> str:
        """List files tool implementation"""
        full_path = os.path.join(self.env.cwd, path)
        results = []

        if recursive:
            for root, _, files in os.walk(full_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.env.cwd)
                    results.append(rel_path)
        else:
            try:
                results = [f for f in os.listdir(full_path)
                           if os.path.isfile(os.path.join(full_path, f))]
            except Exception as e:
                return self.format_response("tool_error", str(e))

        return "\n".join(results) if results else "No files found"

    def attempt_completion_tool(self, result: str, command: str = None) -> str:
        """Handle task completion attempts"""
        completion_msg = f"Task completed:\n{result}"
        if command:
            try:
                cmd_result = self.execute_command_tool(command)
                completion_msg += f"\nCommand execution result:\n{cmd_result}"
            except Exception as e:
                completion_msg += f"\nCommand execution failed: {str(e)}"
        return completion_msg

    async def recursively_make_cline_requests(self, user_content: List[Dict], include_file_details: bool = False) -> bool:
        """Handle recursive requests similar to Cline.ts recursivelyMakeClineRequests"""
        if self.consecutive_mistake_count >= 3:
            feedback = "You seem to be having trouble. Consider breaking down the task into smaller steps."
            user_content.append({
                "type": "text",
                "text": self.format_response("too_many_mistakes", feedback)
            })
            self.consecutive_mistake_count = 0

        # Reset streaming state
        self.current_streaming_content_index = 0
        self.assistant_message_content = []
        self.did_complete_reading_stream = False
        self.user_message_content = []
        self.user_message_content_ready = False
        self.did_reject_tool = False
        self.did_already_use_tool = False
        self.present_assistant_message_locked = False
        self.present_assistant_message_has_pending_updates = False

        try:
            # Load environment details
            loaded_content, env_details = await self.load_context(user_content, include_file_details)
            user_content = loaded_content
            user_content.append({"type": "text", "text": env_details})

            # Stream from LLM
            assistant_message = ""
            async for chunk in self.stream_llm_response(user_content):
                if isinstance(chunk, dict) and chunk.get("type") == "text":
                    assistant_message += chunk.get("text", "")
                    # Parse raw assistant message into content blocks
                    prev_length = len(self.assistant_message_content)
                    self.assistant_message_content = self.parse_assistant_message(
                        assistant_message)
                    if len(self.assistant_message_content) > prev_length:
                        self.user_message_content_ready = False
                    # Present content to user
                    self.present_assistant_message_in_terminal()

                if self.did_reject_tool:
                    assistant_message += "\n\n[Response interrupted by user feedback]"
                    break

                if self.did_already_use_tool:
                    assistant_message += "\n\n[Response interrupted by tool use result]"
                    break

            self.did_complete_reading_stream = True

            # Set remaining blocks to complete
            for block in self.assistant_message_content:
                if block.get("partial"):
                    block["partial"] = False
            self.present_assistant_message_in_terminal()

            # Check for tool usage
            did_end_loop = False
            if assistant_message:
                await self.save_conversation_history("assistant", assistant_message)
                await self._wait_for_user_message_ready()

                did_tool_use = any(block["type"] == "tool_use"
                                   for block in self.assistant_message_content)
                if not did_tool_use:
                    self.user_message_content.append({
                        "type": "text",
                        "text": self.format_response("no_tools_used")
                    })
                    self.consecutive_mistake_count += 1

                rec_did_end_loop = await self.recursively_make_cline_requests(self.user_message_content)
                did_end_loop = rec_did_end_loop
            else:
                # Error if no assistant message
                await self.save_conversation_history(
                    "assistant",
                    "Failure: No response was provided."
                )

            return did_end_loop

        except Exception as e:
            return True

    async def stream_llm_response(self, user_content: List[Dict]):
        """Stream LLM responses with error handling"""
        try:
            # first_chunk = True
            content = "\n".join([item["text"] for item in user_content])
            async for (chunk, metadata) in self.llm.async_stream_chat_oai(
                conversations=self.conversation_history +
                    [{"role": "user", "content": content}],
                    delta_mode=True
            ):
                # if first_chunk:
                #     first_chunk = False
                # Handle potential first chunk errors
                # if chunk.get("error"):
                #     yield {"type": "error", "text": str(chunk["error"])}
                #     return
                yield {"type": "text", "text": chunk}
        except Exception as e:
            yield {"type": "error", "text": str(e)}

    async def load_context(self, user_content: List[Dict], include_file_details: bool) -> Tuple[List[Dict], str]:
        """Load context and environment details similar to Cline.ts loadContext"""
        # Process user content
        processed_content = []
        for block in user_content:
            if block["type"] == "text":
                block["text"] = await self._process_mentions(block["text"])
            processed_content.append(block)

        # Get environment details
        env_details = await self._get_environment_details(include_file_details)

        return processed_content, env_details

    async def _get_environment_details(self, include_file_details: bool) -> str:
        """Build environment details string"""
        details = []        
        if include_file_details:
            details.append(
                f"\n# Current Working Directory ({self.env.cwd}) Files")
            try:
                files = self.list_files_tool(self.env.cwd, recursive=True)
                details.append(files)
            except Exception:
                details.append("(Error listing files)")

        return "\n".join(details)

    async def _wait_for_user_message_ready(self):
        """Wait for user message content to be ready"""
        while not self.user_message_content_ready:
            await asyncio.sleep(0.1)

    async def save_conversation_history(self, role: str, content: str):
        """Save message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })

    async def _process_mentions(self, text: str) -> str:
        """Process any mentions or special tags in text"""
        # Implement mention processing if needed
        return text

    async def _get_system_prompt(self) -> str:
        return self._run.prompt(custom_instructions="", support_computer_use=False)
        

    async def start_task(self, task: str, images: List[str] = None):
        """Start a new task with initial message"""
        self.conversation_history = []
        await self.save_conversation_history("system", await self._get_system_prompt())

        # Initial message
        user_content = [{
            "type": "text",
            "text": f"<task>\n{task}\n</task>"
        }]

        if images:
            for image in images:
                user_content.append({
                    "type": "image",
                    "url": image
                })

        await self.initiate_task_loop(user_content)

    async def initiate_task_loop(self, user_content: List[Dict]):
        """Control the main task execution loop"""
        next_user_content = user_content
        include_file_details = True

        while True:
            did_end_loop = await self.recursively_make_cline_requests(
                next_user_content,
                include_file_details
            )
            include_file_details = False

            if did_end_loop:
                break

            next_user_content = [{
                "type": "text",
                "text": self.format_response("no_tools_used")
            }]
            self.consecutive_mistake_count += 1

    def present_assistant_message_in_terminal(self):
        """Present and handle assistant messages with rich terminal UI"""
        if self.present_assistant_message_locked:
            self.present_assistant_message_has_pending_updates = True
            return

        self.present_assistant_message_locked = True
        self.present_assistant_message_has_pending_updates = False

        console = Console()
        session = PromptSession()

        if self.current_streaming_content_index >= len(self.assistant_message_content):
            if self.did_complete_reading_stream:
                self.user_message_content_ready = True
            self.present_assistant_message_locked = False
            return

        block = self.assistant_message_content[self.current_streaming_content_index]

        if block["type"] == "text":
            if not (self.did_reject_tool or self.did_already_use_tool):
                content = block.get("content", "")
                if content:
                    # Handle thinking tags with special formatting
                    thinking_pattern = r'<thinking>(.*?)</thinking>'
                    matches = re.findall(thinking_pattern, content, re.DOTALL)
                    if matches:
                        for thinking in matches:
                            console.print(Panel(thinking.strip(), title="[bold blue]Thinking", border_style="blue"))
                        content = re.sub(thinking_pattern, '', content)
                    
                    if content.strip():
                        console.print(content.strip(),end="")

        elif block["type"] == "tool_use":
            if not self.did_reject_tool and not self.did_already_use_tool:
                tool_name = block.get("name")
                params = block.get("params", {})

                # Show tool usage confirmation dialog
                console.print(Panel(
                    f"[bold]Tool: {tool_name}[/bold]\nParameters:\n" + 
                    "\n".join([f"- {k}: {v}" for k, v in params.items()]),
                    title="[bold yellow]Tool Usage Confirmation",
                    border_style="yellow"
                ))

                try:
                    confirm = session.prompt(
                        "Proceed with tool execution? (y/n) > ",
                        style=Style.from_dict({
                            'prompt': 'bold yellow',
                        })
                    ).lower().strip()

                    if confirm == 'y':
                        console.print("[bold green]Executing tool...[/bold green]")
                        result = self.execute_tool(tool_name, params)
                        self.user_message_content.append({
                            "type": "text",
                            "text": f"[{tool_name}] Result:\n{result}"
                        })
                        self.did_already_use_tool = True
                        console.print(Panel(str(result), title="[bold green]Tool Result", border_style="green"))
                    else:
                        self.did_reject_tool = True
                        self.user_message_content.append({
                            "type": "text",
                            "text": "The user denied this operation."
                        })
                        console.print("[bold red]Tool execution cancelled[/bold red]")

                except Exception as e:
                    error_msg = str(e)
                    self.user_message_content.append({
                        "type": "text",
                        "text": self.format_response("tool_error", error_msg)
                    })
                    console.print(Panel(error_msg, title="[bold red]Error", border_style="red"))

        self.present_assistant_message_locked = False

        if not block.get("partial", False) or self.did_reject_tool or self.did_already_use_tool:
            if self.current_streaming_content_index == len(self.assistant_message_content) - 1:
                self.user_message_content_ready = True

            self.current_streaming_content_index += 1

            if self.current_streaming_content_index < len(self.assistant_message_content):
                self.present_assistant_message_in_terminal()

        if self.present_assistant_message_has_pending_updates:
            self.present_assistant_message_in_terminal()

    def abort_task(self):
        """Handle task abortion"""
        self.did_abort = True
        # Clean up any resources
        if hasattr(self, 'diff_viewer'):
            self.diff_viewer.close()
        # Close any open file handles
        # Terminate any running processes

    async def resume_task(self):
        """Resume a previously interrupted task"""
        # Load previous conversation history
        if not self.conversation_history:
            raise Exception("No conversation history to resume")

        # Get last message before interruption
        last_message = self.conversation_history[-1]

        # Prepare resume message
        resume_content = [{
            "type": "text",
            "text": "[TASK RESUMPTION] This task was interrupted. Please reassess the current state and continue."
        }]

        await self.initiate_task_loop(resume_content)

    def create_diff(self, filename: str = "file", old_str: str = "", new_str: str = "") -> str:
        """Create a diff between two strings"""
        import difflib
        differ = difflib.Differ()
        diff = list(differ.compare(old_str.splitlines(), new_str.splitlines()))

        # Format diff output
        formatted_diff = []
        for line in diff:
            if line.startswith('+'):
                formatted_diff.append(f"+ {line[2:]}")
            elif line.startswith('-'):
                formatted_diff.append(f"- {line[2:]}")
            elif line.startswith('?'):
                continue
            else:
                formatted_diff.append(f"  {line[2:]}")

        return f"Diff for {filename}:\n" + "\n".join(formatted_diff)

    @byzerllm.prompt()
    def _run(self, custom_instructions: str, support_computer_use: bool = True) -> str:
        '''
        You are auto-coder, a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices.

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

        ## execute_command
        Description: Request to execute a CLI command on the system. Use this when you need to perform system operations or run specific commands to accomplish any step in the user's task. You must tailor your command to the user's system and provide a clear explanation of what the command does. Prefer to execute complex CLI commands over creating executable scripts, as they are more flexible and easier to run. Commands will be executed in the current working directory: {{ cwd }}
        Parameters:
        - command: (required) The CLI command to execute. This should be valid for the current operating system. Ensure the command is properly formatted and does not contain any harmful instructions.
        Usage:
        <execute_command>
        <command>Your command here</command>
        </execute_command>

        ## read_file
        Description: Request to read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file you do not know the contents of, for example to analyze code, review text files, or extract information from configuration files. Automatically extracts raw text from PDF and DOCX files. May not be suitable for other types of binary files, as it returns the raw content as a string.
        Parameters:
        - path: (required) The path of the file to read (relative to the current working directory {{ cwd }})
        Usage:
        <read_file>
        <path>File path here</path>
        </read_file>

        ## write_to_file
        Description: Request to write content to a file at the specified path. If the file exists, it will be overwritten with the provided content. If the file doesn't exist, it will be created. This tool will automatically create any directories needed to write the file.
        Parameters:
        - path: (required) The path of the file to write to (relative to the current working directory {{ cwd }})
        - content: (required) The content to write to the file. ALWAYS provide the COMPLETE intended content of the file, without any truncation or omissions. You MUST include ALL parts of the file, even if they haven't been modified.
        Usage:
        <write_to_file>
        <path>File path here</path>
        <content>
        Your file content here
        </content>
        </write_to_file>

        ## search_files
        Description: Request to perform a regex search across files in a specified directory, providing context-rich results. This tool searches for patterns or specific content across multiple files, displaying each match with encapsulating context.
        Parameters:
        - path: (required) The path of the directory to search in (relative to the current working directory {{ cwd  }}). This directory will be recursively searched.
        - regex: (required) The regular expression pattern to search for. Uses Rust regex syntax.
        - file_pattern: (optional) Glob pattern to filter files (e.g., '*.ts' for TypeScript files). If not provided, it will search all files (*).
        Usage:
        <search_files>
        <path>Directory path here</path>
        <regex>Your regex pattern here</regex>
        <file_pattern>file pattern here (optional)</file_pattern>
        </search_files>

        ## list_files
        Description: Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents. Do not use this tool to confirm the existence of files you may have created, as the user will let you know if the files were created successfully or not.
        Parameters:
        - path: (required) The path of the directory to list contents for (relative to the current working directory {{ cwd  }})
        - recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.
        Usage:
        <list_files>
        <path>Directory path here</path>
        <recursive>true or false (optional)</recursive>
        </list_files>

        ## list_code_definition_names
        Description: Request to list definition names (classes, functions, methods, etc.) used in source code files at the top level of the specified directory. This tool provides insights into the codebase structure and important constructs, encapsulating high-level concepts and relationships that are crucial for understanding the overall architecture.
        Parameters:
        - path: (required) The path of the directory (relative to the current working directory {{ cwd  }}) to list top level source code definitions for.
        Usage:
        <list_code_definition_names>
        <path>Directory path here</path>
        </list_code_definition_names>

        {%- if support_computer_use -%}
        ## browser_action
        Description: Request to interact with a Puppeteer-controlled browser. Every action, except \`close\`, will be responded to with a screenshot of the browser's current state, along with any new console logs. You may only perform one browser action per message, and wait for the user's response including a screenshot and logs to determine the next action.
        - The sequence of actions **must always start with** launching the browser at a URL, and **must always end with** closing the browser. If you need to visit a new URL that is not possible to navigate to from the current webpage, you must first close the browser, then launch again at the new URL.
        - While the browser is active, only the \`browser_action\` tool can be used. No other tools should be called during this time. You may proceed to use other tools only after closing the browser. For example if you run into an error and need to fix a file, you must close the browser, then use other tools to make the necessary changes, then re-launch the browser to verify the result.
        - The browser window has a resolution of **900x600** pixels. When performing any click actions, ensure the coordinates are within this resolution range.
        - Before clicking on any elements such as icons, links, or buttons, you must consult the provided screenshot of the page to determine the coordinates of the element. The click should be targeted at the **center of the element**, not on its edges.
        Parameters:
        - action: (required) The action to perform. The available actions are:
            * launch: Launch a new Puppeteer-controlled browser instance at the specified URL. This **must always be the first action**.
                - Use with the \`url\` parameter to provide the URL.
                - Ensure the URL is valid and includes the appropriate protocol (e.g. http://localhost:3000/page, file:///path/to/file.html, etc.)
            * click: Click at a specific x,y coordinate.
                - Use with the \`coordinate\` parameter to specify the location.
                - Always click in the center of an element (icon, button, link, etc.) based on coordinates derived from a screenshot.
            * type: Type a string of text on the keyboard. You might use this after clicking on a text field to input text.
                - Use with the \`text\` parameter to provide the string to type.
            * scroll_down: Scroll down the page by one page height.
            * scroll_up: Scroll up the page by one page height.
            * close: Close the Puppeteer-controlled browser instance. This **must always be the final browser action**.
                - Example: \`<action>close</action>\`
        - url: (optional) Use this for providing the URL for the \`launch\` action.
            * Example: <url>https://example.com</url>
        - coordinate: (optional) The X and Y coordinates for the \`click\` action. Coordinates should be within the **900x600** resolution.
            * Example: <coordinate>450,300</coordinate>
        - text: (optional) Use this for providing the text for the \`type\` action.
            * Example: <text>Hello, world!</text>
        Usage:
        <browser_action>
        <action>Action to perform (e.g., launch, click, type, scroll_down, scroll_up, close)</action>
        <url>URL to launch the browser at (optional)</url>
        <coordinate>x,y coordinates (optional)</coordinate>
        <text>Text to type (optional)</text>
        </browser_action>
        {%- endif -%}

        ## ask_followup_question
        Description: Ask the user a question to gather additional information needed to complete the task. This tool should be used when you encounter ambiguities, need clarification, or require more details to proceed effectively. It allows for interactive problem-solving by enabling direct communication with the user. Use this tool judiciously to maintain a balance between gathering necessary information and avoiding excessive back-and-forth.
        Parameters:
        - question: (required) The question to ask the user. This should be a clear, specific question that addresses the information you need.
        Usage:
        <ask_followup_question>
        <question>Your question here</question>
        </ask_followup_question>

        ## attempt_completion
        Description: After each tool use, the user will respond with the result of that tool use, i.e. if it succeeded or failed, along with any reasons for failure. Once you've received the results of tool uses and can confirm that the task is complete, use this tool to present the result of your work to the user. Optionally you may provide a CLI command to showcase the result of your work. The user may respond with feedback if they are not satisfied with the result, which you can use to make improvements and try again.
        IMPORTANT NOTE: This tool CANNOT be used until you've confirmed from the user that any previous tool uses were successful. Failure to do so will result in code corruption and system failure. Before using this tool, you must ask yourself in <thinking></thinking> tags if you've confirmed from the user that any previous tool uses were successful. If not, then DO NOT use this tool.
        Parameters:
        - result: (required) The result of the task. Formulate this result in a way that is final and does not require further input from the user. Don't end your result with questions or offers for further assistance.
        - command: (optional) A CLI command to execute to show a live demo of the result to the user. For example, use \`open index.html\` to display a created html website, or \`open localhost:3000\` to display a locally running development server. But DO NOT use commands like \`echo\` or \`cat\` that merely print text. This command should be valid for the current operating system. Ensure the command is properly formatted and does not contain any harmful instructions.
        Usage:
        <attempt_completion>
        <result>
        Your final result description here
        </result>
        <command>Command to demonstrate result (optional)</command>
        </attempt_completion>

        # Tool Use Examples

        ## Example 1: Requesting to execute a command

        <execute_command>
        <command>npm run dev</command>
        </execute_command>

        ## Example 2: Requesting to write to a file

        <write_to_file>
        <path>frontend-config.json</path>
        <content>
        {
        "apiEndpoint": "https://api.example.com",
        "theme": {
            "primaryColor": "#007bff",
            "secondaryColor": "#6c757d",
            "fontFamily": "Arial, sans-serif"
        },
        "features": {
            "darkMode": true,
            "notifications": true,
            "analytics": false
        },
        "version": "1.0.0"
        }
        </content>
        </write_to_file>

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

        It is crucial to proceed step-by-step, waiting for the user's message after each tool use before moving forward with the task. This approach allows you to:
        1. Confirm the success of each step before proceeding.
        2. Address any issues or errors that arise immediately.
        3. Adapt your approach based on new information or unexpected results.
        4. Ensure that each action builds correctly on the previous ones.

        By waiting for and carefully considering the user's response after each tool use, you can react accordingly and make informed decisions about how to proceed with the task. This iterative process helps ensure the overall success and accuracy of your work.

        ====

        CAPABILITIES

        - You have access to tools that let you execute CLI commands on the user's computer, list files, view source code definitions, regex search, {%- if support_computer_use -%}use the browser{%- endif -%}, read and write files, and ask follow-up questions. These tools help you effectively accomplish a wide range of tasks, such as writing code, making edits or improvements to existing files, understanding the current state of a project, performing system operations, and much more.
        - When the user initially gives you a task, a recursive list of all filepaths in the current working directory ('{{ cwd  }}') will be included in environment_details. This provides an overview of the project's file structure, offering key insights into the project from directory/file names (how developers conceptualize and organize their code) and file extensions (the language used). This can also guide decision-making on which files to explore further. If you need to further explore directories such as outside the current working directory, you can use the list_files tool. If you pass 'true' for the recursive parameter, it will list files recursively. Otherwise, it will list files at the top level, which is better suited for generic directories where you don't necessarily need the nested structure, like the Desktop.
        - You can use search_files to perform regex searches across files in a specified directory, outputting context-rich results that include surrounding lines. This is particularly useful for understanding code patterns, finding specific implementations, or identifying areas that need refactoring.
        - You can use the list_code_definition_names tool to get an overview of source code definitions for all files at the top level of a specified directory. This can be particularly useful when you need to understand the broader context and relationships between certain parts of the code. You may need to call this tool multiple times to understand various parts of the codebase related to the task.
            - For example, when asked to make edits or improvements you might analyze the file structure in the initial environment_details to get an overview of the project, then use list_code_definition_names to get further insight using source code definitions for files located in relevant directories, then read_file to examine the contents of relevant files, analyze the code and suggest improvements or make necessary edits, then use the write_to_file tool to implement changes. If you refactored code that could affect other parts of the codebase, you could use search_files to ensure you update other files as needed.
        - You can use the execute_command tool to run commands on the user's computer whenever you feel it can help accomplish the user's task. When you need to execute a CLI command, you must provide a clear explanation of what the command does. Prefer to execute complex CLI commands over creating executable scripts, since they are more flexible and easier to run. Interactive and long-running commands are allowed, since the commands are run in the user's VSCode terminal. The user may keep commands running in the background and you will be kept updated on their status along the way. Each command you execute is run in a new terminal instance.{%- if support_computer_use -%}
        \n- You can use the browser_action tool to interact with websites (including html files and locally running development servers) through a Puppeteer-controlled browser when you feel it is necessary in accomplishing the user's task. This tool is particularly useful for web development tasks as it allows you to launch a browser, navigate to pages, interact with elements through clicks and keyboard input, and capture the results through screenshots and console logs. This tool may be useful at key stages of web development tasks-such as after implementing new features, making substantial changes, when troubleshooting issues, or to verify the result of your work. You can analyze the provided screenshots to ensure correct rendering or identify errors, and review console logs for runtime issues.\n	- For example, if asked to add a component to a react website, you might create the necessary files, use execute_command to run the site locally, then use browser_action to launch the browser, navigate to the local server, and verify the component renders & functions correctly before closing the browser.
        {%- endif -%}

        ====

        RULES

        - Your current working directory is: {{ cwd  }}
        - You cannot \`cd\` into a different directory to complete a task. You are stuck operating from '{{ cwd  }}', so be sure to pass in the correct 'path' parameter when using tools that require a path.
        - Do not use the ~ character or $HOME to refer to the home directory.
        - Before using the execute_command tool, you must first think about the SYSTEM INFORMATION context provided to understand the user's environment and tailor your commands to ensure they are compatible with their system. You must also consider if the command you need to run should be executed in a specific directory outside of the current working directory '{{ cwd  }}', and if so prepend with \`cd\`'ing into that directory && then executing the command (as one command since you are stuck operating from '{{ cwd  }}'). For example, if you needed to run \`npm install\` in a project outside of '{{ cwd  }}', you would need to prepend with a \`cd\` i.e. pseudocode for this would be \`cd (path to project) && (command, in this case npm install)\`.
        - When using the search_files tool, craft your regex patterns carefully to balance specificity and flexibility. Based on the user's task you may use it to find code patterns, TODO comments, function definitions, or any text-based information across the project. The results include context, so analyze the surrounding code to better understand the matches. Leverage the search_files tool in combination with other tools for more comprehensive analysis. For example, use it to find specific code patterns, then use read_file to examine the full context of interesting matches before using write_to_file to make informed changes.
        - When creating a new project (such as an app, website, or any software project), organize all new files within a dedicated project directory unless the user specifies otherwise. Use appropriate file paths when writing files, as the write_to_file tool will automatically create any necessary directories. Structure the project logically, adhering to best practices for the specific type of project being created. Unless otherwise specified, new projects should be easily run without additional setup, for example most projects can be built in HTML, CSS, and JavaScript - which you can open in a browser.
        - Be sure to consider the type of project (e.g. Python, JavaScript, web application) when determining the appropriate structure and files to include. Also consider what files may be most relevant to accomplishing the task, for example looking at a project's manifest file would help you understand the project's dependencies, which you could incorporate into any code you write.
        - When making changes to code, always consider the context in which the code is being used. Ensure that your changes are compatible with the existing codebase and that they follow the project's coding standards and best practices.
        - When you want to modify a file, use the write_to_file tool directly with the desired content. You do not need to display the content before using the tool.
        - Do not ask for more information than necessary. Use the tools provided to accomplish the user's request efficiently and effectively. When you've completed your task, you must use the attempt_completion tool to present the result to the user. The user may provide feedback, which you can use to make improvements and try again.
        - You are only allowed to ask the user questions using the ask_followup_question tool. Use this tool only when you need additional details to complete a task, and be sure to use a clear and concise question that will help you move forward with the task. However if you can use the available tools to avoid having to ask the user questions, you should do so. For example, if the user mentions a file that may be in an outside directory like the Desktop, you should use the list_files tool to list the files in the Desktop and check if the file they are talking about is there, rather than asking the user to provide the file path themselves.
        - When executing commands, if you don't see the expected output, assume the terminal executed the command successfully and proceed with the task. The user's terminal may be unable to stream the output back properly. If you absolutely need to see the actual terminal output, use the ask_followup_question tool to request the user to copy and paste it back to you.
        - The user may provide a file's contents directly in their message, in which case you shouldn't use the read_file tool to get the file contents again since you already have it.
        - Your goal is to try to accomplish the user's task, NOT engage in a back and forth conversation.{%- if support_computer_use -%}
        \n- The user may ask generic non-development tasks, such as "what\'s the latest news" or "look up the weather in San Diego", in which case you might use the browser_action tool to complete the task if it makes sense to do so, rather than trying to create a website or using curl to answer the question.
        {%- endif -%}
        - NEVER end attempt_completion result with a question or request to engage in further conversation! Formulate the end of your result in a way that is final and does not require further input from the user.
        - You are STRICTLY FORBIDDEN from starting your messages with "Great", "Certainly", "Okay", "Sure". You should NOT be conversational in your responses, but rather direct and to the point. For example you should NOT say "Great, I've updated the CSS" but instead something like "I've updated the CSS". It is important you be clear and technical in your messages.
        - When presented with images, utilize your vision capabilities to thoroughly examine them and extract meaningful information. Incorporate these insights into your thought process as you accomplish the user's task.
        - At the end of each user message, you will automatically receive environment_details. This information is not written by the user themselves, but is auto-generated to provide potentially relevant context about the project structure and environment. While this information can be valuable for understanding the project context, do not treat it as a direct part of the user's request or response. Use it to inform your actions and decisions, but don't assume the user is explicitly asking about or referring to this information unless they clearly do so in their message. When using environment_details, explain your actions clearly to ensure the user understands, as they may not be aware of these details.
        - Before executing commands, check the "Actively Running Terminals" section in environment_details. If present, consider how these active processes might impact your task. For example, if a local development server is already running, you wouldn't need to start it again. If no active terminals are listed, proceed with command execution as normal.
        - When using the write_to_file tool, ALWAYS provide the COMPLETE file content in your response. This is NON-NEGOTIABLE. Partial updates or placeholders like '// rest of code unchanged' are STRICTLY FORBIDDEN. You MUST include ALL parts of the file, even if they haven't been modified. Failure to do so will result in incomplete or broken code, severely impacting the user's project.
        - It is critical you wait for the user's response after each tool use, in order to confirm the success of the tool use. For example, if asked to make a todo app, you would create a file, wait for the user's response it was created successfully, then create another file if needed, wait for the user's response it was created successfully, etc.{%- if support_computer_use -%}  Then if you want to test your work, you might use browser_action to launch the site, wait for the user's response confirming the site was launched along with a screenshot, then perhaps e.g., click a button to test functionality if needed, wait for the user's response confirming the button was clicked along with a screenshot of the new state, before finally closing the browser.{%- endif -%}

        ====

        SYSTEM INFORMATION

        Operating System: {{ osName }}
        Default Shell: {{ defaultShell }}
        Home Directory: {{ homedir }}
        Current Working Directory: {{ cwd  }}

        ====

        OBJECTIVE

        You accomplish a given task iteratively, breaking it down into clear steps and working through them methodically.

        1. Analyze the user's task and set clear, achievable goals to accomplish it. Prioritize these goals in a logical order.
        2. Work through these goals sequentially, utilizing available tools one at a time as necessary. Each goal should correspond to a distinct step in your problem-solving process. You will be informed on the work completed and what's remaining as you go.
        3. Remember, you have extensive capabilities with access to a wide range of tools that can be used in powerful and clever ways as necessary to accomplish each goal. Before calling a tool, do some analysis within <thinking></thinking> tags. First, analyze the file structure provided in environment_details to gain context and insights for proceeding effectively. Then, think about which of the provided tools is the most relevant tool to accomplish the user's task. Next, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool use. BUT, if one of the values for a required parameter is missing, DO NOT invoke the tool (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters using the ask_followup_question tool. DO NOT ask for more information on optional parameters if it is not provided.
        4. Once you've completed the user's task, you must use the attempt_completion tool to present the result of the task to the user. You may also provide a CLI command to showcase the result of your task; this can be particularly useful for web development tasks, where you can run e.g. \`open index.html\` to show the website you've built.
        5. The user may provide feedback, which you can use to make improvements and try again. But DO NOT continue in pointless back and forth conversations, i.e. don't end your responses with questions or offers for further assistance.`

        {%- if custom_instructions -%}
        ====

        USER'S CUSTOM INSTRUCTIONS

        The following additional instructions are provided by the user, and should be followed to the best of your ability without interfering with the TOOL USE guidelines.

        {{ custom_instructions }}
        {%- endif -%}
        '''
        env = detect_env()
        res = {
            "cwd": env.cwd,
            "customInstructions": custom_instructions,
            "osName": env.os_name,
            "defaultShell": env.default_shell,
            "homedir": env.home_dir
        }
        return res

    def parse_assistant_message(self, msg: str):
        content_blocks = []
        current_text_content = None
        current_text_content_start_index = 0
        current_tool_use = None
        current_tool_use_start_index = 0
        current_param_name = None
        current_param_value_start_index = 0
        accumulator = ""

        for i, char in enumerate(msg):
            accumulator += char

            # there should not be a param without a tool use
            if current_tool_use is not None and current_param_name is not None:
                current_param_value = accumulator[current_param_value_start_index:]
                param_closing_tag = f"</{current_param_name}>"
                if current_param_value.endswith(param_closing_tag):
                    # end of param value
                    current_tool_use["params"][current_param_name] = current_param_value[:-len(
                        param_closing_tag)].strip()
                    current_param_name = None
                    continue
                else:
                    # partial param value is accumulating
                    continue

            # no currentParamName
            if current_tool_use is not None:
                current_tool_value = accumulator[current_tool_use_start_index:]
                tool_use_closing_tag = f"</{current_tool_use['name']}>"
                if current_tool_value.endswith(tool_use_closing_tag):
                    # end of a tool use
                    current_tool_use["partial"] = False
                    content_blocks.append(current_tool_use)
                    current_tool_use = None
                    continue
                else:
                    # Check for possible param opening tags
                    for param_name in ["command", "path", "content", "regex", "file_pattern",
                                       "recursive", "action", "url", "coordinate", "text",
                                       "question", "result"]:
                        param_opening_tag = f"<{param_name}>"
                        if accumulator.endswith(param_opening_tag):
                            # start of a new parameter
                            current_param_name = param_name
                            current_param_value_start_index = len(accumulator)
                            break

                    # Special case for write_to_file content param
                    if current_tool_use["name"] == "write_to_file" and accumulator.endswith("</content>"):
                        tool_content = accumulator[current_tool_use_start_index:]
                        content_start_tag = "<content>"
                        content_end_tag = "</content>"
                        content_start_index = tool_content.find(
                            content_start_tag) + len(content_start_tag)
                        content_end_index = tool_content.rfind(content_end_tag)
                        if content_start_index != -1 and content_end_index != -1 and content_end_index > content_start_index:
                            current_tool_use["params"]["content"] = tool_content[content_start_index:content_end_index].strip(
                            )

                    continue

            # no currentToolUse
            did_start_tool_use = False
            for tool_name in ["execute_command", "read_file", "write_to_file", "search_files",
                              "list_files", "list_code_definition_names", "browser_action",
                              "ask_followup_question", "attempt_completion"]:
                tool_use_opening_tag = f"<{tool_name}>"
                if accumulator.endswith(tool_use_opening_tag):
                    # start of a new tool use
                    current_tool_use = {
                        "type": "tool_use",
                        "name": tool_name,
                        "params": {},
                        "partial": True
                    }
                    current_tool_use_start_index = len(accumulator)
                    # this also indicates the end of the current text content
                    if current_text_content is not None:
                        current_text_content["partial"] = False
                        # remove the partially accumulated tool use tag from the end of text
                        current_text_content["content"] = current_text_content["content"][:-len(
                            tool_use_opening_tag[:-1])].strip()
                        content_blocks.append(current_text_content)
                        current_text_content = None

                    did_start_tool_use = True
                    break

            if not did_start_tool_use:
                # no tool use, so it must be text either at the beginning or between tools
                if current_text_content is None:
                    current_text_content_start_index = i
                current_text_content = {
                    "type": "text",
                    "content": accumulator[current_text_content_start_index:].strip(),
                    "partial": True
                }

        # Handle incomplete blocks at the end of message
        if current_tool_use is not None:
            # stream did not complete tool call
            if current_param_name is not None:
                # tool call has a parameter that was not completed
                current_tool_use["params"][current_param_name] = accumulator[current_param_value_start_index:].strip(
                )
            content_blocks.append(current_tool_use)
        elif current_text_content is not None:
            # stream did not complete text content
            content_blocks.append(current_text_content)

        return content_blocks
