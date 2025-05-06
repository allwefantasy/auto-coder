"""
Default tools initialization module
Used to initialize and register default tools
"""
from typing import Dict, Type, List
from loguru import logger
import byzerllm
from .tool_registry import ToolRegistry
from .types import BaseTool, ToolDescription, ToolExample

# Import all tool classes
from .types import (
    ExecuteCommandTool, ReadFileTool, WriteToFileTool, ReplaceInFileTool,
    SearchFilesTool, ListFilesTool, AskFollowupQuestionTool, 
    AttemptCompletionTool, PlanModeRespondTool, UseMcpTool
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


# Tool description generators with byzerllm.prompt() decorators

class ToolsCaseGenerator:
    """
    提供 EDITING FILES 部分的文档说明。
    """
    @staticmethod
    def editing_files_doc() -> str:        
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
        return {}

class ToolDescriptionGenerators:
    @byzerllm.prompt()
    def execute_command_description(self) -> Dict:
        """
        Execute shell command
        """
        return {}
    
    @byzerllm.prompt()
    def execute_command_parameters(self) -> Dict:
        """
        command: The command to execute
        requires_approval: Whether user approval is required
        """
        return {}
    
    @byzerllm.prompt()
    def execute_command_usage(self) -> Dict:
        """
        Used to execute system commands, such as installing dependencies, starting services, etc.
        """
        return {}
    
    @byzerllm.prompt()
    def read_file_description(self) -> Dict:
        """
        Read file contents
        """
        return {}
    
    @byzerllm.prompt()
    def read_file_parameters(self) -> Dict:
        """
        path: File path
        """
        return {}
    
    @byzerllm.prompt()
    def read_file_usage(self) -> Dict:
        """
        Used to read the contents of a specified file
        """
        return {}
    
    @byzerllm.prompt()
    def write_to_file_description(self) -> Dict:
        """
        Write content to a file
        """
        return {}
    
    @byzerllm.prompt()
    def write_to_file_parameters(self) -> Dict:
        """
        path: File path
        content: Content to write
        """
        return {}
    
    @byzerllm.prompt()
    def write_to_file_usage(self) -> Dict:
        """
        Used to create a new file or overwrite existing file content
        """
        return {}
    
    @byzerllm.prompt()
    def replace_in_file_description(self) -> Dict:
        """
        Replace content in a file
        """
        return {}
    
    @byzerllm.prompt()
    def replace_in_file_parameters(self) -> Dict:
        """
        path: File path
        diff: Replacement difference
        """
        return {}
    
    @byzerllm.prompt()
    def replace_in_file_usage(self) -> Dict:
        """
        Used to make partial modifications to a file, rather than completely overwriting it
        """
        return {}
    
    @byzerllm.prompt()
    def search_files_description(self) -> Dict:
        """
        Search file contents
        """
        return {}
    
    @byzerllm.prompt()
    def search_files_parameters(self) -> Dict:
        """
        path: Search path
        regex: Regular expression
        file_pattern: File pattern
        """
        return {}
    
    @byzerllm.prompt()
    def search_files_usage(self) -> Dict:
        """
        Used to find file contents that meet conditions in the project
        """
        return {}
    
    @byzerllm.prompt()
    def list_files_description(self) -> Dict:
        """
        List directory contents
        """
        return {}
    
    @byzerllm.prompt()
    def list_files_parameters(self) -> Dict:
        """
        path: Directory path
        recursive: Whether to list recursively
        """
        return {}
    
    @byzerllm.prompt()
    def list_files_usage(self) -> Dict:
        """
        Used to list all files and subdirectories under a specified directory
        """
        return {}
    
    @byzerllm.prompt()
    def ask_followup_question_description(self) -> Dict:
        """
        Ask the user a question to gather additional information needed to complete the task.
        """
        return {}
    
    @byzerllm.prompt()
    def ask_followup_question_parameters(self) -> Dict:
        """
        question: The question to ask the user. This should be a clear, specific question that addresses the information you need.
        options: An array of 2-5 options for the user to choose from. Each option should be a string describing a possible answer.
        """
        return {}
    
    @byzerllm.prompt()
    def ask_followup_question_usage(self) -> Dict:
        """
        This tool should be used when you encounter ambiguities, need clarification, or require more details to proceed effectively. It allows for interactive problem-solving by enabling direct communication with the user.
        """
        return {}
    
    @byzerllm.prompt()
    def attempt_completion_description(self) -> Dict:
        """
        After each tool use, the user will respond with the result of that tool use. Once you've received the results of tool uses and can confirm that the task is complete, use this tool to present the result of your work to the user.
        """
        return {}
    
    @byzerllm.prompt()
    def attempt_completion_parameters(self) -> Dict:
        """
        result: The result of the task. Formulate this result in a way that is final and does not require further input from the user.
        command: A CLI command to execute to show a live demo of the result to the user.
        """
        return {}
    
    @byzerllm.prompt()
    def attempt_completion_usage(self) -> Dict:
        """
        The user may respond with feedback if they are not satisfied with the result, which you can use to make improvements and try again.
        """
        return {}
    
    @byzerllm.prompt()
    def plan_mode_respond_description(self) -> Dict:
        """
        Respond to the user's inquiry in an effort to plan a solution to the user's task.
        """
        return {}
    
    @byzerllm.prompt()
    def plan_mode_respond_parameters(self) -> Dict:
        """
        response: The response to provide to the user. Do not try to use tools in this parameter, this is simply a chat response.
        options: An array of 2-5 options for the user to choose from. Each option should be a string describing a possible choice or path forward in the planning process.
        """
        return {}
    
    @byzerllm.prompt()
    def plan_mode_respond_usage(self) -> Dict:
        """
        This tool should be used when you need to provide a response to a question or statement from the user about how you plan to accomplish the task. This tool is only available in PLAN MODE.
        """
        return {}
    
    @byzerllm.prompt()
    def use_mcp_tool_description(self) -> Dict:
        """
        Request to execute a tool via the Model Context Protocol (MCP) server.
        """
        return {}
    
    @byzerllm.prompt()
    def use_mcp_tool_parameters(self) -> Dict:
        """
        server_name: The name of the MCP server to use. If not provided, the tool will automatically choose the best server based on the query.
        tool_name: The name of the tool to execute. If not provided, the tool will automatically choose the best tool in the selected server based on the query.
        query: The query to pass to the tool.
        """
        return {}
    
    @byzerllm.prompt()
    def use_mcp_tool_usage(self) -> Dict:
        """
        Use this when you need to execute a tool that is not natively supported by the agentic edit tools.
        """
        return {}

# Initialize tool description generators
tool_desc_gen = ToolDescriptionGenerators()

# Default tool descriptions
DEFAULT_TOOL_DESCRIPTIONS = {
    "execute_command": ToolDescription(
        description=tool_desc_gen.execute_command_description.prompt(),
        parameters=tool_desc_gen.execute_command_parameters.prompt(),
        usage=tool_desc_gen.execute_command_usage.prompt()
    ),
    "read_file": ToolDescription(
        description=tool_desc_gen.read_file_description.prompt(),
        parameters=tool_desc_gen.read_file_parameters.prompt(),
        usage=tool_desc_gen.read_file_usage.prompt()
    ),
    "write_to_file": ToolDescription(
        description=tool_desc_gen.write_to_file_description.prompt(),
        parameters=tool_desc_gen.write_to_file_parameters.prompt(),
        usage=tool_desc_gen.write_to_file_usage.prompt()
    ),
    "replace_in_file": ToolDescription(
        description=tool_desc_gen.replace_in_file_description.prompt(),
        parameters=tool_desc_gen.replace_in_file_parameters.prompt(),
        usage=tool_desc_gen.replace_in_file_usage.prompt()
    ),
    "search_files": ToolDescription(
        description=tool_desc_gen.search_files_description.prompt(),
        parameters=tool_desc_gen.search_files_parameters.prompt(),
        usage=tool_desc_gen.search_files_usage.prompt()
    ),
    "list_files": ToolDescription(
        description=tool_desc_gen.list_files_description.prompt(),
        parameters=tool_desc_gen.list_files_parameters.prompt(),
        usage=tool_desc_gen.list_files_usage.prompt()
    ),
    "ask_followup_question": ToolDescription(
        description=tool_desc_gen.ask_followup_question_description.prompt(),
        parameters=tool_desc_gen.ask_followup_question_parameters.prompt(),
        usage=tool_desc_gen.ask_followup_question_usage.prompt()
    ),
    "attempt_completion": ToolDescription(
        description=tool_desc_gen.attempt_completion_description.prompt(),
        parameters=tool_desc_gen.attempt_completion_parameters.prompt(),
        usage=tool_desc_gen.attempt_completion_usage.prompt()
    ),
    "plan_mode_respond": ToolDescription(
        description=tool_desc_gen.plan_mode_respond_description.prompt(),
        parameters=tool_desc_gen.plan_mode_respond_parameters.prompt(),
        usage=tool_desc_gen.plan_mode_respond_usage.prompt()
    ),
    "use_mcp_tool": ToolDescription(
        description=tool_desc_gen.use_mcp_tool_description.prompt(),
        parameters=tool_desc_gen.use_mcp_tool_parameters.prompt(),
        usage=tool_desc_gen.use_mcp_tool_usage.prompt()
    ),
}

# Tool example generators with byzerllm.prompt() decorators
class ToolExampleGenerators:
    @byzerllm.prompt()
    def execute_command_example(self) -> Dict:
        """
        <execute_command>
        <command>npm run dev</command>
        <requires_approval>false</requires_approval>
        </execute_command>
        """
        return {}
    
    @byzerllm.prompt()
    def read_file_example(self) -> Dict:
        """
        <read_file>
        <path>src/main.js</path>
        </read_file>
        """
        return {}
    
    @byzerllm.prompt()
    def write_to_file_example(self) -> Dict:
        """
        <write_to_file>
        <path>research/search-plan.md</path>
        <content>
        # Research Plan        

        ## Objective
        Investigate the latest developments in quantum computing algorithms

        ## Search Strategy
        1. Start with review papers from the last 2 years
        2. Focus specifically on quantum machine learning algorithms
        3. Identify key researchers and follow citation trails

        ## Expected Timeline
        - Day 1-2: Broad overview of the field
        - Day 3-5: Deep dive into specific algorithms
        - Day 6-7: Synthesis and final report preparation
        </content>
        </write_to_file>
        """
        return {}
    
    @byzerllm.prompt()
    def replace_in_file_example(self) -> Dict:
        """
        <replace_in_file>
        <path>research/findings.md</path>
        <diff>
        <<<<<<< SEARCH
        ## Initial Observations
        - Quantum computing shows promise in cryptography
        - Current hardware limitations remain significant
        =======
        ## Initial Observations
        - Quantum computing shows promise in cryptography and machine learning
        - Current hardware limitations remain significant
        - Recent advances in error correction are promising
        >>>>>>> REPLACE

        <<<<<<< SEARCH
        ## Next Steps
        - Examine quantum error correction methods
        =======
        ## Next Steps
        - Examine quantum error correction methods in detail
        - Investigate industry implementations
        >>>>>>> REPLACE
        </diff>
        </replace_in_file>
        """
        return {}
    
    @byzerllm.prompt()
    def search_files_example(self) -> Dict:
        """
        <search_files>
        <path>src</path>
        <regex>function\\s+main</regex>
        <file_pattern>*.js</file_pattern>
        </search_files>
        """
        return {}
    
    @byzerllm.prompt()
    def list_files_example(self) -> Dict:
        """
        <list_files>
        <path>src</path>
        <recursive>true</recursive>
        </list_files>
        """
        return {}
    
    @byzerllm.prompt()
    def ask_followup_question_example(self) -> Dict:
        """
        <ask_followup_question>
        <question>Your question here</question>
        <options>
        Array of options here (optional), e.g. ["Option 1", "Option 2", "Option 3"]
        </options>
        </ask_followup_question>
        """
        return {}
    
    @byzerllm.prompt()
    def attempt_completion_example(self) -> Dict:
        """
        <attempt_completion>
        <result>
        Your final result description here
        </result>
        <command>Command to demonstrate result (optional)</command>
        </attempt_completion>
        """
        return {}
    
    @byzerllm.prompt()
    def plan_mode_respond_example(self) -> Dict:
        """
        <plan_mode_respond>
        <response>Your response here</response>
        <options>
        Array of options here (optional), e.g. ["Option 1", "Option 2", "Option 3"]
        </options>
        </plan_mode_respond>
        """
        return {}
    
    @byzerllm.prompt()
    def use_mcp_tool_example(self) -> Dict:
        """
        <use_mcp_tool>
        <server_name>github</server_name>
        <tool_name>create_issue</tool_name>
        <query>ower is octocat, repo is hello-world, title is Found a bug, body is I'm having a problem with this. labels is "bug" and "help wanted",assignees is "octocat"</query>        
        </use_mcp_tool>
        """
        return {}

# Initialize tool example generators
tool_examples_gen = ToolExampleGenerators()

# Default tool examples
DEFAULT_TOOL_EXAMPLES = {
    "execute_command": ToolExample(
        title="Example of executing a command",
        body=tool_examples_gen.execute_command_example.prompt()
    ),
    "read_file": ToolExample(
        title="Example of reading a file",
        body=tool_examples_gen.read_file_example.prompt()
    ),
    "write_to_file": ToolExample(
        title="Example of writing to a file",
        body=tool_examples_gen.write_to_file_example.prompt()
    ),
    "replace_in_file": ToolExample(
        title="Example of replacing content in a file",
        body=tool_examples_gen.replace_in_file_example.prompt()
    ),
    "search_files": ToolExample(
        title="Example of searching files",
        body=tool_examples_gen.search_files_example.prompt()
    ),
    "list_files": ToolExample(
        title="Example of listing files",
        body=tool_examples_gen.list_files_example.prompt()
    ),
    "ask_followup_question": ToolExample(
        title="Example of asking a followup question",
        body=tool_examples_gen.ask_followup_question_example.prompt()
    ),
    "attempt_completion": ToolExample(
        title="Example of completing a task",
        body=tool_examples_gen.attempt_completion_example.prompt()
    ),
    "plan_mode_respond": ToolExample(
        title="Example of responding in plan mode",
        body=tool_examples_gen.plan_mode_respond_example.prompt()
    ),
    "use_mcp_tool": ToolExample(
        title="Example of using an MCP tool",
        body=tool_examples_gen.use_mcp_tool_example.prompt()
    ),
}




# 定义默认工具用例文档
DEFAULT_TOOLS_CASE_DOC = {
    "editing_files": {
        "tools": ["replace_in_file", "write_to_file"],
        "doc": ToolsCaseGenerator.editing_files_doc()
    }
}


# 统一的工具定义数据结构
DEFAULT_TOOLS = {
    "execute_command": {
        "tool_cls": ExecuteCommandTool,
        "resolver_cls": ExecuteCommandToolResolver,
        "description": ToolDescription(
            description=tool_desc_gen.execute_command_description.prompt(),
            parameters=tool_desc_gen.execute_command_parameters.prompt(),
            usage=tool_desc_gen.execute_command_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of executing a command",
            body=tool_examples_gen.execute_command_example.prompt()
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
            description=tool_desc_gen.read_file_description.prompt(),
            parameters=tool_desc_gen.read_file_parameters.prompt(),
            usage=tool_desc_gen.read_file_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of reading a file",
            body=tool_examples_gen.read_file_example.prompt()
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
            description=tool_desc_gen.write_to_file_description.prompt(),
            parameters=tool_desc_gen.write_to_file_parameters.prompt(),
            usage=tool_desc_gen.write_to_file_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of writing to a file",
            body=tool_examples_gen.write_to_file_example.prompt()
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
            description=tool_desc_gen.replace_in_file_description.prompt(),
            parameters=tool_desc_gen.replace_in_file_parameters.prompt(),
            usage=tool_desc_gen.replace_in_file_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of replacing content in a file",
            body=tool_examples_gen.replace_in_file_example.prompt()
        ),
        "use_guideline": "",
        "category": "file_operation",
        "is_default": True,
        "case_docs": ["editing_files"]
    },
    "search_files": {
        "tool_cls": SearchFilesTool,
        "resolver_cls": SearchFilesToolResolver,
        "description": ToolDescription(
            description=tool_desc_gen.search_files_description.prompt(),
            parameters=tool_desc_gen.search_files_parameters.prompt(),
            usage=tool_desc_gen.search_files_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of searching files",
            body=tool_examples_gen.search_files_example.prompt()
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
            description=tool_desc_gen.list_files_description.prompt(),
            parameters=tool_desc_gen.list_files_parameters.prompt(),
            usage=tool_desc_gen.list_files_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of listing files",
            body=tool_examples_gen.list_files_example.prompt()
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
            description=tool_desc_gen.ask_followup_question_description.prompt(),
            parameters=tool_desc_gen.ask_followup_question_parameters.prompt(),
            usage=tool_desc_gen.ask_followup_question_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of asking a followup question",
            body=tool_examples_gen.ask_followup_question_example.prompt()
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
            description=tool_desc_gen.attempt_completion_description.prompt(),
            parameters=tool_desc_gen.attempt_completion_parameters.prompt(),
            usage=tool_desc_gen.attempt_completion_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of completing a task",
            body=tool_examples_gen.attempt_completion_example.prompt()
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
            description=tool_desc_gen.plan_mode_respond_description.prompt(),
            parameters=tool_desc_gen.plan_mode_respond_parameters.prompt(),
            usage=tool_desc_gen.plan_mode_respond_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of responding in plan mode",
            body=tool_examples_gen.plan_mode_respond_example.prompt()
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
            description=tool_desc_gen.use_mcp_tool_description.prompt(),
            parameters=tool_desc_gen.use_mcp_tool_parameters.prompt(),
            usage=tool_desc_gen.use_mcp_tool_usage.prompt()
        ),
        "example": ToolExample(
            title="Example of using an MCP tool",
            body=tool_examples_gen.use_mcp_tool_example.prompt()
        ),
        "use_guideline": "",
        "category": "external",
        "is_default": True,
        "case_docs": []
    }
}

def register_default_tools_case_doc():
    """
    注册默认工具用例文档
    """
    # 获取所有已注册的工具
    registered_tools = set(ToolRegistry.get_all_registered_tools())
    
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
            logger.info(f"成功注册用例文档 {case_name}, 有效工具: {', '.join(valid_tools)}")
        else:
            logger.warning(f"跳过注册用例文档 {case_name}, 因为没有有效工具")
    
    logger.info(f"处理了 {len(DEFAULT_TOOLS_CASE_DOC)} 个默认工具用例文档")

def register_default_tools():
    """
    Register all default tools
    """
    # 先使用统一的工具注册方法注册所有工具
    for tool_tag, tool_info in DEFAULT_TOOLS.items():
        ToolRegistry.register_unified_tool(tool_tag, tool_info)
    
    logger.info(f"Registered {len(DEFAULT_TOOLS)} default tools using unified registration")
    
    # 然后注册默认工具用例文档
    # 这样可以确保在注册用例文档时，所有工具已经注册完成
    register_default_tools_case_doc()

def get_registered_default_tools() -> List[str]:
    """
    Get the list of registered default tools
    
    Returns:
        List of default tool tags
    """
    return ToolRegistry.get_default_tools() 


