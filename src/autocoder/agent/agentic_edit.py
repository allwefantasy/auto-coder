from enum import Enum
import json
import os
import time
from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any, Union, Callable, Optional
from autocoder.common.printer import Printer
from rich.console import Console
from rich.panel import Panel
from pydantic import SkipValidation

from autocoder.common.result_manager import ResultManager
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from byzerllm.utils.str2model import to_model
from autocoder.common import git_utils
from autocoder.commands.tools import AutoCommandTools
from autocoder.auto_coder import AutoCoderArgs
from autocoder.common import detect_env
from autocoder.common import shells
from loguru import logger
from autocoder.utils import llms as llms_utils
from autocoder.rag.token_counter import count_tokens
from autocoder.common.global_cancel import global_cancel
from autocoder.common.auto_configure import config_readme
from autocoder.utils.auto_project_type import ProjectTypeAnalyzer
from rich.text import Text
from autocoder.common.mcp_server import get_mcp_server, McpServerInfoRequest
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.run_context import get_run_context
import re
from typing import Iterator, Union, Type, Generator
from xml.etree import ElementTree as ET
from autocoder.common.stream_out_type import AgenticFilterStreamOutType
from autocoder.common import SourceCodeList
from autocoder.agent.agentic_edit_types import (AgenticFilterRequest,
                                                AgenticFilterResponse,
                                                MemoryConfig,
                                                CommandConfig,
                                                BaseTool,
                                                PlainTextOutput,
                                                ExecuteCommandTool,
                                                ReadFileTool,
                                                WriteToFileTool,
                                                ReplaceInFileTool,
                                                SearchFilesTool,
                                                ListFilesTool,
                                                ListCodeDefinitionNamesTool,
                                                AskFollowupQuestionTool,
                                                AttemptCompletionTool,
                                                PlanModeRespondTool,
                                                UseMcpTool,TOOL_MODEL_MAP)


