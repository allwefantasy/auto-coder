from autocoder.common.v2.agent.agentic_edit_conversation import AgenticConversation
from enum import Enum
from enum import Enum
import json
import os
import time
from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any, Union, Callable, Optional, Tuple
from autocoder.common.printer import Printer
from rich.console import Console
from rich.panel import Panel
from pydantic import SkipValidation
from byzerllm.utils.types import SingleOutputMeta

# Removed ResultManager, stream_out, git_utils, AutoCommandTools, count_tokens, global_cancel, ActionYmlFileManager, get_event_manager, EventContentCreator, get_run_context, AgenticFilterStreamOutType
from autocoder.common import AutoCoderArgs, git_utils, SourceCodeList, SourceCode
from autocoder.common.global_cancel import global_cancel
from autocoder.common import detect_env
from autocoder.common import shells
from loguru import logger
from autocoder.utils import llms as llms_utils
from autocoder.common.auto_configure import config_readme
from autocoder.utils.auto_project_type import ProjectTypeAnalyzer
from rich.text import Text
from autocoder.common.mcp_server import get_mcp_server, McpServerInfoRequest
from autocoder.common import SourceCodeList
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue  # Added import
import re
import xml.sax.saxutils
import time  # Added for sleep
from typing import Iterator, Union, Type, Generator
from xml.etree import ElementTree as ET
from rich.console import Console  # Added
from rich.panel import Panel  # Added
from rich.syntax import Syntax  # Added
from rich.markdown import Markdown  # Added
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events.event_types import Event, EventType, EventMetadata
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.events import event_content as EventContentCreator
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.linters.shadow_linter import ShadowLinter
from autocoder.compilers.shadow_compiler import ShadowCompiler
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common.auto_coder_lang import get_message
# Import the new display function
from autocoder.common.v2.agent.agentic_tool_display import get_tool_display_message
from autocoder.common.v2.agent.agentic_edit_types import FileChangeEntry
from autocoder.common.v2.agent.agentic_edit_tools import (  # Import specific resolvers
    BaseToolResolver,
    ExecuteCommandToolResolver, ReadFileToolResolver, WriteToFileToolResolver,
    ReplaceInFileToolResolver, SearchFilesToolResolver, ListFilesToolResolver,
    ListCodeDefinitionNamesToolResolver, AskFollowupQuestionToolResolver,
    AttemptCompletionToolResolver, PlanModeRespondToolResolver, UseMcpToolResolver,
    ListPackageInfoToolResolver
)

from autocoder.common.v2.agent.agentic_edit_types import (AgenticEditRequest, ToolResult,
                                                          MemoryConfig, CommandConfig, BaseTool,
                                                          ExecuteCommandTool, ReadFileTool,
                                                          WriteToFileTool,
                                                          ReplaceInFileTool,
                                                          SearchFilesTool,
                                                          ListFilesTool,
                                                          ListCodeDefinitionNamesTool, AskFollowupQuestionTool,
                                                          AttemptCompletionTool, PlanModeRespondTool, UseMcpTool,
                                                          ListPackageInfoTool,
                                                          TOOL_MODEL_MAP,
                                                          # Event Types
                                                          LLMOutputEvent, LLMThinkingEvent, ToolCallEvent,
                                                          ToolResultEvent, CompletionEvent, PlanModeRespondEvent, ErrorEvent, TokenUsageEvent,
                                                          # Import specific tool types for display mapping
                                                          ReadFileTool, WriteToFileTool, ReplaceInFileTool, ExecuteCommandTool,
                                                          ListFilesTool, SearchFilesTool, ListCodeDefinitionNamesTool,
                                                          AskFollowupQuestionTool, UseMcpTool, AttemptCompletionTool
                                                          )


# Map Pydantic Tool Models to their Resolver Classes
TOOL_RESOLVER_MAP: Dict[Type[BaseTool], Type[BaseToolResolver]] = {
    ExecuteCommandTool: ExecuteCommandToolResolver,
    ReadFileTool: ReadFileToolResolver,
    WriteToFileTool: WriteToFileToolResolver,
    ReplaceInFileTool: ReplaceInFileToolResolver,
    SearchFilesTool: SearchFilesToolResolver,
    ListFilesTool: ListFilesToolResolver,
    ListCodeDefinitionNamesTool: ListCodeDefinitionNamesToolResolver,
    ListPackageInfoTool: ListPackageInfoToolResolver,
    AskFollowupQuestionTool: AskFollowupQuestionToolResolver,
    AttemptCompletionTool: AttemptCompletionToolResolver,  # Will stop the loop anyway
    PlanModeRespondTool: PlanModeRespondToolResolver,
    UseMcpTool: UseMcpToolResolver,
}


# --- Tool Display Customization is now handled by agentic_tool_display.py ---


