"""
Default tools initialization module
Used to initialize and register default tools
"""
from typing import Dict, Optional, List, Any
from loguru import logger
import byzerllm
from .tool_registry import ToolRegistry
from .types import BaseTool, ToolDescription, ToolExample

# Import all tool classes
from .types import (
    ExecuteCommandTool, ReadFileTool, WriteToFileTool, ReplaceInFileTool,
    SearchFilesTool, ListFilesTool, AskFollowupQuestionTool,
    AttemptCompletionTool, PlanModeRespondTool, UseMcpTool,
    TalkToTool, TalkToGroupTool
)

# Import all resolvers
from .tools.execute_command_tool_resolver import ExecuteCommandToolResolver
from .tools.read_file_tool_resolver import ReadFileToolResolver
from .tools.write_to_file_tool_resolver import WriteToFileToolResolver
from .tools.replace_in_file_tool_resolver import ReplaceInFileToolResolver
from .tools.search_files_tool_resolver import SearchFilesToolResolver
from .tools.list_files_tool_resolver import ListFilesToolResolver
from .tools.ask_followup_question_tool_resolver import AskFollowupQuestionToolResolver
from .tools.attempt_completion_tool_resolver import AttemptCompletionToolResolver
from .tools.plan_mode_respond_tool_resolver import PlanModeRespondToolResolver
from .tools.use_mcp_tool_resolver import UseMcpToolResolver
from .tools.talk_to_tool_resolver import TalkToToolResolver
from .tools.talk_to_group_tool_resolver import TalkToGroupToolResolver


# Tool description generators with byzerllm.prompt() decorators

class ToolsCaseGenerator:

    def __init__(self, params: Dict[str, Any]):
        self.params = params

    @byzerllm.prompt()
    def editing_files_doc(self) -> str:
        """
        You have access to two tools for working with files: **write_to_file** and **replace_in_file**. Understanding their roles and selecting the right one for the job will help ensure efficient and accurate modifications.

        # write_to_file

        ## Purpose

        - Create a new file, or overwrite the entire contents of an existing file.

        ## When to Use

        - Initial file creation, such as when scaffolding a new research plan.  
        - Overwriting large research documents where you want to replace the entire content at once.
        - When the complexity or number of changes would make replace_in_file unwieldy or error-prone.

        ## Important Considerations

        - Using write_to_file requires providing the file's complete final content.  
        - If you only need to make small changes to an existing file, consider using replace_in_file instead to avoid unnecessarily rewriting the entire file.
        - Only use this for research planning and documentation, not system files.

        # replace_in_file

        ## Purpose

        - Make targeted edits to specific parts of an existing file without overwriting the entire file.

        ## When to Use

        - Small, localized changes like updating a few lines in a research document, modifying a search strategy, or adding new findings.
        - Targeted improvements where only specific portions of the file's content needs to be altered.
        - Especially useful for long research documents where much of the file will remain unchanged.

        ## Advantages

        - More efficient for minor edits, since you don't need to supply the entire file content.  
        - Reduces the chance of errors that can occur when overwriting large files.

        # Choosing the Appropriate Tool

        - **Default to replace_in_file** for most changes to existing research documents. It's the safer, more precise option that minimizes potential issues.
        - **Use write_to_file** when:
            - Creating new research documents
            - The changes are so extensive that using replace_in_file would be more complex or risky
            - You need to completely reorganize or restructure a document
            - The file is relatively small and the changes affect most of its content

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
        """
        return self.params