class AgenticEdit:
    def __init__(
        self,
        llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
        conversation_history: List[Dict[str, Any]],
        files: SourceCodeList,
        args: AutoCoderArgs,
        memory_config: MemoryConfig,
        command_config: Optional[CommandConfig] = None,
    ):
        self.llm = llm
        self.args = args
        self.printer = Printer()
        self.tools = AutoCommandTools(args=args, llm=self.llm)
        self.result_manager = ResultManager(source_dir=args.source_dir)
        self.files = files
        # Use existing args for max iterations
        self.max_iterations = args.auto_command_max_iterations
        self.conversation_history = conversation_history
        self.memory_config = memory_config
        self.command_config = command_config
        self.project_type_analyzer = ProjectTypeAnalyzer(
            args=args, llm=self.llm)
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
            self.mcp_server_info = ""

    @byzerllm.prompt()
    def _analyze(self, request: AgenticFilterRequest) -> str:
        """        
        You are a highly skilled software engineer with extensive knowledge in many programming languages, frameworks, design patterns, and best practices.

        ====

        FILES

        The following files are provided to you as context for the user's task. You can use these files to understand the project structure and codebase, and to make informed decisions about which files to modify.
        If you need to read more files, you can use the read_file tool.

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

        ## MCP_TOOL

        {%if mcp_server_info %}
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

        ## Example 4: Another example of using an MCP tool (where the server name is a unique identifier such as a URL)

        <use_mcp_tool>
        <server_name>github.com/modelcontextprotocol/servers/tree/main/src/github</server_name>
        <tool_name>create_issue</tool_name>
        <arguments>
        {
        "owner": "octocat",
        "repo": "hello-world",
        "title": "Found a bug",
        "body": "I'm having a problem with this.",
        "labels": ["bug", "help wanted"],
        "assignees": ["octocat"]
        }
        </arguments>
        </use_mcp_tool>`
                : ""
        }

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
        """
        env_info = detect_env()
        shell_type = "bash"
        if shells.is_running_in_cmd():
            shell_type = "cmd"
        elif shells.is_running_in_powershell():
            shell_type = "powershell"
        return {
            "current_files": self.memory_config.memory["current_files"]["files"],
            "conversation_history": self.conversation_history,
            "current_conf": json.dumps(self.memory_config.memory["conf"], indent=2),
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
        }

    @byzerllm.prompt()
    def _execute_command_result(self, result: str) -> str:
        """
        根据函数执行结果，返回下一个函数。

        下面是我们上一个函数执行结果:

        <function_result>
        {{ result }}
        </function_result>

        请根据命令执行结果以及前面的对话，返回下一个函数。

        *** 非常非常重要的提示 ***
        1. 如果你认为已经收集到足够信息来确定最终的文件列表，请务必调用 `output_result` 并以如下格式要求的JSON字符串作为 `response` 参数。最多允许 {{ max_iterations }} 次工具调用。
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
        2. 你最多尝试 {{ auto_command_max_iterations }} 次，如果 {{ auto_command_max_iterations }} 次都没有满足要求，则不要返回任何函数，确保 suggestions 为空。
        """
        return {
            "auto_command_max_iterations": self.args.auto_command_max_iterations,
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
        }

    def analyze(self, request: AgenticFilterRequest) -> Optional[AgenticFilterResponse]:
        # 获取 prompt 内容
        prompt = self._analyze.prompt(request)
        new_messages.append({"role": "system", "content": prompt})

        # 获取对当前项目变更的最近8条历史人物
        action_yml_file_manager = ActionYmlFileManager(self.args.source_dir)
        history_tasks = action_yml_file_manager.to_tasks_prompt(limit=8)
        new_messages = []

        if self.args.enable_task_history:
            new_messages.append({"role": "user", "content": history_tasks})
            new_messages.append(
                {
                    "role": "assistant",
                    "content": "好的，我知道最近的任务对项目的变更了，我会参考这些来更好的理解你的需求。",
                }
            )

        # 构造对话上下文
        conversations = new_messages + [{"role": "user", "content": prompt}]

        # 使用 stream_out 进行输出
        printer = Printer()
        title = printer.get_message_from_key("auto_command_analyzing")
        final_title = printer.get_message_from_key("auto_command_analyzed")

        def extract_command_response(content: str) -> str:
            # 提取 JSON 并转换为 AutoCommandResponse
            try:
                response = to_model(content, AutoCommandResponse)
                if response.suggestions:
                    command = response.suggestions[0].command
                    parameters = response.suggestions[0].parameters
                    if parameters:
                        params_str = ", ".join(
                            [f"{k}={v}" for k, v in parameters.items()]
                        )
                    else:
                        params_str = ""
                    return f"{command}({params_str})"
                else:
                    return printer.get_message_from_key("satisfied_prompt")
            except Exception as e:
                logger.error(f"Error extracting command response: {str(e)}")
                return content

        result_manager = ResultManager()
        success_flag = False

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=printer.get_message_from_key("agenticFilterContext")),
            metadata={
                "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
            }
        )

        while True:
            global_cancel.check_and_raise()
            # print(json.dumps(conversations, ensure_ascii=False, indent=4))
            model_name = ",".join(llms_utils.get_llm_names(self.llm))
            start_time = time.monotonic()
            result, last_meta = stream_out(
                self.llm.stream_chat_oai(
                    conversations=conversations, delta_mode=True),
                model_name=model_name,
                title=title,
                final_title=final_title,
                display_func=extract_command_response,
                args=self.args,
                extra_meta={
                    "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
                },
            )

            if last_meta:
                elapsed_time = time.monotonic() - start_time
                speed = last_meta.generated_tokens_count / elapsed_time

                # Get model info for pricing
                from autocoder.utils import llms as llm_utils

                model_info = (
                    llm_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                )
                input_price = model_info.get(
                    "input_price", 0.0) if model_info else 0.0
                output_price = (
                    model_info.get("output_price", 0.0) if model_info else 0.0
                )

                # Calculate costs
                input_cost = (
                    last_meta.input_tokens_count * input_price
                ) / 1000000  # Convert to millions
                output_cost = (
                    last_meta.generated_tokens_count * output_price
                ) / 1000000  # Convert to millions

                temp_content = printer.get_message_from_key_with_format(
                    "stream_out_stats",
                    model_name=",".join(llms_utils.get_llm_names(self.llm)),
                    elapsed_time=elapsed_time,
                    first_token_time=last_meta.first_token_time,
                    input_tokens=last_meta.input_tokens_count,
                    output_tokens=last_meta.generated_tokens_count,
                    input_cost=round(input_cost, 4),
                    output_cost=round(output_cost, 4),
                    speed=round(speed, 2),
                )
                printer.print_str_in_terminal(temp_content)
                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        content=EventContentCreator.ResultTokenStatContent(
                            model_name=model_name,
                            elapsed_time=elapsed_time,
                            first_token_time=last_meta.first_token_time,
                            input_tokens=last_meta.input_tokens_count,
                            output_tokens=last_meta.generated_tokens_count,
                            input_cost=round(input_cost, 4),
                            output_cost=round(output_cost, 4),
                            speed=round(speed, 2),
                        )
                    ).to_dict()
                )

            conversations.append({"role": "assistant", "content": result})
            # 提取 JSON 并转换为 AutoCommandResponse
            response = to_model(result, AutoCommandResponse)

            if not response or not response.suggestions:
                break

            # 执行命令
            command = response.suggestions[0].command
            parameters = response.suggestions[0].parameters

            # 打印正在执行的命令
            temp_content = printer.get_message_from_key_with_format(
                "auto_command_executing", command=command
            )
            printer.print_str_in_terminal(temp_content, style="blue")

            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(
                    content=EventContentCreator.ResultCommandPrepareStatContent(
                        command=command, parameters=parameters
                    ).to_dict()
                ), metadata={
                    "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
                }
            )
            try:
                self.execute_auto_command(command, parameters)
            except Exception as e:
                error_content = f"执行命令失败，错误信息：{e}"
                conversations.append(
                    {"role": "user", "content": error_content})
                continue

            content = ""
            last_result = result_manager.get_last()
            if last_result:
                action = last_result.meta["action"]
                if action == "coding":
                    # 如果上一步是 coding，则需要把上一步的更改前和更改后的内容作为上下文
                    changes = git_utils.get_changes_by_commit_message(
                        "", last_result.meta["commit_message"]
                    )
                    if changes.success:
                        for file_path, change in changes.changes.items():
                            if change:
                                content += f"## File: {file_path}[更改前]\n{change.before or 'New File'}\n\nFile: {file_path}\n\n[更改后]\n{change.after or 'Deleted File'}\n\n"
                    else:
                        content = printer.get_message_from_key(
                            "no_changes_made")
                else:
                    # 其他的直接获取执行结果
                    content = last_result.content

                if action != command:
                    # command 和 action 不一致，则认为命令执行失败，退出
                    temp_content = printer.get_message_from_key_with_format(
                        "auto_command_action_break", command=command, action=action
                    )
                    printer.print_str_in_terminal(temp_content, style="yellow")
                    get_event_manager(self.args.event_file).write_result(
                        EventContentCreator.create_result(
                            content=temp_content),
                        metadata={
                            "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
                        }
                    )
                    break

                if command == "output_result":
                    success_flag = True
                    break

                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        content=EventContentCreator.ResultCommandExecuteStatContent(
                            command=command, content=content
                        ).to_dict(),
                        metadata={
                            "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
                        }
                    )
                )

                # 打印执行结果
                console = Console()
                # 截取content前后200字符
                truncated_content = (
                    content[:200] + "\n...\n" + content[-200:]
                    if len(content) > 400
                    else content
                )
                title = printer.get_message_from_key_with_format(
                    "command_execution_result", action=action
                )
                # 转义内容，避免Rich将内容中的[]解释为markup语法
                text_content = Text(truncated_content)
                console.print(
                    Panel(
                        text_content, title=title, border_style="blue", padding=(1, 2)
                    )
                )

                # 添加新的对话内容
                new_content = self._execute_command_result.prompt(content)
                conversations.append({"role": "user", "content": new_content})

                # 统计 token 数量
                total_tokens = count_tokens(
                    json.dumps(conversations, ensure_ascii=False)
                )

                # 如果对话过长，使用默认策略进行修剪
                if total_tokens > self.args.conversation_prune_safe_zone_tokens:
                    self.printer.print_in_terminal(
                        "conversation_pruning_start",
                        style="yellow",
                        total_tokens=total_tokens,
                        safe_zone=self.args.conversation_prune_safe_zone_tokens,
                    )
                    from autocoder.common.conversation_pruner import ConversationPruner

                    pruner = ConversationPruner(self.args, self.llm)
                    conversations = pruner.prune_conversations(conversations)

            else:
                temp_content = printer.get_message_from_key_with_format(
                    "auto_command_break", command=command
                )
                printer.print_str_in_terminal(temp_content, style="yellow")
                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(content=temp_content),
                    metadata={
                        "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
                    }
                )
                break

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(
                content=printer.get_message_from_key("agenticFilterCommandResult")),
            metadata={
                "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value
            }
        )

        if success_flag:
            to_model(content, AgenticFilterResponse)
            # return AgenticFilterResponse(**json.loads(content))
        else:
            return None

    def execute_auto_command(self, command: str, parameters: Dict[str, Any]) -> None:
        """
        执行自动生成的命令
        """
        command_map = {
            "run_python": self.tools.run_python_code,
            "get_related_files_by_symbols": self.tools.get_related_files_by_symbols,
            "get_project_map": self.tools.get_project_map,
            "get_project_structure": self.tools.get_project_structure,
            "list_files": self.tools.list_files,
            "read_files": self.tools.read_files,
            "find_files_by_name": self.tools.find_files_by_name,
            "find_files_by_content": self.tools.find_files_by_content,
            "get_project_related_files": self.tools.get_project_related_files,
            "ask_user": self.tools.ask_user,
            "read_file_with_keyword_ranges": self.tools.read_file_with_keyword_ranges,
            "get_project_type": self.project_type_analyzer.analyze,
            "output_result": self.tools.output_result,
            "execute_mcp_server": self.tools.execute_mcp_server,
            "count_file_tokens": self.tools.count_file_tokens,
            "count_string_tokens": self.tools.count_string_tokens,
            "find_symbol_definition": self.tools.find_symbol_definition,
        }

        if command not in command_map:
            v = self.printer.get_message_from_key_with_format(
                "auto_command_not_found", style="red", command=command
            )
            raise Exception(v)
            return

        try:
            # 将参数字典转换为命令所需的格式
            if parameters:
                command_map[command](**parameters)
            else:
                command_map[command]()

        except Exception as e:
            error_msg = str(e)
            v = self.printer.get_message_from_key_with_format(
                "auto_command_failed", style="red", command=command, error=error_msg
            )
            raise Exception(v)

    def stream_and_parse_llm_response(
        self, generator: Iterator[str]
    ) -> Generator[Union[BaseTool, PlainTextOutput], None, None]:
        """
        Streamingly parses the LLM response generator, distinguishing between
        plain text and tool usage blocks, yielding corresponding Pydantic models.

        Args:
            generator: An iterator yielding string chunks from the LLM response.

        Yields:
            Union[BaseTool, PlainTextOutput]: Either a Pydantic model representing
            a detected tool usage or a PlainTextOutput model for plain text segments.
        """
        buffer = ""
        in_tool_block = False
        current_tool_tag = None
        # Regex to find the start tag, potentially with attributes, but we only care about the tag name
        # It captures the tag name in group 1. Handles simple tags like <tool_name>
        tool_start_pattern = re.compile(r"<([a-zA-Z0-9_]+?)>")
        plain_text_buffer = ""

        for chunk in generator:
            buffer += chunk
            logger.debug(f"Chunk received: '{chunk}', Buffer: '{buffer}'")

            while True:
                if not in_tool_block:
                    # Try to find the start of a potential tool block
                    match = tool_start_pattern.search(buffer)
                    if match:
                        tool_name = match.group(1)
                        logger.debug(
                            f"Potential tool start tag found: '{tool_name}' at index {match.start()}")
                        if tool_name in TOOL_MODEL_MAP:
                            start_index = match.start()
                            # Yield any preceding plain text
                            preceding_text = buffer[:start_index]
                            if preceding_text:
                                plain_text_buffer += preceding_text
                                logger.debug(
                                    f"Yielding preceding plain text: '{plain_text_buffer}'")
                                yield PlainTextOutput(text=plain_text_buffer)
                                plain_text_buffer = ""

                            # Keep the start tag and everything after it
                            buffer = buffer[start_index:]
                            in_tool_block = True
                            current_tool_tag = tool_name
                            logger.debug(
                                f"Entering tool block: '{current_tool_tag}', Buffer: '{buffer}'")
                            # Continue loop to check for end tag immediately
                        else:
                            # Not a recognized tool tag, treat up to the end of the match as plain text
                            plain_text_buffer += buffer[:match.end()]
                            buffer = buffer[match.end():]
                            logger.debug(
                                f"Tag '{tool_name}' not in TOOL_MODEL_MAP. Treating as plain text. Buffer: '{buffer}'")
                            # Continue loop to search for next potential tag in the remaining buffer

                    else:
                        # No tool start tag found in the current buffer
                        # Keep the last part of the buffer in case a tag spans chunks
                        # Keep last 50 chars as a safety margin
                        split_point = max(0, len(buffer) - 50)
                        plain_text_buffer += buffer[:split_point]
                        buffer = buffer[split_point:]
                        logger.debug(
                            f"No tool start tag found. Accumulating plain text. Buffer: '{buffer}'")
                        break  # Need more chunks

                if in_tool_block:
                    # Try to find the end of the current tool block
                    end_tag = f"</{current_tool_tag}>"
                    end_index = buffer.find(end_tag)
                    logger.debug(
                        f"Searching for end tag: '{end_tag}' in Buffer: '{buffer}'")

                    if end_index != -1:
                        tool_block_end_index = end_index + len(end_tag)
                        tool_xml = buffer[:tool_block_end_index]
                        # Consume the tool block
                        buffer = buffer[tool_block_end_index:]
                        logger.debug(
                            f"Found end tag. Tool XML: '{tool_xml}', Remaining Buffer: '{buffer}'")

                        try:
                            # Parse the XML-like tool block
                            # Ensure the root tag matches the expected tool tag
                            if not tool_xml.startswith(f"<{current_tool_tag}>"):
                                raise ET.ParseError(
                                    "Root tag mismatch or malformed XML start.")

                            root = ET.fromstring(tool_xml)
                            if root.tag != current_tool_tag:
                                raise ET.ParseError(
                                    f"Root tag '{root.tag}' does not match expected '{current_tool_tag}'")

                            params = {}
                            # Handle multi-line content within tags correctly
                            for child in root:
                                params[child.tag] = child.text if child.text is not None else ""
                                # If there's tail text immediately after the child open tag (rare but possible in mixed content)
                                # if child.tail and child.tail.strip():
                                #     params[child.tag] += child.tail.strip() # Append tail text if relevant

                            logger.debug(
                                f"Parsing tool '{current_tool_tag}' with params: {params}")
                            tool_model = TOOL_MODEL_MAP[current_tool_tag]
                            yield tool_model(**params)
                            logger.debug(
                                f"Yielded tool model: {current_tool_tag}")

                        except ET.ParseError as e:
                            logger.error(
                                f"Failed to parse tool XML: {tool_xml}. Error: {e}")
                            # Fallback: yield the block as plain text
                            yield PlainTextOutput(text=tool_xml)
                        except Exception as e:
                            logger.error(
                                f"Failed to instantiate/validate tool model {current_tool_tag} with params: {params}. Error: {e}")
                            # Fallback: yield the block as plain text
                            yield PlainTextOutput(text=tool_xml)

                        in_tool_block = False
                        current_tool_tag = None
                        # Continue processing the rest of the buffer in the same iteration loop
                    else:
                        # End tag not found yet, need more chunks
                        logger.debug("End tag not found yet, need more data.")
                        break  # Break the inner loop to get the next chunk

        # After the generator is exhausted, yield any remaining plain text
        if plain_text_buffer:
            logger.debug(
                f"Yielding final accumulated plain text: '{plain_text_buffer}'")
            yield PlainTextOutput(text=plain_text_buffer)
        # Yield remaining buffer content if it wasn't part of an incomplete tool block
        if buffer and not in_tool_block:
            logger.debug(
                f"Yielding final remaining buffer content: '{buffer}'")
            yield PlainTextOutput(text=buffer)
        elif buffer and in_tool_block:
            logger.warning(
                f"Stream ended with incomplete tool block for '{current_tool_tag}': '{buffer}'")
            # Optionally yield the incomplete block as text
            yield PlainTextOutput(text=buffer)