class AgenticEdit:
    def __init__(
        self,
        llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
        conversation_history: List[Dict[str, Any]],
        files: SourceCodeList,
        args: AutoCoderArgs,
        memory_config: MemoryConfig,
        command_config: Optional[CommandConfig] = None,
        conversation_name: str = "current"
    ):
        self.llm = llm
        self.args = args
        self.printer = Printer()
        # Removed self.tools and self.result_manager
        self.files = files
        # Removed self.max_iterations
        # Note: This might need updating based on the new flow
        self.conversation_history = conversation_history
        self.memory_config = memory_config
        self.command_config = command_config  # Note: command_config might be unused now
        self.project_type_analyzer = ProjectTypeAnalyzer(
            args=args, llm=self.llm)

        self.conversation_manager = AgenticConversation(
            args, self.conversation_history, conversation_name=conversation_name)
        # 当前不开启历史记录，所以清空
        self.conversation_manager.clear_history()

        self.shadow_manager = ShadowManager(
            args.source_dir, args.event_file, args.ignore_clean_shadows)
        self.shadow_linter = ShadowLinter(self.shadow_manager, verbose=False)
        self.shadow_compiler = ShadowCompiler(
            self.shadow_manager, verbose=False)

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

    def get_all_file_changes(self) -> Dict[str, FileChangeEntry]:
        """
        获取当前记录的所有文件变更信息。

        Returns:
            字典，key 为文件路径，value 为变更详情
        """
        return self.file_changes

    def get_changed_files_from_shadow(self) -> List[str]:
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

    @byzerllm.prompt()
    def _analyze(self, request: AgenticEditRequest) -> str:
        """        
        You are a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices.

        ====

        FILES CONTEXT

        The following files are provided to you as context for the user's task. You can use these files to understand the project structure and codebase, and to make informed decisions about which files to modify.
        If you need to read more files, you can use the tools to find and read more files.

        <files>
        {{files}}
        </files>

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
        Description: Request to execute a CLI command on the system. Use this when you need to perform system operations or run specific commands to accomplish any step in the user's task. You must tailor your command to the user's system and provide a clear explanation of what the command does. For command chaining, use the appropriate chaining syntax for the user's shell. Prefer to execute complex CLI commands over creating executable scripts, as they are more flexible and easier to run. Commands will be executed in the current working directory: ${cwd.toPosix()}
        Parameters:
        - command: (required) The CLI command to execute. This should be valid for the current operating system. Ensure the command is properly formatted and does not contain any harmful instructions.
        - requires_approval: (required) A boolean indicating whether this command requires explicit user approval before execution in case the user has auto-approve mode enabled. Set to 'true' for potentially impactful operations like installing/uninstalling packages, deleting/overwriting files, system configuration changes, network operations, or any commands that could have unintended side effects. Set to 'false' for safe operations like reading files/directories, running development servers, building projects, and other non-destructive operations.
        Usage:
        <execute_command>
        <command>Your command here</command>
        <requires_approval>true or false</requires_approval>
        </execute_command>

        ## list_package_info
        Description: Request to retrieve information about a source code package, such as recent changes or documentation summary, to better understand the code context. It accepts a directory path (absolute or relative to the current project).
        Parameters:
        - path: (required) The source code package directory path.
        Usage:
        <list_package_info>
        <path>relative/or/absolute/package/path</path>
        </list_package_info>

        ## read_file
        Description: Request to read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file you do not know the contents of, for example to analyze code, review text files, or extract information from configuration files. Automatically extracts raw text from PDF and DOCX files. May not be suitable for other types of binary files, as it returns the raw content as a string.
        Parameters:
        - path: (required) The path of the file to read (relative to the current working directory ${cwd.toPosix()})
        Usage:
        <read_file>
        <path>File path here</path>
        </read_file>

        ## write_to_file
        Description: Request to write content to a file at the specified path. If the file exists, it will be overwritten with the provided content. If the file doesn't exist, it will be created. This tool will automatically create any directories needed to write the file.
        Parameters:
        - path: (required) The path of the file to write to (relative to the current working directory ${cwd.toPosix()})
        - content: (required) The content to write to the file. ALWAYS provide the COMPLETE intended content of the file, without any truncation or omissions. You MUST include ALL parts of the file, even if they haven't been modified.
        Usage:
        <write_to_file>
        <path>File path here</path>
        <content>
        Your file content here
        </content>
        </write_to_file>

        ## replace_in_file
        Description: Request to replace sections of content in an existing file using SEARCH/REPLACE blocks that define exact changes to specific parts of the file. This tool should be used when you need to make targeted changes to specific parts of a file.
        Parameters:
        - path: (required) The path of the file to modify (relative to the current working directory ${cwd.toPosix()})
        - diff: (required) One or more SEARCH/REPLACE blocks following this exact format:
        \`\`\`
        <<<<<<< SEARCH
        [exact content to find]
        =======
        [new content to replace with]
        >>>>>>> REPLACE
        \`\`\`
        Critical rules:
        1. SEARCH content must match the associated file section to find EXACTLY:
            * Match character-for-character including whitespace, indentation, line endings
            * Include all comments, docstrings, etc.
        2. SEARCH/REPLACE blocks will ONLY replace the first match occurrence.
            * Including multiple unique SEARCH/REPLACE blocks if you need to make multiple changes.
            * Include *just* enough lines in each SEARCH section to uniquely match each set of lines that need to change.
            * When using multiple SEARCH/REPLACE blocks, list them in the order they appear in the file.
        3. Keep SEARCH/REPLACE blocks concise:
            * Break large SEARCH/REPLACE blocks into a series of smaller blocks that each change a small portion of the file.
            * Include just the changing lines, and a few surrounding lines if needed for uniqueness.
            * Do not include long runs of unchanging lines in SEARCH/REPLACE blocks.
            * Each line must be complete. Never truncate lines mid-way through as this can cause matching failures.
        4. Special operations:
            * To move code: Use two SEARCH/REPLACE blocks (one to delete from original + one to insert at new location)
            * To delete code: Use empty REPLACE section
        Usage:
        <replace_in_file>
        <path>File path here</path>
        <diff>
        Search and replace blocks here
        </diff>
        </replace_in_file>

        ## search_files
        Description: Request to perform a regex search across files in a specified directory, providing context-rich results. This tool searches for patterns or specific content across multiple files, displaying each match with encapsulating context.
        Parameters:
        - path: (required) The path of the directory to search in (relative to the current working directory ${cwd.toPosix()}). This directory will be recursively searched.
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
        - path: (required) The path of the directory to list contents for (relative to the current working directory ${cwd.toPosix()})
        - recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.
        Usage:
        <list_files>
        <path>Directory path here</path>
        <recursive>true or false (optional)</recursive>
        </list_files>

        ## list_code_definition_names
        Description: Request to list definition names (classes, functions, methods, etc.) used in source code files at the top level of the specified directory. This tool provides insights into the codebase structure and important constructs, encapsulating high-level concepts and relationships that are crucial for understanding the overall architecture.
        Parameters:
        - path: (required) The path of the directory (relative to the current working directory ${cwd.toPosix()}) to list top level source code definitions for.
        Usage:
        <list_code_definition_names>
        <path>Directory path here</path>
        </list_code_definition_names>

        ## ask_followup_question
        Description: Ask the user a question to gather additional information needed to complete the task. This tool should be used when you encounter ambiguities, need clarification, or require more details to proceed effectively. It allows for interactive problem-solving by enabling direct communication with the user. Use this tool judiciously to maintain a balance between gathering necessary information and avoiding excessive back-and-forth.
        Parameters:
        - question: (required) The question to ask the user. This should be a clear, specific question that addresses the information you need.
        - options: (optional) An array of 2-5 options for the user to choose from. Each option should be a string describing a possible answer. You may not always need to provide options, but it may be helpful in many cases where it can save the user from having to type out a response manually. IMPORTANT: NEVER include an option to toggle to Act mode, as this would be something you need to direct the user to do manually themselves if needed.
        Usage:
        <ask_followup_question>
        <question>Your question here</question>
        <options>
        Array of options here (optional), e.g. ["Option 1", "Option 2", "Option 3"]
        </options>
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

        ## plan_mode_respond
        Description: Respond to the user's inquiry in an effort to plan a solution to the user's task. This tool should be used when you need to provide a response to a question or statement from the user about how you plan to accomplish the task. This tool is only available in PLAN MODE. The environment_details will specify the current mode, if it is not PLAN MODE then you should not use this tool. Depending on the user's message, you may ask questions to get clarification about the user's request, architect a solution to the task, and to brainstorm ideas with the user. For example, if the user's task is to create a website, you may start by asking some clarifying questions, then present a detailed plan for how you will accomplish the task given the context, and perhaps engage in a back and forth to finalize the details before the user switches you to ACT MODE to implement the solution.
        Parameters:
        - response: (required) The response to provide to the user. Do not try to use tools in this parameter, this is simply a chat response. (You MUST use the response parameter, do not simply place the response text directly within <plan_mode_respond> tags.)
        - options: (optional) An array of 2-5 options for the user to choose from. Each option should be a string describing a possible choice or path forward in the planning process. This can help guide the discussion and make it easier for the user to provide input on key decisions. You may not always need to provide options, but it may be helpful in many cases where it can save the user from having to type out a response manually. Do NOT present an option to toggle to Act mode, as this will be something you need to direct the user to do manually themselves.
        Usage:
        <plan_mode_respond>
        <response>Your response here</response>
        <options>
        Array of options here (optional), e.g. ["Option 1", "Option 2", "Option 3"]
        </options>
        </plan_mode_respond>

        ## mcp_tool
        Description: Request to execute a tool via the Model Context Protocol (MCP) server. Use this when you need to execute a tool that is not natively supported by the agentic edit tools.
        Parameters:
        - server_name: (optional) The name of the MCP server to use. If not provided, the tool will automatically choose the best server based on the query.
        - tool_name: (optional) The name of the tool to execute. If not provided, the tool will automatically choose the best tool in the selected server based on the query.
        - query: (required) The query to pass to the tool.
        Usage:
        <use_mcp_tool>
        <server_name>xxx</server_name>
        <tool_name>xxxx</tool_name>
        <query>
        Your query here
        </query>
        </use_mcp_tool> 

        {%if mcp_server_info %}
        ### MCP_SERVER_LIST
        {{mcp_server_info}}
        {%endif%}

        # Tool Use Examples

        ## Example 1: Requesting to execute a command

        <execute_command>
        <command>npm run dev</command>
        <requires_approval>false</requires_approval>
        </execute_command>

        ## Example 2: Requesting to create a new file

        <write_to_file>
        <path>src/frontend-config.json</path>
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

        ## Example 3: Requesting to make targeted edits to a file

        <replace_in_file>
        <path>src/components/App.tsx</path>
        <diff>
        <<<<<<< SEARCH
        import React from 'react';
        =======
        import React, { useState } from 'react';
        >>>>>>> REPLACE

        <<<<<<< SEARCH
        function handleSubmit() {
        saveData();
        setLoading(false);
        }

        =======
        >>>>>>> REPLACE

        <<<<<<< SEARCH
        return (
        <div>
        =======
        function handleSubmit() {
        saveData();
        setLoading(false);
        }

        return (
        <div>
        >>>>>>> REPLACE
        </diff>
        </replace_in_file>

        ## Example 4: Another example of using an MCP tool (where the server name is a unique identifier listed in MCP_SERVER_LIST)

        <use_mcp_tool>
        <server_name>github</server_name>
        <tool_name>create_issue</tool_name>
        <query>ower is octocat, repo is hello-world, title is Found a bug, body is I'm having a problem with this. labels is "bug" and "help wanted",assignees is "octocat"</query>        
        </use_mcp_tool>                

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

        EDITING FILES

        You have access to two tools for working with files: **write_to_file** and **replace_in_file**. Understanding their roles and selecting the right one for the job will help ensure efficient and accurate modifications.

        # write_to_file

        ## Purpose

        - Create a new file, or overwrite the entire contents of an existing file.

        ## When to Use

        - Initial file creation, such as when scaffolding a new project.  
        - Overwriting large boilerplate files where you want to replace the entire content at once.
        - When the complexity or number of changes would make replace_in_file unwieldy or error-prone.
        - When you need to completely restructure a file's content or change its fundamental organization.

        ## Important Considerations

        - Using write_to_file requires providing the file's complete final content.  
        - If you only need to make small changes to an existing file, consider using replace_in_file instead to avoid unnecessarily rewriting the entire file.
        - While write_to_file should not be your default choice, don't hesitate to use it when the situation truly calls for it.

        # replace_in_file

        ## Purpose

        - Make targeted edits to specific parts of an existing file without overwriting the entire file.

        ## When to Use

        - Small, localized changes like updating a few lines, function implementations, changing variable names, modifying a section of text, etc.
        - Targeted improvements where only specific portions of the file's content needs to be altered.
        - Especially useful for long files where much of the file will remain unchanged.

        ## Advantages

        - More efficient for minor edits, since you don't need to supply the entire file content.  
        - Reduces the chance of errors that can occur when overwriting large files.

        # Choosing the Appropriate Tool

        - **Default to replace_in_file** for most changes. It's the safer, more precise option that minimizes potential issues.
        - **Use write_to_file** when:
        - Creating new files
        - The changes are so extensive that using replace_in_file would be more complex or risky
        - You need to completely reorganize or restructure a file
        - The file is relatively small and the changes affect most of its content
        - You're generating boilerplate or template files

        # Auto-formatting Considerations

        - After using either write_to_file or replace_in_file, the user's editor may automatically format the file
        - This auto-formatting may modify the file contents, for example:
        - Breaking single lines into multiple lines
        - Adjusting indentation to match project style (e.g. 2 spaces vs 4 spaces vs tabs)
        - Converting single quotes to double quotes (or vice versa based on project preferences)
        - Organizing imports (e.g. sorting, grouping by type)
        - Adding/removing trailing commas in objects and arrays
        - Enforcing consistent brace style (e.g. same-line vs new-line)
        - Standardizing semicolon usage (adding or removing based on style)
        - The write_to_file and replace_in_file tool responses will include the final state of the file after any auto-formatting
        - Use this final state as your reference point for any subsequent edits. This is ESPECIALLY important when crafting SEARCH blocks for replace_in_file which require the content to match what's in the file exactly.

        # Workflow Tips

        1. Before editing, assess the scope of your changes and decide which tool to use.
        2. For targeted edits, apply replace_in_file with carefully crafted SEARCH/REPLACE blocks. If you need multiple changes, you can stack multiple SEARCH/REPLACE blocks within a single replace_in_file call.
        3. For major overhauls or initial file creation, rely on write_to_file.
        4. Once the file has been edited with either write_to_file or replace_in_file, the system will provide you with the final state of the modified file. Use this updated content as the reference point for any subsequent SEARCH/REPLACE operations, since it reflects any auto-formatting or user-applied changes.

        By thoughtfully selecting between write_to_file and replace_in_file, you can make your file editing process smoother, safer, and more efficient.

        ====

        ACT MODE V.S. PLAN MODE

        In each user message, the environment_details will specify the current mode. There are two modes:

        - ACT MODE: In this mode, you have access to all tools EXCEPT the plan_mode_respond tool.
        - In ACT MODE, you use tools to accomplish the user's task. Once you've completed the user's task, you use the attempt_completion tool to present the result of the task to the user.
        - PLAN MODE: In this special mode, you have access to the plan_mode_respond tool.
        - In PLAN MODE, the goal is to gather information and get context to create a detailed plan for accomplishing the task, which the user will review and approve before they switch you to ACT MODE to implement the solution.
        - In PLAN MODE, when you need to converse with the user or present a plan, you should use the plan_mode_respond tool to deliver your response directly, rather than using <thinking> tags to analyze when to respond. Do not talk about using plan_mode_respond - just use it directly to share your thoughts and provide helpful answers.

        ## What is PLAN MODE?

        - While you are usually in ACT MODE, the user may switch to PLAN MODE in order to have a back and forth with you to plan how to best accomplish the task. 
        - When starting in PLAN MODE, depending on the user's request, you may need to do some information gathering e.g. using read_file or search_files to get more context about the task. You may also ask the user clarifying questions to get a better understanding of the task. You may return mermaid diagrams to visually display your understanding.
        - Once you've gained more context about the user's request, you should architect a detailed plan for how you will accomplish the task. Returning mermaid diagrams may be helpful here as well.
        - Then you might ask the user if they are pleased with this plan, or if they would like to make any changes. Think of this as a brainstorming session where you can discuss the task and plan the best way to accomplish it.
        - If at any point a mermaid diagram would make your plan clearer to help the user quickly see the structure, you are encouraged to include a Mermaid code block in the response. (Note: if you use colors in your mermaid diagrams, be sure to use high contrast colors so the text is readable.)
        - Finally once it seems like you've reached a good plan, ask the user to switch you back to ACT MODE to implement the solution.

        ====

        CAPABILITIES

        - You have access to tools that let you execute CLI commands on the user's computer, list files, view source code definitions, regex search${
            supportsComputerUse ? ", use the browser" : ""
        }, read and edit files, and ask follow-up questions. These tools help you effectively accomplish a wide range of tasks, such as writing code, making edits or improvements to existing files, understanding the current state of a project, performing system operations, and much more.
        - When the user initially gives you a task, a recursive list of all filepaths in the current working directory ('${cwd.toPosix()}') will be included in environment_details. This provides an overview of the project's file structure, offering key insights into the project from directory/file names (how developers conceptualize and organize their code) and file extensions (the language used). This can also guide decision-making on which files to explore further. If you need to further explore directories such as outside the current working directory, you can use the list_files tool. If you pass 'true' for the recursive parameter, it will list files recursively. Otherwise, it will list files at the top level, which is better suited for generic directories where you don't necessarily need the nested structure, like the Desktop.
        - You can use search_files to perform regex searches across files in a specified directory, outputting context-rich results that include surrounding lines. This is particularly useful for understanding code patterns, finding specific implementations, or identifying areas that need refactoring.
        - You can use the list_code_definition_names tool to get an overview of source code definitions for all files at the top level of a specified directory. This can be particularly useful when you need to understand the broader context and relationships between certain parts of the code. You may need to call this tool multiple times to understand various parts of the codebase related to the task.
            - For example, when asked to make edits or improvements you might analyze the file structure in the initial environment_details to get an overview of the project, then use list_code_definition_names to get further insight using source code definitions for files located in relevant directories, then read_file to examine the contents of relevant files, analyze the code and suggest improvements or make necessary edits, then use the replace_in_file tool to implement changes. If you refactored code that could affect other parts of the codebase, you could use search_files to ensure you update other files as needed.
        - You can use the execute_command tool to run commands on the user's computer whenever you feel it can help accomplish the user's task. When you need to execute a CLI command, you must provide a clear explanation of what the command does. Prefer to execute complex CLI commands over creating executable scripts, since they are more flexible and easier to run. Interactive and long-running commands are allowed, since the commands are run in the user's VSCode terminal. The user may keep commands running in the background and you will be kept updated on their status along the way. Each command you execute is run in a new terminal instance.

        ====

        RULES

        - Your current working directory is: {{current_project}}
        - You cannot \`cd\` into a different directory to complete a task. You are stuck operating from '${cwd.toPosix()}', so be sure to pass in the correct 'path' parameter when using tools that require a path.
        - Do not use the ~ character or $HOME to refer to the home directory.
        - Before using the execute_command tool, you must first think about the SYSTEM INFORMATION context provided to understand the user's environment and tailor your commands to ensure they are compatible with their system. You must also consider if the command you need to run should be executed in a specific directory outside of the current working directory '${cwd.toPosix()}', and if so prepend with \`cd\`'ing into that directory && then executing the command (as one command since you are stuck operating from '${cwd.toPosix()}'). For example, if you needed to run \`npm install\` in a project outside of '${cwd.toPosix()}', you would need to prepend with a \`cd\` i.e. pseudocode for this would be \`cd (path to project) && (command, in this case npm install)\`.
        - When using the search_files tool, craft your regex patterns carefully to balance specificity and flexibility. Based on the user's task you may use it to find code patterns, TODO comments, function definitions, or any text-based information across the project. The results include context, so analyze the surrounding code to better understand the matches. Leverage the search_files tool in combination with other tools for more comprehensive analysis. For example, use it to find specific code patterns, then use read_file to examine the full context of interesting matches before using replace_in_file to make informed changes.
        - When creating a new project (such as an app, website, or any software project), organize all new files within a dedicated project directory unless the user specifies otherwise. Use appropriate file paths when creating files, as the write_to_file tool will automatically create any necessary directories. Structure the project logically, adhering to best practices for the specific type of project being created. Unless otherwise specified, new projects should be easily run without additional setup, for example most projects can be built in HTML, CSS, and JavaScript - which you can open in a browser.
        - Be sure to consider the type of project (e.g. Python, JavaScript, web application) when determining the appropriate structure and files to include. Also consider what files may be most relevant to accomplishing the task, for example looking at a project's manifest file would help you understand the project's dependencies, which you could incorporate into any code you write.
        - When making changes to code, always consider the context in which the code is being used. Ensure that your changes are compatible with the existing codebase and that they follow the project's coding standards and best practices.
        - When you want to modify a file, use the replace_in_file or write_to_file tool directly with the desired changes. You do not need to display the changes before using the tool.
        - Do not ask for more information than necessary. Use the tools provided to accomplish the user's request efficiently and effectively. When you've completed your task, you must use the attempt_completion tool to present the result to the user. The user may provide feedback, which you can use to make improvements and try again.
        - You are only allowed to ask the user questions using the ask_followup_question tool. Use this tool only when you need additional details to complete a task, and be sure to use a clear and concise question that will help you move forward with the task. However if you can use the available tools to avoid having to ask the user questions, you should do so. For example, if the user mentions a file that may be in an outside directory like the Desktop, you should use the list_files tool to list the files in the Desktop and check if the file they are talking about is there, rather than asking the user to provide the file path themselves.
        - When executing commands, if you don't see the expected output, assume the terminal executed the command successfully and proceed with the task. The user's terminal may be unable to stream the output back properly. If you absolutely need to see the actual terminal output, use the ask_followup_question tool to request the user to copy and paste it back to you.
        - The user may provide a file's contents directly in their message, in which case you shouldn't use the read_file tool to get the file contents again since you already have it.
        - Your goal is to try to accomplish the user's task, NOT engage in a back and forth conversation.
        - NEVER end attempt_completion result with a question or request to engage in further conversation! Formulate the end of your result in a way that is final and does not require further input from the user.
        - You are STRICTLY FORBIDDEN from starting your messages with "Great", "Certainly", "Okay", "Sure". You should NOT be conversational in your responses, but rather direct and to the point. For example you should NOT say "Great, I've updated the CSS" but instead something like "I've updated the CSS". It is important you be clear and technical in your messages.
        - When presented with images, utilize your vision capabilities to thoroughly examine them and extract meaningful information. Incorporate these insights into your thought process as you accomplish the user's task.
        - At the end of each user message, you will automatically receive environment_details. This information is not written by the user themselves, but is auto-generated to provide potentially relevant context about the project structure and environment. While this information can be valuable for understanding the project context, do not treat it as a direct part of the user's request or response. Use it to inform your actions and decisions, but don't assume the user is explicitly asking about or referring to this information unless they clearly do so in their message. When using environment_details, explain your actions clearly to ensure the user understands, as they may not be aware of these details.
        - Before executing commands, check the "Actively Running Terminals" section in environment_details. If present, consider how these active processes might impact your task. For example, if a local development server is already running, you wouldn't need to start it again. If no active terminals are listed, proceed with command execution as normal.
        - When using the replace_in_file tool, you must include complete lines in your SEARCH blocks, not partial lines. The system requires exact line matches and cannot match partial lines. For example, if you want to match a line containing "const x = 5;", your SEARCH block must include the entire line, not just "x = 5" or other fragments.
        - When using the replace_in_file tool, if you use multiple SEARCH/REPLACE blocks, list them in the order they appear in the file. For example if you need to make changes to both line 10 and line 50, first include the SEARCH/REPLACE block for line 10, followed by the SEARCH/REPLACE block for line 50.
        - It is critical you wait for the user's response after each tool use, in order to confirm the success of the tool use. For example, if asked to make a todo app, you would create a file, wait for the user's response it was created successfully, then create another file if needed, wait for the user's response it was created successfully, etc.        

        ====

        SYSTEM INFORMATION

        Operating System: {{os_distribution}}
        Default Shell: {{shell_type}}
        Home Directory: {{home_dir}}
        Current Working Directory: {{current_project}}

        ====

        OBJECTIVE

        You accomplish a given task iteratively, breaking it down into clear steps and working through them methodically.

        1. Analyze the user's task and set clear, achievable goals to accomplish it. Prioritize these goals in a logical order.
        2. Work through these goals sequentially, utilizing available tools one at a time as necessary. Each goal should correspond to a distinct step in your problem-solving process. You will be informed on the work completed and what's remaining as you go.
        3. Remember, you have extensive capabilities with access to a wide range of tools that can be used in powerful and clever ways as necessary to accomplish each goal. Before calling a tool, do some analysis within <thinking></thinking> tags. First, analyze the file structure provided in environment_details to gain context and insights for proceeding effectively. Then, think about which of the provided tools is the most relevant tool to accomplish the user's task. Next, go through each of the required parameters of the relevant tool and determine if the user has directly provided or given enough information to infer a value. When deciding if the parameter can be inferred, carefully consider all the context to see if it supports a specific value. If all of the required parameters are present or can be reasonably inferred, close the thinking tag and proceed with the tool use. BUT, if one of the values for a required parameter is missing, DO NOT invoke the tool (not even with fillers for the missing params) and instead, ask the user to provide the missing parameters using the ask_followup_question tool. DO NOT ask for more information on optional parameters if it is not provided.
        4. Once you've completed the user's task, you must use the attempt_completion tool to present the result of the task to the user. You may also provide a CLI command to showcase the result of your task; this can be particularly useful for web development tasks, where you can run e.g. \`open index.html\` to show the website you've built.
        5. The user may provide feedback, which you can use to make improvements and try again. But DO NOT continue in pointless back and forth conversations, i.e. don't end your responses with questions or offers for further assistance.

        {% if enable_active_context %}
        **Very Important Notice**
        Each directory has a description file stored separately. For example, the description for the directory `{{ current_project }}/src/abc/bbc` can be found in the file `{{ current_project }}/.auto-coder/active-context/src/abc/bbc/active.md`.
        You can use the tool  `read_file` to read these description files, which helps you decide exactly which files need detailed attention. Note that the `active.md` file does not contain information about all files within the directory—it only includes information 
        about the files that were recently changed.
        {% endif %}

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
        import os
        extra_docs = {}
        rules_dir = os.path.join(self.args.source_dir,
                                 ".auto-coder", "autocoderrules")
        if os.path.isdir(rules_dir):
            for fname in os.listdir(rules_dir):
                if fname.endswith(".md"):
                    fpath = os.path.join(rules_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                            key = os.path.splitext(fname)[0]
                            extra_docs[key] = content
                    except Exception:
                        continue

        env_info = detect_env()
        shell_type = "bash"
        if shells.is_running_in_cmd():
            shell_type = "cmd"
        elif shells.is_running_in_powershell():
            shell_type = "powershell"
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
            "enable_active_context": self.args.enable_active_context,
            "extra_docs": extra_docs,
        }

    # Removed _execute_command_result and execute_auto_command methods
    def _reconstruct_tool_xml(self, tool: BaseTool) -> str:
        """
        Reconstructs the XML representation of a tool call from its Pydantic model.
        """
        tool_tag = next(
            (tag for tag, model in TOOL_MODEL_MAP.items() if isinstance(tool, model)), None)
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

    def analyze(self, request: AgenticEditRequest) -> Generator[Union[LLMOutputEvent, LLMThinkingEvent, ToolCallEvent, ToolResultEvent, CompletionEvent, ErrorEvent], None, None]:
        """
        Analyzes the user request, interacts with the LLM, parses responses,
        executes tools, and yields structured events for visualization until completion or error.
        """
        system_prompt = self._analyze.prompt(request)
        # print(system_prompt)
        conversations = [
            {"role": "system", "content": system_prompt},
        ] + self.conversation_manager.get_history()
        conversations.append({
            "role": "user", "content": request.user_input
        })
        self.conversation_manager.add_user_message(request.user_input)
        logger.debug(
            f"Initial conversation history size: {len(conversations)}")

        tool_executed = False
        while True:
            global_cancel.check_and_raise()
            logger.info(
                f"Starting LLM interaction cycle. History size: {len(conversations)}")

            assistant_buffer = ""

            llm_response_gen = stream_chat_with_continue(
                llm=self.llm,
                conversations=conversations,
                llm_config={},  # Placeholder for future LLM configs
                args=self.args
            )

            meta_holder = byzerllm.MetaHolder()
            parsed_events = self.stream_and_parse_llm_response(
                llm_response_gen, meta_holder)

            for event in parsed_events:
                global_cancel.check_and_raise()
                if isinstance(event, (LLMOutputEvent, LLMThinkingEvent)):
                    assistant_buffer += event.text
                    yield event  # Yield text/thinking immediately for display

                elif isinstance(event, ToolCallEvent):
                    tool_executed = True
                    tool_obj = event.tool
                    tool_xml = event.tool_xml  # Already reconstructed by parser

                    # Append assistant's thoughts and the tool call to history
                    conversations.append({
                        "role": "assistant",
                        "content": assistant_buffer + tool_xml
                    })
                    self.conversation_manager.add_assistant_message(
                        assistant_buffer + tool_xml)
                    assistant_buffer = ""  # Reset buffer after tool call

                    yield event  # Yield the ToolCallEvent for display

                    # Handle AttemptCompletion separately as it ends the loop
                    if isinstance(tool_obj, AttemptCompletionTool):
                        logger.info(
                            "AttemptCompletionTool received. Finalizing session.")
                        yield CompletionEvent(completion=tool_obj, completion_xml=tool_xml)
                        logger.info(
                            "AgenticEdit analyze loop finished due to AttemptCompletion.")
                        return

                    if isinstance(tool_obj, PlanModeRespondTool):
                        logger.info(
                            "PlanModeRespondTool received. Finalizing session.")
                        yield PlanModeRespondEvent(completion=tool_obj, completion_xml=tool_xml)
                        logger.info(
                            "AgenticEdit analyze loop finished due to PlanModeRespond.")
                        return

                    # Resolve the tool
                    resolver_cls = TOOL_RESOLVER_MAP.get(type(tool_obj))
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

                    # Append the tool result (as user message) to history
                    conversations.append({
                        "role": "user",  # Simulating the user providing the tool result
                        "content": error_xml
                    })
                    self.conversation_manager.add_user_message(error_xml)
                    logger.debug(
                        f"Added tool result to conversations for tool {type(tool_obj).__name__}")
                    break  # After tool execution and result, break to start a new LLM cycle

                elif isinstance(event, ErrorEvent):
                    yield event  # Pass through errors
                    # Optionally stop the process on parsing errors
                    # logger.error("Stopping analyze loop due to parsing error.")
                    # return

            yield TokenUsageEvent(usage=meta_holder.meta)
            if not tool_executed:
                # No tool executed in this LLM response cycle
                logger.info("LLM response finished without executing a tool.")
                # Append any remaining assistant buffer to history if it wasn't followed by a tool
                if assistant_buffer:
                    conversations.append(
                        {"role": "assistant", "content": assistant_buffer})
                    self.conversation_manager.add_assistant_message(
                        assistant_buffer)
                # If the loop ends without AttemptCompletion, it means the LLM finished talking
                # without signaling completion. We might just stop or yield a final message.
                # Let's assume it stops here.
                break

        logger.info("AgenticEdit analyze loop finished.")

    def stream_and_parse_llm_response(
        self, generator: Generator[Tuple[str, Any], None, None], meta_holder: byzerllm.MetaHolder
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

                tool_cls = TOOL_MODEL_MAP.get(tool_tag)
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

        for content_chunk, metadata in generator:
            global_cancel.check_and_raise()

            meta_holder.meta = metadata
            logger.info(f"metadata: {metadata.input_tokens_count}")
            if not content_chunk:
                continue
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
                        if tool_name in TOOL_MODEL_MAP:
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

    def run_with_events(self, request: AgenticEditRequest):
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
            error_content = EventContentCreator.create_error(
                error_code="AGENT_FATAL_ERROR",
                error_message=f"An unexpected error occurred: {str(e)}",
                details={"exception_type": type(e).__name__}
            )
            event_manager.write_error(
                content=error_content.to_dict(), metadata=metadata.to_dict())
            # Re-raise the exception if needed, or handle appropriately
            raise e

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

    def run_in_terminal(self, request: AgenticEditRequest):
        """
        Runs the agentic edit process based on the request and displays
        the interaction streamingly in the terminal using Rich.
        """
        console = Console()
        project_name = os.path.basename(os.path.abspath(self.args.source_dir))
        console.rule(f"[bold cyan]Starting Agentic Edit: {project_name}[/]")
        console.print(Panel(
            f"[bold]{get_message('/agent/edit/user_query')}:[/bold]\n{request.user_input}", title=get_message("/agent/edit/objective"), border_style="blue"))

        try:
            self.apply_pre_changes()
            event_stream = self.analyze(request)
            for event in event_stream:
                if isinstance(event, LLMThinkingEvent):
                    # Render thinking within a less prominent style, maybe grey?
                    console.print(f"[grey50]{event.text}[/grey50]", end="")
                elif isinstance(event, LLMOutputEvent):
                    # Print regular LLM output, potentially as markdown if needed later
                    console.print(event.text, end="")
                elif isinstance(event, ToolCallEvent):
                    # Skip displaying AttemptCompletionTool's tool call
                    if isinstance(event.tool, AttemptCompletionTool):
                        continue  # Do not display AttemptCompletionTool tool call

                    tool_name = type(event.tool).__name__
                    # Use the new internationalized display function
                    display_content = get_tool_display_message(event.tool)
                    console.print(Panel(
                        display_content, title=f"🛠️ Action: {tool_name}", border_style="blue", title_align="left"))

                elif isinstance(event, ToolResultEvent):
                    # Skip displaying AttemptCompletionTool's result
                    if event.tool_name == "AttemptCompletionTool":
                        continue  # Do not display AttemptCompletionTool result

                    if event.tool_name == "PlanModeRespondTool":
                        continue

                    result = event.result
                    title = f"✅ Tool Result: {event.tool_name}" if result.success else f"❌ Tool Result: {event.tool_name}"
                    border_style = "green" if result.success else "red"
                    base_content = f"[bold]Status:[/bold] {'Success' if result.success else 'Failure'}\n"
                    base_content += f"[bold]Message:[/bold] {result.message}\n"

                    def _format_content(content):
                        if len(content) > 200:
                            return f"{content[:100]}\n...\n{content[-100:]}"
                        else:
                            return content

                    # Prepare panel for base info first
                    panel_content = [base_content]
                    syntax_content = None

                    if result.content is not None:
                        content_str = ""
                        try:
                            if isinstance(result.content, (dict, list)):
                                import json
                                content_str = json.dumps(
                                    result.content, indent=2, ensure_ascii=False)
                                syntax_content = Syntax(
                                    content_str, "json", theme="default", line_numbers=False)
                            elif isinstance(result.content, str) and ('\n' in result.content or result.content.strip().startswith('<')):
                                # Heuristic for code or XML/HTML
                                lexer = "python"  # Default guess
                                if event.tool_name == "ReadFileTool" and isinstance(event.result.message, str):
                                    # Try to guess lexer from file extension in message
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
                                        lexer = "text"  # Fallback lexer
                                elif event.tool_name == "ExecuteCommandTool":
                                    lexer = "shell"
                                else:
                                    lexer = "text"

                                syntax_content = Syntax(
                                    _format_content(result.content), lexer, theme="default", line_numbers=True)
                            else:
                                content_str = str(result.content)
                                # Append simple string content directly
                                panel_content.append(
                                    _format_content(content_str))
                        except Exception as e:
                            logger.warning(
                                f"Error formatting tool result content: {e}")
                            panel_content.append(
                                # Fallback
                                _format_content(str(result.content)))

                    # Print the base info panel
                    console.print(Panel("\n".join(
                        panel_content), title=title, border_style=border_style, title_align="left"))
                    # Print syntax highlighted content separately if it exists
                    if syntax_content:
                        console.print(syntax_content)
                elif isinstance(event, PlanModeRespondEvent):
                    console.print(Panel(Markdown(event.completion.response),
                                  title="🏁 Task Completion", border_style="green", title_align="left"))

                elif isinstance(event, CompletionEvent):
                    # 在这里完成实际合并
                    try:
                        self.apply_changes()
                    except Exception as e:
                        logger.exception(
                            f"Error merging shadow changes to project: {e}")

                    console.print(Panel(Markdown(event.completion.result),
                                  title="🏁 Task Completion", border_style="green", title_align="left"))
                    if event.completion.command:
                        console.print(
                            f"[dim]Suggested command:[/dim] [bold cyan]{event.completion.command}[/]")
                elif isinstance(event, ErrorEvent):
                    console.print(Panel(
                        f"[bold red]Error:[/bold red] {event.message}", title="🔥 Error", border_style="red", title_align="left"))

                time.sleep(0.1)  # Small delay for better visual flow

        except Exception as e:
            logger.exception(
                "An unexpected error occurred during agent execution:")
            console.print(Panel(
                f"[bold red]FATAL ERROR:[/bold red]\n{str(e)}", title="🔥 System Error", border_style="red"))
            raise e
        finally:
            console.rule("[bold cyan]Agentic Edit Finished[/]")
