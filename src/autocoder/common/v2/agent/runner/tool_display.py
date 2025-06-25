"""
工具显示模块，提供格式化工具调用信息的功能。

这个模块负责生成用户友好的、国际化的工具调用显示信息，
主要用于终端运行器中展示工具调用的详细信息。
"""

import json
from typing import Dict, Callable, Type

from autocoder.common.auto_coder_lang import get_system_language, format_str_jinja2
from autocoder.common.v2.agent.agentic_edit_types import (
    BaseTool,
    ReadFileTool, WriteToFileTool, ReplaceInFileTool, ExecuteCommandTool,
    ListFilesTool, SearchFilesTool, ListCodeDefinitionNamesTool,
    AskFollowupQuestionTool, UseMcpTool, AttemptCompletionTool
)

# Define message templates for each tool in English and Chinese
TOOL_DISPLAY_MESSAGES: Dict[Type[BaseTool], Dict[str, str]] = {
    ReadFileTool: {
        "en": "AutoCoder wants to read this file:\n[bold cyan]{{ path }}[/]",
        "zh": "AutoCoder 想要读取此文件：\n[bold cyan]{{ path }}[/]"
    },
    WriteToFileTool: {
        "en": (
            "AutoCoder wants to write to this file:\n[bold cyan]{{ path }}[/]\n\n"
            "[dim]Content Snippet:[/dim]\n{{ content_snippet }}{{ ellipsis }}"
        ),
        "zh": (
            "AutoCoder 想要写入此文件：\n[bold cyan]{{ path }}[/]\n\n"
            "[dim]内容片段：[/dim]\n{{ content_snippet }}{{ ellipsis }}"
        )
    },
    ReplaceInFileTool: {
        "en": (
            "AutoCoder wants to replace content in this file:\n[bold cyan]{{ path }}[/]\n\n"
            "[dim]Diff Snippet:[/dim]\n{{ diff_snippet }}{{ ellipsis }}"
        ),
        "zh": (
            "AutoCoder 想要替换此文件中的内容：\n[bold cyan]{{ path }}[/]\n\n"
            "[dim]差异片段：[/dim]\n{{ diff_snippet }}{{ ellipsis }}"
        )
    },
    ExecuteCommandTool: {
        "en": (
            "AutoCoder wants to execute this command:\n[bold yellow]{{ command }}[/]\n"
            "[dim](Requires Approval: {{ requires_approval }})[/]"
        ),
        "zh": (
            "AutoCoder 想要执行此命令：\n[bold yellow]{{ command }}[/]\n"
            "[dim](需要批准：{{ requires_approval }})[/]"
        )
    },
    ListFilesTool: {
        "en": (
            "AutoCoder wants to list files in:\n[bold green]{{ path }}[/] "
            "{{ recursive_text }}"
        ),
        "zh": (
            "AutoCoder 想要列出此目录中的文件：\n[bold green]{{ path }}[/] "
            "{{ recursive_text }}"
        )
    },
    SearchFilesTool: {
        "en": (
            "AutoCoder wants to search files in:\n[bold green]{{ path }}[/]\n"
            "[dim]File Pattern:[/dim] [yellow]{{ file_pattern }}[/]\n"
            "[dim]Regex:[/dim] [yellow]{{ regex }}[/]"
        ),
        "zh": (
            "AutoCoder 想要在此目录中搜索文件：\n[bold green]{{ path }}[/]\n"
            "[dim]文件模式：[/dim] [yellow]{{ file_pattern }}[/]\n"
            "[dim]正则表达式：[/dim] [yellow]{{ regex }}[/]"
        )
    },
    ListCodeDefinitionNamesTool: {
        "en": "AutoCoder wants to list definitions in:\n[bold green]{{ path }}[/]",
        "zh": "AutoCoder 想要列出此路径中的定义：\n[bold green]{{ path }}[/]"
    },
    AskFollowupQuestionTool: {
        "en": (
            "AutoCoder is asking a question:\n[bold magenta]{{ question }}[/]\n"
            "{{ options_text }}"
        ),
        "zh": (
            "AutoCoder 正在提问：\n[bold magenta]{{ question }}[/]\n"
            "{{ options_text }}"
        )
    },
    UseMcpTool: {
        "en": (
            "AutoCoder wants to use an MCP tool:\n"
            "[dim]Server:[/dim] [blue]{{ server_name }}[/]\n"
            "[dim]Tool:[/dim] [blue]{{ tool_name }}[/]\n"
            "[dim]Args:[/dim] {{ arguments_snippet }}{{ ellipsis }}"
        ),
        "zh": (
            "AutoCoder 想要使用 MCP 工具：\n"
            "[dim]服务器：[/dim] [blue]{{ server_name }}[/]\n"
            "[dim]工具：[/dim] [blue]{{ tool_name }}[/]\n"
            "[dim]参数：[/dim] {{ arguments_snippet }}{{ ellipsis }}"
        )
    }
}

