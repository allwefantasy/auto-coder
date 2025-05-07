import locale
from byzerllm.utils import format_str_jinja2

MESSAGES = {
    "auto_command_analyzing": {
        "en": "Analyzing Command Request",
        "zh": "正在分析命令请求"
    },
    # run_in_terminal方法的国际化文本
    "agent_start": {
        "en": "[bold cyan]Starting Agent: {{ project_name }}[/]",
        "zh": "[bold cyan]启动代理: {{ project_name }}[/]"
    },
    "user_input": {
        "en": "[bold]User Input:[/bold]\n{{ input }}",
        "zh": "[bold]用户输入:[/bold]\n{{ input }}"
    },
    "user_input_title": {
        "en": "Objective",
        "zh": "目标"
    },
    "token_usage_log": {
        "en": "Token Usage: Model={{ model }}, Input Tokens={{ input_tokens }}, Output Tokens={{ output_tokens }}, Input Cost=${{ input_cost }}, Output Cost=${{ output_cost }}",
        "zh": "Token使用情况: 模型={{ model }}, 输入Token={{ input_tokens }}, 输出Token={{ output_tokens }}, 输入成本=${{ input_cost }}, 输出成本=${{ output_cost }}"
    },
    "tool_operation_title": {
        "en": "🛠️ Operation: {{ tool_name }}",
        "zh": "🛠️ 操作: {{ tool_name }}"
    },
    "tool_result_success_title": {
        "en": "✅ Tool Result: {{ tool_name }}",
        "zh": "✅ 工具结果: {{ tool_name }}"
    },
    "tool_result_failure_title": {
        "en": "❌ Tool Result: {{ tool_name }}",
        "zh": "❌ 工具结果: {{ tool_name }}"
    },
    "status": {
        "en": "[bold]Status:[/bold] {{ status }}",
        "zh": "[bold]状态:[/bold] {{ status }}"
    },
    "message": {
        "en": "[bold]Message:[/bold] {{ message }}",
        "zh": "[bold]消息:[/bold] {{ message }}"
    },
    "success_status": {
        "en": "Success",
        "zh": "成功"
    },
    "failure_status": {
        "en": "Failure",
        "zh": "失败"
    },
    "format_tool_error": {
        "en": "Error formatting tool result content: {{ error }}",
        "zh": "格式化工具结果内容时出错: {{ error }}"
    },
    "completion_title": {
        "en": "🏁 Task Completed",
        "zh": "🏁 任务完成"
    },
    "suggested_command": {
        "en": "[dim]Suggested Command:[/dim] [bold cyan]{{ command }}[/]",
        "zh": "[dim]建议命令:[/dim] [bold cyan]{{ command }}[/]"
    },
    "error_title": {
        "en": "🔥 Error",
        "zh": "🔥 错误"
    },
    "error_content": {
        "en": "[bold red]Error:[/bold red] {{ message }}",
        "zh": "[bold red]错误:[/bold red] {{ message }}"
    },
    "fatal_error_title": {
        "en": "🔥 System Error",
        "zh": "🔥 系统错误"
    },
    "fatal_error_content": {
        "en": "[bold red]Fatal Error:[/bold red]\n{{ error }}",
        "zh": "[bold red]致命错误:[/bold red]\n{{ error }}"
    },
    "shadow_merge_error": {
        "en": "Error merging shadow changes to project: {{ error }}",
        "zh": "合并影子更改到项目时出错: {{ error }}"
    },
    "agent_execution_complete": {
        "en": "[bold cyan]Agent Execution Completed[/]",
        "zh": "[bold cyan]代理执行完成[/]"
    },
    "unexpected_error": {
        "en": "Unexpected error during agent execution:",
        "zh": "代理执行过程中发生意外错误:"
    }
}


def get_system_language():
    try:
        return locale.getdefaultlocale()[0][:2]
    except:
        return "en"


def get_message(key):
    lang = get_system_language()
    if key in MESSAGES:
        return MESSAGES[key].get(lang, MESSAGES[key].get("en", ""))
    return ""


def get_message_with_format(msg_key: str, **kwargs):
    return format_str_jinja2(get_message(msg_key), **kwargs)
