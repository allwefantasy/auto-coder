import os
import sys
import time
from typing import Iterator, Union, Generator
from autocoder.auto_coder_runner import load_tokenizer, configure_logger
from autocoder.common import AutoCoderArgs, SourceCode, SourceCodeList
from autocoder.utils.llms import get_single_llm
from autocoder.agent.agentic_edit import AgenticEdit, MemoryConfig
from autocoder.agent.agentic_edit_types import (
    AgenticEditRequest,
    LLMOutputEvent, LLMThinkingEvent, ToolCallEvent,
    ToolResultEvent, CompletionEvent, ErrorEvent
)
from autocoder.rag.token_counter import count_tokens
from autocoder.helper.project_creator import ProjectCreator
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown

configure_logger() 

def file_to_source_code(file_path: str) -> SourceCode:
    """Converts a file to a SourceCode object."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        return SourceCode(module_name=file_path, source_code=content, tokens=count_tokens(content))
    except Exception as e:
        logger.warning(f"Could not read file {file_path}: {e}")
        return None

def get_source_code_list(project_dir: str) -> SourceCodeList:
    """Gets a list of SourceCode objects for all Python files in the project."""
    source_codes = []
    abs_project_dir = os.path.abspath(project_dir)
    logger.info(f"Scanning for source files in: {abs_project_dir}")
    for root, _, files in os.walk(abs_project_dir):
        for file in files:
            # Simple check for common code extensions, can be expanded
            if file.endswith(('.py', '.js', '.ts', '.tsx', '.java', '.go', '.rs', '.html', '.css', '.scss', '.md')):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, abs_project_dir)
                sc = file_to_source_code(file_path)
                if sc:
                    sc.module_name = rel_path # Use relative path for module name
                    source_codes.append(sc)

    logger.info(f"Found {len(source_codes)} source files.")
    return SourceCodeList(sources=source_codes)

# --- Configuration ---
MODEL_NAME = "quasar-alpha" # Or choose your preferred model
PROJECT_NAME = "test_project"
USER_QUERY = "给计算器添加乘法和除法功能，并为所有方法添加类型提示和文档字符串。"
# --- End Configuration ---

# 1. Load tokenizer (Important for token counting if needed)
load_tokenizer()

# 2. Create or find the example project
project_dir = os.path.abspath(PROJECT_NAME)
if not os.path.exists(project_dir):
    logger.info(f"Creating example project: {project_dir}")
    creator = ProjectCreator(
        project_name=PROJECT_NAME,
        project_type="python",
        query="Create a simple calculator class with add and subtract methods."
    )
    project_dir = creator.create_project()
    logger.info(f"Created example project at: {project_dir}")
else:
    logger.info(f"Using existing project directory: {project_dir}")

# 3. Get source code from the project
source_code_list = get_source_code_list(project_dir)
if not source_code_list.sources:
    logger.error(f"No source code files found in {project_dir}. Exiting.")
    sys.exit(1)

# 4. Change working directory to project root
os.chdir(project_dir)
logger.info(f"Changed working directory to: {os.getcwd()}")


# 5. Setup AutoCoderArgs
args = AutoCoderArgs(
    source_dir=".", # Use relative path now
    model=MODEL_NAME,
    product_mode="lite",
    # target_file and file are not strictly needed for agentic edit but kept for compatibility
    target_file=os.path.join(project_dir, "output.txt"),
    file=os.path.join(project_dir, "actions", "placeholder_action.yml")
)

# 6. Get LLM instance
llm = get_single_llm(args.model, product_mode=args.product_mode)
if not llm:
     logger.error(f"Failed to initialize LLM: {args.model}. Please check configuration/API keys.")
     sys.exit(1)


# 7. Setup MemoryConfig (dummy for this example)
def dummy_save_memory(memory: dict):
    # In a real scenario, this would persist memory
    pass
memory_config = MemoryConfig(memory={}, save_memory_func=dummy_save_memory)

# 8. Instantiate AgenticEdit
agentic_editor = AgenticEdit(
    llm=llm,
    conversation_history=[],
    files=source_code_list,
    args=args,
    memory_config=memory_config,
    # command_config is optional
)

# 9. Prepare the request
request = AgenticEditRequest(user_input=USER_QUERY)

# 10. Initialize Rich Console
console = Console()
console.rule(f"[bold cyan]Starting Agentic Edit: {PROJECT_NAME}[/]")
console.print(Panel(f"[bold]User Query:[/bold]\n{USER_QUERY}", title="Objective", border_style="blue"))

# 11. Run the agent and display output streamingly
try:
    event_stream = agentic_editor.analyze(request)
    for event in event_stream:
        if isinstance(event, LLMThinkingEvent):
            console.print(event.text,end="")
        elif isinstance(event, LLMOutputEvent):
            # Print regular LLM output, potentially as markdown
            console.print(event.text, end="") # Less prominent style
        elif isinstance(event, ToolCallEvent):
            # Display the tool call XML using Syntax highlighting
            syntax = Syntax(event.tool_xml, "xml", theme="default", line_numbers=False)
            console.print(Panel(syntax, title=f"🛠️ Tool Call: {type(event.tool).__name__}", border_style="blue", title_align="left"))
        elif isinstance(event, ToolResultEvent):
            result = event.result
            title = f"✅ Tool Result: {event.tool_name}" if result.success else f"❌ Tool Result: {event.tool_name}"
            border_style = "green" if result.success else "red"
            content = f"[bold]Status:[/bold] {'Success' if result.success else 'Failure'}\n"
            content += f"[bold]Message:[/bold] {result.message}\n"
            if result.content is not None:
                 # Try to format content nicely (e.g., JSON, code, or just string)
                 content_str = ""
                 if isinstance(result.content, (dict, list)):
                     try:
                         import json
                         content_str = json.dumps(result.content, indent=2, ensure_ascii=False)
                         syntax = Syntax(content_str, "json", theme="default", line_numbers=False)
                         content += f"[bold]Content:[/bold]\n"
                         console.print(Panel(content, title=title, border_style=border_style, title_align="left"))
                         console.print(syntax) # Print syntax separately for better formatting
                         continue # Skip default content print
                     except Exception:
                         content_str = str(result.content) # Fallback to string
                 elif isinstance(result.content, str) and ('\n' in result.content or result.content.strip().startswith('<')):
                     # Heuristic for code or XML/HTML
                     lexer = "python" if event.tool_name == "ReadFileTool" and ".py" in str(event.result.message) else "markup" # Basic guess
                     syntax = Syntax(result.content, lexer, theme="default", line_numbers=True)
                     content += f"[bold]Content:[/bold]\n"
                     console.print(Panel(content, title=title, border_style=border_style, title_align="left"))
                     console.print(syntax)
                     continue # Skip default content print
                 else:
                    content_str = str(result.content)

                 content += f"[bold]Content:[/bold]\n{content_str}"

            console.print(Panel(content, title=title, border_style=border_style, title_align="left"))

        elif isinstance(event, CompletionEvent):
            syntax = Syntax(event.completion_xml, "xml", theme="default", line_numbers=False)
            console.print(Panel(syntax, title="🏁 Attempt Completion", border_style="green", title_align="left"))
            # Optionally print the result text from the completion object
            console.print(Panel(f"[bold]Final Result:[/bold]\n{event.completion.result}", title="Summary", border_style="green"))
            if event.completion.command:
                console.print(f"[dim]Suggested command:[/dim] [bold cyan]{event.completion.command}[/]")
        elif isinstance(event, ErrorEvent):
            console.print(Panel(f"[bold red]Error:[/bold red] {event.message}", title="🔥 Error", border_style="red", title_align="left"))

        time.sleep(0.1) # Small delay for better visual flow

except Exception as e:
    logger.exception("An unexpected error occurred during agent execution:")
    console.print(Panel(f"[bold red]FATAL ERROR:[/bold red]\n{str(e)}", title="🔥 System Error", border_style="red"))
finally:
    console.rule("[bold cyan]Agentic Edit Finished[/]")