def get_tool_display_message(tool: BaseTool) -> str:
    """
    生成工具调用的用户友好、国际化的字符串表示。

    Args:
        tool: 工具实例（Pydantic模型）。

    Returns:
        用于在终端中显示的格式化字符串。
    """
    lang = get_system_language()
    tool_type = type(tool)

    if tool_type not in TOOL_DISPLAY_MESSAGES:
        # 未知工具的回退处理
        return f"未知工具类型: {tool_type.__name__}\n数据: {tool.model_dump_json(indent=2)}"

    templates = TOOL_DISPLAY_MESSAGES[tool_type]
    template = templates.get(lang, templates.get("en", "工具显示模板未找到")) # 回退到英文

    # 准备特定于每种工具类型的上下文
    context = {}
    if isinstance(tool, ReadFileTool):
        context = {"path": tool.path}
    elif isinstance(tool, WriteToFileTool):
        snippet = tool.content[:150]
        context = {
            "path": tool.path,
            "content_snippet": snippet,
            "ellipsis": '...' if len(tool.content) > 150 else ''
        }
    elif isinstance(tool, ReplaceInFileTool):
        snippet = tool.diff
        context = {
            "path": tool.path,
            "diff_snippet": snippet,
            "ellipsis": ''
        }
    elif isinstance(tool, ExecuteCommandTool):
        context = {"command": tool.command, "requires_approval": tool.requires_approval}
    elif isinstance(tool, ListFilesTool):
        rec_text_en = '(Recursively)' if tool.recursive else '(Top Level)'
        rec_text_zh = '（递归）' if tool.recursive else '（顶层）'
        context = {
            "path": tool.path,
            "recursive_text": rec_text_zh if lang == 'zh' else rec_text_en
        }
    elif isinstance(tool, SearchFilesTool):
        context = {
            "path": tool.path,
            "file_pattern": tool.file_pattern or '*',
            "regex": tool.regex
        }
    elif isinstance(tool, ListCodeDefinitionNamesTool):
        context = {"path": tool.path}
    elif isinstance(tool, AskFollowupQuestionTool):
        options_text_en = ""
        options_text_zh = ""
        if tool.options:
            options_list_en = "\n".join([f"- {opt}" for opt in tool.options])
            options_list_zh = "\n".join([f"- {opt}" for opt in tool.options]) # 假设选项足够简单，不需要翻译
            options_text_en = f"[dim]Options:[/dim]\n{options_list_en}"
            options_text_zh = f"[dim]选项：[/dim]\n{options_list_zh}"
        context = {
            "question": tool.question,
            "options_text": options_text_zh if lang == 'zh' else options_text_en
        }
    elif isinstance(tool, UseMcpTool):
        args_str = tool.query
        snippet = args_str[:100]
        context = {
            "server_name": tool.server_name,
            "tool_name": tool.tool_name,
            "arguments_snippet": snippet,
            "ellipsis": '...' if len(args_str) > 100 else ''
        }    
    else:
        # 未专门处理的工具的通用上下文
        context = tool.model_dump()

    try:
        return format_str_jinja2(template, **context)
    except Exception as e:
        # 格式化错误时的回退处理
        return f"格式化 {tool_type.__name__} 的显示时出错: {e}\n模板: {template}\n上下文: {context}"