class ToolDescGenerators:

    def __init__(self, params: Dict[str, Any]):
        self.params = params

    @byzerllm.prompt()
    def execute_command(self) -> Dict:
        """
        Description: Request to execute a CLI command on the system. Use this when you need to perform system operations or run specific commands to accomplish any step in the user's task. You must tailor your command to the user's system and provide a clear explanation of what the command does. For command chaining, use the appropriate chaining syntax for the user's shell. Prefer to execute complex CLI commands over creating executable scripts, as they are more flexible and easier to run. Commands will be executed in the current working directory: {{current_project}}
        Parameters:
        - command: (required) The CLI command to execute. This should be valid for the current operating system. Ensure the command is properly formatted and does not contain any harmful instructions.
        - requires_approval: (required) A boolean indicating whether this command requires explicit user approval before execution in case the user has auto-approve mode enabled. Set to 'true' for potentially impactful operations like installing/uninstalling packages, deleting/overwriting files, system configuration changes, network operations, or any commands that could have unintended side effects. Set to 'false' for safe operations like reading files/directories, running development servers, building projects, and other non-destructive operations.
        Usage:
        <execute_command>
        <command>Your command here</command>
        <requires_approval>true or false</requires_approval>
        </execute_command>
        """
        return self.params

    @byzerllm.prompt()
    def list_package_info(self) -> Dict:
        """
        Description: Request to retrieve information about a source code package, such as recent changes or documentation summary, to better understand the code context. It accepts a directory path (absolute or relative to the current project).
        Parameters:
        - path: (required) The source code package directory path.
        Usage:
        <list_package_info>
        <path>relative/or/absolute/package/path</path>
        </list_package_info>
        """
        return self.params

    @byzerllm.prompt()
    def read_file(self) -> Dict:
        """
        Description: Request to read the contents of a file at the specified path. Use this when you need to examine the contents of an existing file you do not know the contents of, for example to analyze code, review text files, or extract information from configuration files. Automatically extracts raw text from PDF and DOCX files. May not be suitable for other types of binary files, as it returns the raw content as a string.
        Parameters:
        - path: (required) The path of the file to read (relative to the current working directory ${cwd.toPosix()})
        Usage:
        <read_file>
        <path>File path here</path>
        </read_file>
        """
        return self.params

    @byzerllm.prompt()
    def write_to_file(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def replace_in_file(self) -> Dict:
        """
        Description: Request to replace sections of content in an existing file using SEARCH/REPLACE blocks that define exact changes to specific parts of the file. This tool should be used when you need to make targeted changes to specific parts of a file.
        Parameters:
        - path: (required) The path of the file to modify (relative to the current working directory ${cwd.toPosix()})
        - diff: (required) One or more SEARCH/REPLACE blocks following this exact format:
        ```
        <<<<<<< SEARCH
        [exact content to find]
        =======
        [new content to replace with]
        >>>>>>> REPLACE
        ```
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
        """
        return self.params

    @byzerllm.prompt()
    def search_files(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def list_files(self) -> Dict:
        """
        Description: Request to list files and directories within the specified directory. If recursive is true, it will list all files and directories recursively. If recursive is false or not provided, it will only list the top-level contents. Do not use this tool to confirm the existence of files you may have created, as the user will let you know if the files were created successfully or not.
        Parameters:
        - path: (required) The path of the directory to list contents for (relative to the current working directory ${cwd.toPosix()})
        - recursive: (optional) Whether to list files recursively. Use true for recursive listing, false or omit for top-level only.
        Usage:
        <list_files>
        <path>Directory path here</path>
        <recursive>true or false (optional)</recursive>
        </list_files>
        """
        return self.params

    @byzerllm.prompt()
    def list_code_definition_names(self) -> Dict:
        """
        Description: Request to list definition names (classes, functions, methods, etc.) used in source code files at the top level of the specified directory. This tool provides insights into the codebase structure and important constructs, encapsulating high-level concepts and relationships that are crucial for understanding the overall architecture.
        Parameters:
        - path: (required) The path of the directory (relative to the current working directory ${cwd.toPosix()}) to list top level source code definitions for.
        Usage:
        <list_code_definition_names>
        <path>Directory path here</path>
        </list_code_definition_names>
        """
        return self.params

    @byzerllm.prompt()
    def ask_followup_question(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def attempt_completion(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def plan_mode_respond(self) -> Dict:
        """
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
        """
        return {}

    @byzerllm.prompt()
    def use_mcp_tool(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def talk_to(self) -> Dict:
        """
        Description: Send a message to another agent
        Parameters:
        - agent_name: (required) The name of the agent to talk to
        - content: (required) The message content
        - mentions: (optional) An array of agent names to mention in the message
        - print_conversation: (optional) Whether to print the conversation to the console
        Usage:
        <talk_to>
        <agent_name>assistant2</agent_name>
        <content>Hello assistant2, can you help me with this task?</content>
        <mentions>["assistant3"]</mentions>
        <print_conversation>true</print_conversation>
        </talk_to>
        """
        return self.params

    @byzerllm.prompt()
    def talk_to_group_description(self) -> Dict:
        """
        Description: Send a message to a group of agents
        Parameters:
        - group_name: (required) The name of the group to talk to
        - content: (required) The message content
        - mentions: (optional) An array of agent names to mention in the message
        - print_conversation: (optional) Whether to print the conversation to the console
        Usage:
        <talk_to_group>
        <group_name>research_team</group_name>
        <content>Hello team, I need your input on the research plan.</content>
        <mentions>["assistant2", "assistant3"]</mentions>
        <print_conversation>true</print_conversation>
        </talk_to_group>
        """
        return self.params


class ToolExampleGenerators:
    def __init__(self, params: Dict):
        self.params = params

    @byzerllm.prompt()
    def example_1(self) -> Dict:
        """
        <execute_command>
        <command>npm run dev</command>
        <requires_approval>false</requires_approval>
        </execute_command>
        """
        return self.params

    @byzerllm.prompt()
    def example_2(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def example_3(self) -> Dict:
        """
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
        """
        return self.params

    @byzerllm.prompt()
    def example_4(self) -> Dict:
        """
        <use_mcp_tool>
        <server_name>github</server_name>
        <tool_name>create_issue</tool_name>
        <query>ower is octocat, repo is hello-world, title is Found a bug, body is I'm having a problem with this. labels is "bug" and "help wanted",assignees is "octocat"</query>        
        </use_mcp_tool> 
        """
        return self.params


def register_default_tools_case_doc(params: Dict[str, Any]):
    """
    注册默认工具用例文档
    """
    # 获取所有已注册的工具
    registered_tools = set(ToolRegistry.get_all_registered_tools())

    tool_case_gen = ToolsCaseGenerator(params)

    # 定义默认工具用例文档
    DEFAULT_TOOLS_CASE_DOC = {
        "editing_files": {
            "tools": ["replace_in_file", "write_to_file"],
            "doc": tool_case_gen.editing_files_doc.prompt()
        }
    }

    for case_name, case_info in DEFAULT_TOOLS_CASE_DOC.items():
        # 检查所有工具是否存在
        tools = case_info["tools"]
        valid_tools = []

        for tool in tools:
            if tool in registered_tools:
                valid_tools.append(tool)
            else:
                logger.warning(f"用例文档 {case_name} 引用了不存在的工具: {tool}")

        # 只有当存在有效工具时才注册用例文档
        if valid_tools:
            ToolRegistry.register_tools_case_doc(
                case_name=case_name,
                tools=valid_tools,
                doc=case_info["doc"]
            )
            logger.info(
                f"成功注册用例文档 {case_name}, 有效工具: {', '.join(valid_tools)}")
        else:
            logger.warning(f"跳过注册用例文档 {case_name}, 因为没有有效工具")

    logger.info(f"处理了 {len(DEFAULT_TOOLS_CASE_DOC)} 个默认工具用例文档")

def get_default_tool_names():
    return [
        "execute_command",
        "read_file",
        "write_to_file",
        "replace_in_file",
        "search_files",
        "list_files",
        "ask_followup_question",
        "attempt_completion",
        "plan_mode_respond",
        "use_mcp_tool",
        "talk_to",
        "talk_to_group"
    ]

def register_default_tools(params: Dict[str, Any], default_tools_list: Optional[List[str]] = None):
    """
    Register default tools
    
    Args:
        params: Parameters for tool generators
        default_tools_list: Optional list of tool names to register. If provided, only tools in this list will be registered.
                          If None, all default tools will be registered.
    """
    tool_desc_gen = ToolDescGenerators(params)
    tool_examples_gen = ToolExampleGenerators(params)

    # 统一的工具定义数据结构
    DEFAULT_TOOLS = {
        "execute_command": {
            "tool_cls": ExecuteCommandTool,
            "resolver_cls": ExecuteCommandToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.execute_command.prompt(),
            ),
            "example": ToolExample(
                title="Requesting to execute a command",
                body=tool_examples_gen.example_1.prompt()
            ),
            "use_guideline": "",
            "category": "system",
            "is_default": True,
            "case_docs": []
        },
        "read_file": {
            "tool_cls": ReadFileTool,
            "resolver_cls": ReadFileToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.read_file.prompt(),
            ),
            "use_guideline": "",
            "category": "file_operation",
            "is_default": True,
            "case_docs": []
        },
        "write_to_file": {
            "tool_cls": WriteToFileTool,
            "resolver_cls": WriteToFileToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.write_to_file.prompt(),
            ),
            "example": ToolExample(
                title="Requesting to create a new file",
                body=tool_examples_gen.example_2.prompt()
            ),
            "use_guideline": "",
            "category": "file_operation",
            "is_default": True,
            "case_docs": ["editing_files"]
        },
        "replace_in_file": {
            "tool_cls": ReplaceInFileTool,
            "resolver_cls": ReplaceInFileToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.replace_in_file.prompt(),
            ),
            "use_guideline": "",
            "example": ToolExample(
                title="Requesting to make targeted edits to a file",
                body=tool_examples_gen.example_3.prompt()
            ),
            "category": "file_operation",
            "is_default": True,
            "case_docs": ["editing_files"]
        },
        "search_files": {
            "tool_cls": SearchFilesTool,
            "resolver_cls": SearchFilesToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.search_files.prompt(),
            ),
            "use_guideline": "",
            "category": "file_operation",
            "is_default": True,
            "case_docs": []
        },
        "list_files": {
            "tool_cls": ListFilesTool,
            "resolver_cls": ListFilesToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.list_files.prompt(),
            ),
            "use_guideline": "",
            "category": "file_operation",
            "is_default": True,
            "case_docs": []
        },
        "ask_followup_question": {
            "tool_cls": AskFollowupQuestionTool,
            "resolver_cls": AskFollowupQuestionToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.ask_followup_question.prompt(),
            ),
            "use_guideline": "",
            "category": "interaction",
            "is_default": True,
            "case_docs": []
        },
        "attempt_completion": {
            "tool_cls": AttemptCompletionTool,
            "resolver_cls": AttemptCompletionToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.attempt_completion.prompt(),
            ),
            "use_guideline": "",
            "category": "interaction",
            "is_default": True,
            "case_docs": []
        },
        "plan_mode_respond": {
            "tool_cls": PlanModeRespondTool,
            "resolver_cls": PlanModeRespondToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.plan_mode_respond.prompt(),
            ),
            "use_guideline": "",
            "category": "interaction",
            "is_default": True,
            "case_docs": []
        },
        "use_mcp_tool": {
            "tool_cls": UseMcpTool,
            "resolver_cls": UseMcpToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.use_mcp_tool.prompt(),
            ),
            "example": ToolExample(
                title="Another example of using an MCP tool (where the server name is a unique identifier listed in MCP_SERVER_LIST)",
                body=tool_examples_gen.example_4.prompt()
            ),
            "use_guideline": "",
            "category": "external",
            "is_default": True,
            "case_docs": []
        },
        "talk_to": {
            "tool_cls": TalkToTool,
            "resolver_cls": TalkToToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.talk_to.prompt(),
            ),
            "use_guideline": "",
            "category": "interaction",
            "is_default": True,
            "case_docs": []
        },
        "talk_to_group": {
            "tool_cls": TalkToGroupTool,
            "resolver_cls": TalkToGroupToolResolver,
            "description": ToolDescription(
                description=tool_desc_gen.talk_to_group_description.prompt(),
            ),
            "use_guideline": "",
            "category": "interaction",
            "is_default": True,
            "case_docs": []
        }
    }
    # 先使用统一的工具注册方法注册工具
    registered_count = 0
    for tool_tag, tool_info in DEFAULT_TOOLS.items():
        # attempt_completion 工具是必须注册的
        if tool_tag == "attempt_completion":
            ToolRegistry.register_unified_tool(tool_tag, tool_info)
            registered_count += 1
            continue
            
        # 如果提供了工具列表，则只注册列表中的工具
        if default_tools_list is not None and tool_tag not in default_tools_list:
            continue
            
        ToolRegistry.register_unified_tool(tool_tag, tool_info)
        registered_count += 1        

    logger.info(
        f"Registered {registered_count} default tools using unified registration")

    # 然后注册默认工具用例文档
    # 这样可以确保在注册用例文档时，所有工具已经注册完成
    register_default_tools_case_doc(params)


def get_registered_default_tools() -> List[str]:
    """
    Get the list of registered default tools

    Returns:
        List of default tool tags
    """
    return ToolRegistry.get_default_tools()
