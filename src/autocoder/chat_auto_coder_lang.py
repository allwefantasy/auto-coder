import locale
from byzerllm.utils import format_str_jinja2

MESSAGES = {
    "auto_command_analyzing": {
        "en": "Analyzing Command Request",
        "zh": "正在分析命令请求"
    },
    "mcp_remove_error": {
        "en": "Error removing MCP server: {{error}}",
        "zh": "移除 MCP 服务器时出错:{{error}}"
    },
    "mcp_remove_success": {
        "en": "Successfully removed MCP server: {{result}}",
        "zh": "成功移除 MCP 服务器：{{result}}"
    },
    "mcp_list_running_error": {
        "en": "Error listing running MCP servers: {{error}}",
        "zh": "列出运行中的 MCP 服务器时出错：{{error}}"
    },
    "mcp_list_running_title": {
        "en": "Running MCP servers:",
        "zh": "正在运行的 MCP 服务器："
    },
    "mcp_list_builtin_error": {
        "en": "Error listing builtin MCP servers: {{error}}",
        "zh": "列出内置 MCP 服务器时出错：{{error}}"
    },
    "mcp_list_builtin_title": {
        "en": "Available builtin MCP servers:",
        "zh": "可用的内置 MCP 服务器："
    },
    "mcp_refresh_error": {
        "en": "Error refreshing MCP servers: {{error}}",
        "zh": "刷新 MCP 服务器时出错：{{error}}"
    },
    "mcp_refresh_success": {
        "en": "Successfully refreshed MCP servers",
        "zh": "成功刷新 MCP 服务器"
    },
    "mcp_install_error": {
        "en": "Error installing MCP server: {{error}}",
        "zh": "安装 MCP 服务器时出错：{{error}}"
    },
    "mcp_install_success": {
        "en": "Successfully installed MCP server: {{result}}",
        "zh": "成功安装 MCP 服务器：{{result}}"
    },
    "mcp_query_empty": {
        "en": "Please enter your query.",
        "zh": "请输入您的查询。"
    },
    "mcp_error_title": {
        "en": "Error",
        "zh": "错误"
    },
    "mcp_response_title": {
        "en": "MCP Response",
        "zh": "MCP 响应"
    },
    "initializing": {
        "en": "🚀 Initializing system...",
        "zh": "🚀 正在初始化系统..."
    },
    "not_initialized": {
        "en": "The current directory is not initialized as an auto-coder project.",
        "zh": "当前目录未初始化为auto-coder项目。"
    },
    "init_prompt": {
        "en": "Do you want to initialize the project now? (y/n): ",
        "zh": "是否现在初始化项目？(y/n): "
    },
    "init_success": {
        "en": "Project initialized successfully.",
        "zh": "项目初始化成功。"
    },
    "init_fail": {
        "en": "Failed to initialize the project.",
        "zh": "项目初始化失败。"
    },
    "init_manual": {
        "en": "Please try manually: auto-coder init --source_dir .",
        "zh": "请尝试手动初始化：auto-coder init --source_dir ."
    },
    "exit_no_init": {
        "en": "Exiting without initialization.",
        "zh": "退出而不初始化。"
    },
    "created_dir": {
        "en": "Created directory: {{path}}",
        "zh": "创建目录：{{path}}"
    },
    "init_complete": {
        "en": "Project initialization completed.",
        "zh": "项目初始化完成。"
    },
    "checking_ray": {
        "en": "Checking Ray status...",
        "zh": "正在检查Ray状态..."
    },
    "ray_not_running": {
        "en": "Ray is not running. Starting Ray...",
        "zh": "Ray未运行。正在启动Ray..."
    },
    "ray_start_success": {
        "en": "Ray started successfully.",
        "zh": "Ray启动成功。"
    },
    "ray_start_fail": {
        "en": "Failed to start Ray. Please start it manually.",
        "zh": "Ray启动失败。请手动启动。"
    },
    "ray_running": {
        "en": "Ray is already running.",
        "zh": "Ray已经在运行。"
    },
    "checking_model": {
        "en": "Checking deepseek_chat model availability...",
        "zh": "正在检查deepseek_chat模型可用性..."
    },
    "model_available": {
        "en": "deepseek_chat model is available.",
        "zh": "deepseek_chat模型可用。"
    },
    "model_timeout": {
        "en": "Command timed out. deepseek_chat model might not be available.",
        "zh": "命令超时。deepseek_chat模型可能不可用。"
    },
    "model_error": {
        "en": "Error occurred while checking deepseek_chat model.",
        "zh": "检查deepseek_chat模型时出错。"
    },
    "model_not_available": {
        "en": "deepseek_chat model is not available.",
        "zh": "deepseek_chat模型不可用。"
    },
    "provider_selection": {
        "en": "Select a provider for deepseek_chat model:",
        "zh": "为deepseek_chat模型选择一个提供商："
    },
    "no_provider": {
        "en": "No provider selected. Exiting initialization.",
        "zh": "未选择提供商。退出初始化。"
    },
    "enter_api_key": {
        "en": "Please enter your API key（https://www.deepseek.com/）: ",
        "zh": "请输入您的API密钥（https://www.deepseek.com/）："
    },
    "deploying_model": {
        "en": "Deploying deepseek_chat model using {}...",
        "zh": "正在使用{}部署deepseek_chat模型..."
    },
    "deploy_complete": {
        "en": "Deployment completed.",
        "zh": "部署完成。"
    },
    "deploy_fail": {
        "en": "Deployment failed. Please try again or deploy manually.",
        "zh": "部署失败。请重试或手动部署。"
    },
    "validating_deploy": {
        "en": "Validating the deployment...",
        "zh": "正在验证部署..."
    },
    "validation_success": {
        "en": "Validation successful. deepseek_chat model is now available.",
        "zh": "验证成功。deepseek_chat模型现在可用。"
    },
    "validation_fail": {
        "en": "Validation failed. The model might not be deployed correctly.",
        "zh": "验证失败。模型可能未正确部署。"
    },
    "manual_start": {
        "en": "Please try to start the model manually using:",
        "zh": "请尝试使用以下命令手动启动模型："
    },
    "init_complete_final": {
        "en": "Initialization completed.",
        "zh": "初始化完成。"
    },
    "project_type_config": {
        "en": "Project Type Configuration",
        "zh": "项目类型配置"
    },
    "project_type_supports": {
        "en": "The project_type supports:",
        "zh": "项目类型支持："
    },
    "language_suffixes": {
        "en": "  - Language suffixes (e.g., .py, .java, .ts)",
        "zh": "  - 语言后缀（例如：.py, .java, .ts）"
    },
    "predefined_types": {
        "en": "  - Predefined types: py (Python), ts (TypeScript/JavaScript)",
        "zh": "  - 预定义类型：py（Python）, ts（TypeScript/JavaScript）"
    },
    "mixed_projects": {
        "en": "For mixed language projects, use comma-separated values.",
        "zh": "对于混合语言项目，使用逗号分隔的值。"
    },
    "examples": {
        "en": "Examples: '.java,.scala' or '.py,.ts'",
        "zh": "示例：'.java,.scala' 或 '.py,.ts'"
    },
    "default_type": {
        "en": "Default is 'py' if left empty.",
        "zh": "如果留空，默认为 'py'。"
    },
    "enter_project_type": {
        "en": "Enter the project type: ",
        "zh": "请输入项目类型："
    },
    "project_type_set": {
        "en": "Project type set to:",
        "zh": "项目类型设置为："
    },
    "using_default_type": {
        "en": "will automatically collect extensions of code file, otherwise default to 'py'",
        "zh": "使用默认项目类型，会自动查找代码代码相关的后缀名，如果项目为空，则默认为py"
    },
    "change_setting_later": {
        "en": "You can change this setting later using",
        "zh": "您可以稍后使用以下命令更改此设置"
    },
    "supported_commands": {
        "en": "Supported commands:",
        "zh": "支持的命令："
    },
    "commands": {
        "en": "Commands",
        "zh": "命令"
    },
    "description": {
        "en": "Description",
        "zh": "描述"
    },
    "add_files_desc": {
        "en": "Add files to the current session",
        "zh": "将文件添加到当前会话"
    },
    "remove_files_desc": {
        "en": "Remove files from the current session",
        "zh": "从当前会话中移除文件"
    },
    "chat_desc": {
        "en": "Chat with the AI about the current active files to get insights",
        "zh": "与AI聊天，获取关于当前活动文件的见解"
    },
    "coding_desc": {
        "en": "Request the AI to modify code based on requirements",
        "zh": "根据需求请求AI修改代码"
    },
    "ask_desc": {
        "en": "Ask the AI any questions or get insights about the current project, without modifying code",
        "zh": "向AI提问或获取关于当前项目的见解，不修改代码"
    },
    "summon_desc": {
        "en": "Summon the AI to perform complex tasks using the auto_tool agent",
        "zh": "召唤AI使用auto_tool代理执行复杂任务"
    },
    "revert_desc": {
        "en": "Revert commits from last coding chat",
        "zh": "撤销上次代码聊天的提交"
    },
    "conf_desc": {
        "en": "Set configuration. Use /conf project_type:<type> to set project type for indexing",
        "zh": "设置配置。使用 /conf project_type:<type> 设置索引的项目类型"
    },
    "index_query_desc": {
        "en": "Query the project index",
        "zh": "查询项目索引"
    },
    "index_build_desc": {
        "en": "Trigger building the project index",
        "zh": "触发构建项目索引"
    },
    "list_files_desc": {
        "en": "List all active files in the current session",
        "zh": "列出当前会话中的所有活动文件"
    },
    "help_desc": {
        "en": "Show this help message",
        "zh": "显示此帮助消息"
    },
    "exclude_dirs_desc": {
        "en": "Add directories to exclude from project",
        "zh": "添加要从项目中排除的目录"
    },
    "shell_desc": {
        "en": "Execute a shell command",
        "zh": "执行shell命令"
    },
    "index_export_success": {
        "en": "Successfully exported index to {{ path }}",
        "zh": "成功导出索引到 {{ path }}"
    },
    "index_export_fail": {
        "en": "Failed to export index to {{ path }}",
        "zh": "导出索引到 {{ path }} 失败"
    },
    "index_import_success": {
        "en": "Successfully imported index from {{ path }}",
        "zh": "成功从 {{ path }} 导入索引"
    },
    "index_import_fail": {
        "en": "Failed to import index from {{ path }}",
        "zh": "从 {{ path }} 导入索引失败"
    },
    "index_not_found": {
        "en": "Index file not found at {{ path }}",
        "zh": "在 {{ path }} 未找到索引文件"
    },
    "index_backup_success": {
        "en": "Backed up existing index to {{ path }}",
        "zh": "已备份现有索引到 {{ path }}"
    },
    "index_convert_path_fail": {
        "en": "Could not convert path {{ path }}",
        "zh": "无法转换路径 {{ path }}"
    },
    "index_error": {
        "en": "Error in index operation: {{ error }}",
        "zh": "索引操作出错：{{ error }}"
    },
    "voice_input_desc": {
        "en": "Convert voice input to text",
        "zh": "将语音输入转换为文本"
    },
    "mode_desc": {
        "en": "Switch input mode",
        "zh": "切换输入模式"
    },
    "conf_key": {
        "en": "Key",
        "zh": "键"
    },
    "conf_value": {
        "en": "Value",
        "zh": "值"
    },
    "conf_title": {
        "en": "Configuration Settings",
        "zh": "配置设置"
    },
    "conf_subtitle": {
        "en": "Use /conf <key>:<value> to modify these settings",
        "zh": "使用 /conf <key>:<value> 修改这些设置"
    },
    "lib_desc": {
        "en": "Manage libraries",
        "zh": "管理库"
    },
    "exit_desc": {
        "en": "Exit the program",
        "zh": "退出程序"
    },
    "design_desc": {
        "en": "Generate SVG image based on the provided description",
        "zh": "根据需求设计SVG图片"
    },
    "commit_desc": {
        "en": "Auto generate yaml file and commit changes based on user's manual changes",
        "zh": "根据用户人工修改的代码自动生成yaml文件并提交更改"
    },
    "models_desc": {
        "en": "Manage model configurations, only available in lite mode",
        "zh": "管理模型配置，仅在lite模式下可用"
    },
    "models_usage": {
        "en": "Usage: /models <command>\nAvailable subcommands:\n  /list - List all models\n  /add <name> <api_key> - Add a built-in model\n  /add_model - Add a custom model\n  /remove <name> - Remove a model\n  /input_price <name> <value> - Set model input price\n  /output_price <name> <value> - Set model output price\n  /speed <name> <value> - Set model speed\n  /speed-test - Test models speed\n  /speed-test-long - Test models speed with long context",
        "zh": "用法: /models <命令>\n可用的子命令:\n  /list - 列出所有模型\n  /add <名称> <API密钥> - 添加内置模型\n  /add_model - 添加自定义模型\n  /remove <名称> - 移除模型\n  /input_price <名称> <价格> - 设置模型输入价格\n  /output_price <名称> <价格> - 设置模型输出价格\n  /speed <名称> <速度> - 设置模型速度\n  /speed-test - 测试模型速度\n  /speed-test-long - 使用长文本上下文测试模型速度"
    },
    "models_added": {
        "en": "Added/Updated model '{{name}}' successfully.",
        "zh": "成功添加/更新模型 '{{name}}'。"
    },
    "models_add_failed": {
        "en": "Failed to add model '{{name}}'. Model not found in defaults.",
        "zh": "添加模型 '{{name}}' 失败。在默认模型中未找到该模型。"
    },
    "models_add_usage": {
        "en": "Usage: /models /add <name> <api_key> or\n/models /add <name> <model_type> <model_name> <base_url> <api_key_path> [description]",
        "zh": "用法: /models /add <name> <api_key> 或\n/models /add <name> <model_type> <model_name> <base_url> <api_key_path> [description]"
    },
    "models_add_model_params": {
        "en": "Please provide parameters in key=value format",
        "zh": "请提供 key=value 格式的参数"
    },
    "models_add_model_name_required": {
        "en": "'name' parameter is required",
        "zh": "缺少必需的 'name' 参数"
    },
    "models_add_model_exists": {
        "en": "Model '{{name}}' already exists.",
        "zh": "模型 '{{name}}' 已存在。"
    },
    "models_add_model_success": {
        "en": "Successfully added custom model: {{name}}",
        "zh": "成功添加自定义模型: {{name}}"
    },
    "models_add_model_remove": {
        "en": "Model '{{name}}' not found.",
        "zh": "找不到模型 '{{name}}'。"
    },
    "models_add_model_removed": {
        "en": "Removed model: {{name}}",
        "zh": "已移除模型: {{name}}"
    },
    "models_unknown_subcmd": {
        "en": "Unknown subcommand: {{subcmd}}",
        "zh": "未知的子命令: {{subcmd}}"
    },
    "models_input_price_updated": {
        "en": "Updated input price for model {{name}} to {{price}} M/token",
        "zh": "已更新模型 {{name}} 的输入价格为 {{price}} M/token"
    },
    "models_output_price_updated": {
        "en": "Updated output price for model {{name}} to {{price}} M/token",
        "zh": "已更新模型 {{name}} 的输出价格为 {{price}} M/token"
    },
    "models_invalid_price": {
        "en": "Invalid price value: {{error}}",
        "zh": "无效的价格值: {{error}}"
    },
    "models_input_price_usage": {
        "en": "Usage: /models /input_price <name> <value>",
        "zh": "用法: /models /input_price <name> <value>"
    },
    "models_output_price_usage": {
        "en": "Usage: /models /output_price <name> <value>",
        "zh": "用法: /models /output_price <name> <value>"
    },
    "models_speed_updated": {
        "en": "Updated speed for model {{name}} to {{speed}} s/request",
        "zh": "已更新模型 {{name}} 的速度为 {{speed}} 秒/请求"
    },
    "models_invalid_speed": {
        "en": "Invalid speed value: {{error}}",
        "zh": "无效的速度值: {{error}}"
    },
    "models_speed_usage": {
        "en": "Usage: /models /speed <name> <value>",
        "zh": "用法: /models /speed <name> <value>"
    },
    "models_title": {
        "en": "All Models (内置 + models.json)",
        "zh": "所有模型 (内置 + models.json)"
    },
    "models_no_models": {
        "en": "No models found.",
        "zh": "未找到任何模型。"
    },
    "models_lite_only": {
        "en": "The /models command is only available in lite mode",
        "zh": "/models 命令仅在 lite 模式下可用"
    },
    "models_api_key_exists": {
        "en": "API key file exists: {{path}}",
        "zh": "API密钥文件存在: {{path}}"
    },
    "config_invalid_format": {
        "en": "Error: Invalid configuration format. Use 'key:value' or '/drop key'.",
        "zh": "错误：配置格式无效。请使用 'key:value' 或 '/drop key'。"
    },
    "config_value_empty": {
        "en": "Error: Value cannot be empty. Use 'key:value'.",
        "zh": "错误：值不能为空。请使用 'key:value'。"
    },
    "config_set_success": {
        "en": "Set {{key}} to {{value}}",
        "zh": "已设置 {{key}} 为 {{value}}"
    },
    "config_delete_success": {
        "en": "Deleted configuration: {{key}}",
        "zh": "已删除配置：{{key}}"
    },
    "config_not_found": {
        "en": "Configuration not found: {{key}}",
        "zh": "未找到配置：{{key}}"
    },
    "add_files_matched": {
        "en": "All specified files are already in the current session or no matches found.",
        "zh": "所有指定的文件都已在当前会话中或未找到匹配项。"
    },
    "add_files_added_files": {
        "en": "Added Files",
        "zh": "已添加的文件"
    },
    "add_files_no_args": {
        "en": "Please provide arguments for the /add_files command.",
        "zh": "请为 /add_files 命令提供参数。"
    },
    "remove_files_all": {
        "en": "Removed all files.",
        "zh": "已移除所有文件。"
    },
    "remove_files_removed": {
        "en": "Removed Files",
        "zh": "已移除的文件"
    },
    "remove_files_none": {
        "en": "No files were removed.",
        "zh": "没有文件被移除。"
    },
    "files_removed": {
        "en": "Files Removed",
        "zh": "移除的文件"
    },
    "models_api_key_empty": {
        "en": "Warning : {{name}} API key is empty. Please set a valid API key.",
        "zh": "警告:  {{name}}  API key 为空。请设置一个有效的 API key。"
    },
    "commit_generating": {
        "en": "{{ model_name }} Generating commit message...",
        "zh": "{{ model_name }} 正在生成提交信息..."
    },
    "auto_command_reasoning_title": {
        "en": "Reply",
        "zh": "回复"
    },
    "commit_message": {
        "en": "{{ model_name }} Generated commit message: {{ message }}",
        "zh": "{{ model_name }} 生成的提交信息: {{ message }}"
    },
    "commit_failed": {
        "en": "{{ model_name }} Failed to generate commit message: {{ error }}",
        "zh": "{{ model_name }} 生成提交信息失败: {{ error }}"
    },
    "confirm_execute": {
        "en": "Do you want to execute this script?",
        "zh": "是否执行此脚本?"
    },
    "official_doc": {
        "en": "Official Documentation: https://uelng8wukz.feishu.cn/wiki/NhPNwSRcWimKFIkQINIckloBncI",
        "zh": "官方文档: https://uelng8wukz.feishu.cn/wiki/NhPNwSRcWimKFIkQINIckloBncI"
    },
    "plugins_desc": {
        "en": "Manage plugins",
        "zh": "管理插件"
    },
    "plugins_usage": {
        "en": "Usage: /plugins <command>\nAvailable subcommands:\n  /plugins /list - List all available plugins\n  /plugins /load <name> - Load a plugin\n  /plugins /unload <name> - Unload a plugin\n  /plugins/dirs - List plugin directories\n  /plugins/dirs /add <path> - Add a plugin directory\n  /plugins/dirs /remove <path> - Remove a plugin directory\n  /plugins/dirs /clear - Clear all plugin directories",
        "zh": "用法: /plugins <命令>\n可用的子命令:\n  /plugins /list - 列出所有可用插件\n  /plugins /load <名称> - 加载一个插件\n  /plugins /unload <名称> - 卸载一个插件\n  /plugins/dirs - 列出插件目录\n  /plugins/dirs /add <路径> - 添加一个插件目录\n  /plugins/dirs /remove <路径> - 移除一个插件目录\n  /plugins/dirs /clear - 清除所有插件目录"
    },
    "mcp_server_info_error": {
        "en": "Error getting MCP server info: {{ error }}",
        "zh": "获取MCP服务器信息时出错: {{ error }}"
    },
    "mcp_server_info_title": {
        "en": "Connected MCP Server Info",
        "zh": "已连接的MCP服务器信息"
    },
    "active_context_desc": {
        "en": "Manage active context tasks, list all tasks and their status",
        "zh": "管理活动上下文任务，列出所有任务及其状态"
    }
}


def get_system_language():
    try:
        return locale.getdefaultlocale()[0][:2]
    except:
        return "en"


def get_message(key):
    lang = get_system_language()
    return MESSAGES.get(key, {}).get(lang, MESSAGES[key].get("en", ""))


def get_message_with_format(msg_key: str, **kwargs):
    return format_str_jinja2(get_message(msg_key), **kwargs)
