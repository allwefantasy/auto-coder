import locale
from byzerllm.utils import format_str_jinja2

MESSAGES = {
    "auto_command_analyzing": {"en": "Selected command", "zh": "被选择指令"},
    "auto_command_break": {"en": "Auto command execution failed to execute command: {{command}}", "zh": "自动命令执行失败: {{command}}"},
    "auto_command_executing": {"en": "\n\n============= Executing command: {{command}} =============\n\n", "zh": "\n\n============= 正在执行指令: {{command}} =============\n\n"},
    "auto_command_failed": {"en": "Auto command failed: {{error}}. Please check your input and try again.", "zh": "自动命令执行失败: {{error}}。请检查您的输入并重试。"},
    "auto_command_not_found": {"en": "Auto command not found: {{command}}. Please check your input and try again.", "zh": "未找到自动命令: {{command}}。请检查您的输入并重试。"},
    "auto_config_analyzing": {"en": "Analyzing configuration...", "zh": "正在分析配置..."},
    "auto_web_analyzed": {"en": "Web automation task analysis completed", "zh": "网页自动化任务分析完成"},
    "auto_web_analyzing": {"en": "Analyzing web automation task...", "zh": "正在分析网页自动化任务..."},
    "begin_index_source_code": {"en": "🚀 Begin to index source code in {{ source_dir }}", "zh": "🚀 开始为 {{ source_dir }} 中的源代码建立索引"},
    "building_index_progress": {"en": "⏳ Building Index: {{ counter }}/{{ num_files }}...", "zh": "⏳ 正在构建索引: {{ counter }}/{{ num_files }}..."},
    "code_execution_warning": {"en": "Content(send to model) is {{ content_length }} tokens (you may collect too much files), which is larger than the maximum input length {{ max_length }}", "zh": "发送给模型的内容长度为 {{ content_length }} tokens（您可能收集了太多文件），超过了最大输入长度 {{ max_length }}"},
    "code_generation_complete": {"en": "{{ model_names}} Code generation completed in {{ duration }} seconds (sampling_count: {{ sampling_count }}), input_tokens_count: {{ input_tokens }}, generated_tokens_count: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}, speed: {{ speed }} tokens/s", "zh": "{{ model_names}} 代码生成完成，耗时 {{ duration }} 秒 (采样数: {{ sampling_count }}), 输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}, 速度: {{ speed }} tokens/秒"},
    "code_generation_start": {"en": "Auto generate the code...", "zh": "正在自动生成代码..."},
    "code_merge_start": {"en": "Auto merge the code...", "zh": "正在自动合并代码..."},
    "command_execution_result": {"en": "{{action}} execution result", "zh": "{{action}} 执行结果"},
    "config_delete_success": {"en": "Successfully deleted configuration: {{key}}", "zh": "成功删除配置: {{key}}"},
    "config_invalid_format": {"en": "Invalid configuration format. Expected 'key:value'", "zh": "配置格式无效，应为'key:value'格式"},
    "config_not_found": {"en": "Configuration not found: {{key}}", "zh": "未找到配置: {{key}}"},
    "config_set_success": {"en": "Successfully set configuration: {{key}} = {{value}}", "zh": "成功设置配置: {{key}} = {{value}}"},
    "config_validation_error": {"en": "Config validation error: {{error}}", "zh": "配置验证错误: {{error}}"},
    "conversation_pruning_start": {"en": "⚠️ Conversation pruning started, total tokens: {{total_tokens}}, safe zone: {{safe_zone}}", "zh": "⚠️ 对话长度 {{total_tokens}} tokens 超过安全阈值 {{safe_zone}}，开始修剪对话。"},
    "file_decode_error": {"en": "Failed to decode file: {{file_path}}. Tried encodings: {{encodings}}", "zh": "无法解码文件: {{file_path}}。尝试的编码: {{encodings}}"},
    "file_scored_message": {"en": "File scored: {{file_path}} - Score: {{score}}", "zh": "文件评分: {{file_path}} - 分数: {{score}}"},
    "file_write_error": {"en": "Failed to write file: {{file_path}}. Error: {{error}}", "zh": "无法写入文件: {{file_path}}. 错误: {{error}}"},
    "files_merged": {"en": "✅ Merged {{ total }} files into the project.", "zh": "✅ 成功合并了 {{ total }} 个文件到项目中。"},
    "generation_cancelled": {"en": "[Interrupted] Generation cancelled", "zh": "[已中断] 生成已取消"},
    "generating_shell_script": {"en": "Generating Shell Script", "zh": "正在生成 Shell 脚本"},
    "git_command_error": {"en": "Git command execution error: {{error}}", "zh": "Git命令执行错误: {{error}}"},
    "git_init_required": {"en": "⚠️ auto_merge only applies to git repositories.\n\nPlease try using git init in the source directory:\n\n```shell\ncd {{ source_dir }}\ngit init.\n```\n\nThen run auto - coder again.\nError: {{ error }}", "zh": "⚠️ auto_merge 仅适用于 git 仓库。\n\n请尝试在源目录中使用 git init:\n\n```shell\ncd {{ source_dir }}\ngit init.\n```\n\n然后再次运行 auto-coder。\n错误: {{ error }}"},
    "human_as_model_instructions": {"en": "You are now in Human as Model mode. The content has been copied to your clipboard.\nThe system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\nUse '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again.", "zh": "您现在处于人类作为模型模式。内容已复制到您的剪贴板。\n系统正在等待您的输入。完成后，在新行输入'EOF'提交。\n使用'/break'退出此模式。如果复制粘贴有问题，使用'/clear'清理并重新粘贴。"},
    "index_build_error": {"en": "❌ {{ model_name }} Error building index for {{ file_path }}: {{ error }}", "zh": "❌ {{ model_name }} 构建 {{ file_path }} 索引时出错: {{ error }}"},
    "index_build_summary": {"en": "📊 Total Files: {{ total_files }}, Need to Build Index: {{ num_files }}", "zh": "📊 总文件数: {{ total_files }}, 需要构建索引: {{ num_files }}"},
    "index_file_filtered": {"en": "File {{file_path}} is filtered by model {{model_name}} restrictions", "zh": "文件 {{file_path}} 被模型 {{model_name}} 的访问限制过滤"},
    "index_file_removed": {"en": "🗑️ Removed non-existent file index: {{ file_path }}", "zh": "🗑️ 已移除不存在的文件索引：{{ file_path }}"},
    "index_file_saved": {"en": "💾 Saved index file, updated {{ updated_files }} files, removed {{ removed_files }} files, input_tokens: {{ input_tokens }}, output_tokens: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}", "zh": "💾 已保存索引文件，更新了 {{ updated_files }} 个文件，移除了 {{ removed_files }} 个文件，输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}"},
    "index_file_too_large": {"en": "⚠️ File {{ file_path }} is too large ({{ file_size }} > {{ max_length }}), splitting into chunks...", "zh": "⚠️ 文件 {{ file_path }} 过大 ({{ file_size }} > {{ max_length }}), 正在分块处理..."},
    "index_source_dir_mismatch": {"en": "⚠️ Source directory mismatch (file_path: {{ file_path }}, source_dir: {{ source_dir }})", "zh": "⚠️ 源目录不匹配 (文件路径: {{ file_path }}, 源目录: {{ source_dir }})"},
    "index_update_success": {"en": "✅ {{ model_name }} Successfully updated index for {{ file_path }} (md5: {{ md5 }}) in {{ duration }}s, input_tokens: {{ input_tokens }}, output_tokens: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}", "zh": "✅ {{ model_name }} 成功更新 {{ file_path }} 的索引 (md5: {{ md5 }}), 耗时 {{ duration }} 秒, 输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}"},
    "invalid_boolean_value": {"en": "Value '{{value}}' is not a valid boolean(true/false)", "zh": "值 '{{value}}' 不是有效的布尔值(true/false)"},
    "invalid_choice": {"en": "Value '{{value}}' is not in allowed options({{allowed}})", "zh": "值 '{value}' 不在允许选项中({allowed})"},
    "invalid_file_pattern": {"en": "Invalid file pattern: {{file_pattern}}. e.g. regex://.*/package-lock\\.json", "zh": "无效的文件模式: {{file_pattern}}. 例如: regex://.*/package-lock\\.json"},
    "invalid_float_value": {"en": "Value '{{value}}' is not a valid float", "zh": "值 '{{value}}' 不是有效的浮点数"},
    "invalid_integer_value": {"en": "Value '{{value}}' is not a valid integer", "zh": "值 '{{value}}' 不是有效的整数"},
    "invalid_type_value": {"en": "Value '{{value}}' is not a valid type (expected: {{types}})", "zh": "值 '{{value}}' 不是有效的类型 (期望: {{types}})"},
    "memory_save_success": {"en": "✅ Saved to your memory(path: {{path}})", "zh": "✅ 已保存到您的记忆中(路径: {{path}})"},
    "model_not_found": {"en": "Model '{{model}}' is not configured in models.yml", "zh": "模型 '{model}' 未在 models.yml 中配置"},
    "models_no_active": {"en": "No active models found", "zh": "未找到激活的模型"},
    "models_speed_test_results": {"en": "Model Speed Test Results", "zh": "模型速度测试结果"},
    "models_testing": {"en": "Testing model: {{name}}...", "zh": "正在测试模型: {{name}}..."},
    "models_testing_start": {"en": "Starting speed test for all active models...", "zh": "开始对所有激活的模型进行速度测试..."},
    "new_session_started": {"en": "New session started. Previous chat history has been archived.", "zh": "新会话已开始。之前的聊天历史已存档。"},
    "no_changes_made": {"en": "⚠️ No changes were made to any files.", "zh": "⚠️ 未对任何文件进行更改。这个原因可能是因为coding函数生成的文本块格式有问题，导致无法合并进项目"},
    "phase1_processing_sources": {"en": "Phase 1: Processing REST/RAG/Search sources...", "zh": "阶段 1: 正在处理 REST/RAG/Search 源..."},
    "phase2_building_index": {"en": "Phase 2: Building index for all files...", "zh": "阶段 2: 正在为所有文件构建索引..."},
    "phase6_file_selection": {"en": "Phase 6: Processing file selection and limits...", "zh": "阶段 6: 正在处理文件选择和限制..."},
    "phase7_preparing_output": {"en": "Phase 7: Preparing final output...", "zh": "阶段 7: 正在准备最终输出..."},
    "pylint_check_failed": {"en": "⚠️ Pylint check failed: {{ error_message }}", "zh": "⚠️ Pylint 检查失败: {{ error_message }}"},
    "pylint_error": {"en": "❌ Error running pylint: {{ error_message }}", "zh": "❌ 运行 Pylint 时出错: {{ error_message }}"},
    "quick_filter_start": {"en": "{{ model_name }} Starting filter context(quick_filter)...", "zh": "{{ model_name }} 开始查找上下文(quick_filter)..."},
    "required_without_default": {"en": "Config key '{{key}}' requires explicit value", "zh": "配置项 '{key}' 需要明确设置值"},
    "satisfied_prompt": {"en": "Requirements satisfied, no further action needed", "zh": "已满足需求，无需进一步操作"},
    "task_cancelled_by_user": {"en": "Task was cancelled by user", "zh": "任务被用户取消"},
    "unknown_config_key": {"en": "Unknown config key '{{key}}'", "zh": "未知的配置项 '{key}'"},
    "value_out_of_range": {"en": "Value {{value}} is out of allowed range({{min}}~{{max}})", "zh": "值 {value} 超出允许范围({min}~{max})"},
    "yaml_load_error": {"en": "Error loading yaml file {{yaml_file}}: {{error}}", "zh": "加载YAML文件出错 {{yaml_file}}: {{error}}"}
}

def get_system_language():
    try:
        return locale.getdefaultlocale()[0][:2]
    except:
        return 'en'

def get_message(key):
    lang = get_system_language()
    return MESSAGES.get(key, {}).get(lang, MESSAGES[key]['en'])

def get_message_with_format(msg_key: str, **kwargs):
    return format_str_jinja2(get_message(msg_key), **kwargs)