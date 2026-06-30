from byzerllm.utils import format_str_jinja2
import locale

MESSAGES = {
    "file_scored_message": {
        "en": "File scored: {{file_path}} - Score: {{score}}",
        "zh": "文件评分: {{file_path}} - 分数: {{score}}"
    },
    "invalid_file_pattern": {
        "en": "Invalid file pattern: {{file_pattern}}. e.g. regex://.*/package-lock\\.json",
        "zh": "无效的文件模式: {{file_pattern}}. 例如: regex://.*/package-lock\\.json"
    },
    "config_validation_error": {
        "en": "Config validation error: {{error}}",
        "zh": "配置验证错误: {{error}}"
    },
    "invalid_boolean_value": {
        "en": "Value '{{value}}' is not a valid boolean(true/false)",
        "zh": "值 '{{value}}' 不是有效的布尔值(true/false)"
    },
    "invalid_integer_value": {
        "en": "Value '{{value}}' is not a valid integer",
        "zh": "值 '{{value}}' 不是有效的整数"
    },
    "invalid_float_value": {
        "en": "Value '{{value}}' is not a valid float",
        "zh": "值 '{{value}}' 不是有效的浮点数"
    },
    "invalid_type_value": {
        "en": "Value '{{value}}' is not a valid type (expected: {{types}})",
        "zh": "值 '{{value}}' 不是有效的类型 (期望: {{types}})"
    },
    "value_out_of_range": {
        "en": "Value {{value}} is out of allowed range({{min}}~{{max}})",
        "zh": "值 {value} 超出允许范围({min}~{max})"
    },
    "invalid_choice": {
        "en": "Value '{{value}}' is not in allowed options({{allowed}})",
        "zh": "值 '{value}' 不在允许选项中({allowed})"
    },
    "unknown_config_key": {
        "en": "Unknown config key '{{key}}'",
        "zh": "未知的配置项 '{key}'"
    },
    "model_not_found": {
        "en": "Model '{{model}}' is not configured in models.yml",
        "zh": "模型 '{model}' 未在 models.yml 中配置"
    },
    "required_without_default": {
        "en": "Config key '{{key}}' requires explicit value",
        "zh": "配置项 '{key}' 需要明确设置值"
    },
    "auto_command_action_break": {
        "en": "Command {{command}} execution failed (got {{action}} result), no result can be obtained, please try again",
        "zh": "命令 {{command}} 执行失败（获取到了 {{action}} 的结果），无法获得任何结果,请重试"
    },
    "auto_command_break": {
        "en": "Auto command execution failed to execute command: {{command}}",
        "zh": "自动命令执行失败: {{command}}"
    },
    "auto_command_executing": {
        "en": "\n\n============= Executing command: {{command}} =============\n\n",
        "zh": "\n\n============= 正在执行指令: {{command}} =============\n\n"
    },
    "model_provider_select_title": {
        "en": "Select Model Provider",
        "zh": "选择模型供应商"
    },
    "auto_config_analyzing": {
        "en": "Analyzing configuration...",
        "zh": "正在分析配置..."
    },
    "config_delete_success": {
        "en": "Successfully deleted configuration: {{key}}",
        "zh": "成功删除配置: {{key}}"
    },
    "config_not_found": {
        "en": "Configuration not found: {{key}}",
        "zh": "未找到配置: {{key}}"
    },
    "config_invalid_format": {
        "en": "Invalid configuration format. Expected 'key:value'",
        "zh": "配置格式无效，应为'key:value'格式"
    },
    "config_value_empty": {
        "en": "Configuration value cannot be empty",
        "zh": "配置值不能为空"
    },
    "config_set_success": {
        "en": "Successfully set configuration: {{key}} = {{value}}",
        "zh": "成功设置配置: {{key}} = {{value}}"
    },
    "model_provider_select_text": {
        "en": "Please select your model provider:",
        "zh": "请选择您的模型供应商："
    },
    "model_provider_volcano": {
        "en": "Volcano Engine",
        "zh": "火山方舟"
    },
    "model_provider_siliconflow": {
        "en": "SiliconFlow AI",
        "zh": "硅基流动"
    },
    "model_provider_deepseek": {
        "en": "DeepSeek Official",
        "zh": "DeepSeek官方"
    },
    "model_provider_openrouter": {
        "en": "OpenRouter",
        "zh": "OpenRouter"
    },
    "model_provider_requesty": {
        "en": "Requesty",
        "zh": "Requesty"
    },
    "model_provider_api_key_title": {
        "en": "API Key",
        "zh": "API密钥"
    },
    "model_provider_volcano_api_key_text": {
        "en": "Please enter your Volcano Engine API key:",
        "zh": "请输入您的火山方舟API密钥："
    },
    "model_provider_openrouter_api_key_text": {
        "en": "Please enter your OpenRouter API key:",
        "zh": "请输入您的OpenRouter API密钥："
    },
    "model_provider_requesty_api_key_text": {
        "en": "Please enter your Requesty API key:",
        "zh": "请输入您的Requesty API密钥："
    },
    "model_provider_volcano_r1_text": {
        "en": "Please enter your Volcano Engine R1 endpoint (format: ep-20250204215011-vzbsg):",
        "zh": "请输入您的火山方舟 R1 推理点(格式如: ep-20250204215011-vzbsg)："
    },
    "model_provider_volcano_v3_text": {
        "en": "Please enter your Volcano Engine V3 endpoint (format: ep-20250204215011-vzbsg):",
        "zh": "请输入您的火山方舟 V3 推理点(格式如: ep-20250204215011-vzbsg)："
    },
    "model_provider_siliconflow_api_key_text": {
        "en": "Please enter your SiliconFlow AI API key:",
        "zh": "请输入您的硅基流动API密钥："
    },
    "model_provider_deepseek_api_key_text": {
        "en": "Please enter your DeepSeek API key:",
        "zh": "请输入您的DeepSeek API密钥："
    },    
    "model_provider_selected": {
        "en": "Provider configuration completed successfully! You can use /models command to view, add and modify all models later.",
        "zh": "供应商配置已成功完成！后续你可以使用 /models 命令，查看，新增和修改所有模型"
    },
    "model_provider_success_title": {
        "en": "Success",
        "zh": "成功"
    },
    "index_file_filtered": {
        "en": "File {{file_path}} is filtered by model {{model_name}} restrictions",
        "zh": "文件 {{file_path}} 被模型 {{model_name}} 的访问限制过滤"
    },
    "models_no_active": {
        "en": "No active models found",
        "zh": "未找到激活的模型"
    },
    "models_speed_test_results": {
        "en": "Model Speed Test Results",
        "zh": "模型速度测试结果"
    },
    "models_testing": {
        "en": "Testing model: {{name}}...",
        "zh": "正在测试模型: {{name}}..."
    },
    "models_testing_start": {
        "en": "Starting speed test for all active models...",
        "zh": "开始对所有激活的模型进行速度测试..."
    },
    "models_testing_progress": {
        "en": "Testing progress: {{ completed }}/{{ total }} models",
        "zh": "测试进度: {{ completed }}/{{ total }} 个模型"
    },
    "generation_cancelled": {
        "en": "[Interrupted] Generation cancelled",
        "zh": "[已中断] 生成已取消"
    },
    "model_not_found": {
        "en": "Model {{model_name}} not found",
        "zh": "未找到模型: {{model_name}}"
    },
    "generating_shell_script": {
        "en": "Generating Shell Script",
        "zh": "正在生成 Shell 脚本"
    },
    "new_session_started": {
        "en": "New session started. Previous chat history has been archived.",
        "zh": "新会话已开始。之前的聊天历史已存档。"
    },
    "memory_save_success": {
        "en": "✅ Saved to your memory(path: {{path}})",
        "zh": "✅ 已保存到您的记忆中(路径: {{path}})"
    },
    "file_decode_error": {
        "en": "Failed to decode file: {{file_path}}. Tried encodings: {{encodings}}",
        "zh": "无法解码文件: {{file_path}}。尝试的编码: {{encodings}}"
    },
    "file_write_error": {
        "en": "Failed to write file: {{file_path}}. Error: {{error}}",
        "zh": "无法写入文件: {{file_path}}. 错误: {{error}}"
    },
    "yaml_load_error": {
        "en": "Error loading yaml file {{yaml_file}}: {{error}}",
        "zh": "加载YAML文件出错 {{yaml_file}}: {{error}}"
    },
    "git_command_error": {
        "en": "Git command execution error: {{error}}",
        "zh": "Git命令执行错误: {{error}}"
    },
    "get_commit_diff_error": {
        "en": "Error getting commit diff: {{error}}",
        "zh": "获取commit diff时出错: {{error}}"
    },
    "no_latest_commit": {
        "en": "Unable to get latest commit information",
        "zh": "无法获取最新的提交信息"
    },
    "code_review_error": {
        "en": "Code review process error: {{error}}",
        "zh": "代码审查过程出错: {{error}}"
    },
    "index_file_too_large": {
        "en": "⚠️ File {{ file_path }} is too large ({{ file_size }} > {{ max_length }}), splitting into chunks...",
        "zh": "⚠️ 文件 {{ file_path }} 过大 ({{ file_size }} > {{ max_length }}), 正在分块处理..."
    },
    "index_update_success": {
        "en": "✅ {{ model_name }} Successfully updated index for {{ file_path }} (md5: {{ md5 }}) in {{ duration }}s, input_tokens: {{ input_tokens }}, output_tokens: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}",
        "zh": "✅ {{ model_name }} 成功更新 {{ file_path }} 的索引 (md5: {{ md5 }}), 耗时 {{ duration }} 秒, 输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}"
    },
    "index_build_error": {
        "en": "❌ {{ model_name }} Error building index for {{ file_path }}: {{ error }}",
        "zh": "❌ {{ model_name }} 构建 {{ file_path }} 索引时出错: {{ error }}"
    },
    "index_build_summary": {
        "en": "📊 Total Files: {{ total_files }}, Need to Build Index: {{ num_files }}",
        "zh": "📊 总文件数: {{ total_files }}, 需要构建索引: {{ num_files }}"
    },
    "building_index_progress": {
        "en": "⏳ Building Index: {{ counter }}/{{ num_files }}...",
        "zh": "⏳ 正在构建索引: {{ counter }}/{{ num_files }}..."
    },
    "index_source_dir_mismatch": {
        "en": "⚠️ Source directory mismatch (file_path: {{ file_path }}, source_dir: {{ source_dir }})",
        "zh": "⚠️ 源目录不匹配 (文件路径: {{ file_path }}, 源目录: {{ source_dir }})"
    },
    "index_related_files_fail": {
        "en": "⚠️ Failed to find related files for chunk {{ chunk_count }}",
        "zh": "⚠️ 无法为块 {{ chunk_count }} 找到相关文件"
    },
    "index_threads_completed": {
        "en": "✅ Completed {{ completed_threads }}/{{ total_threads }} threads",
        "zh": "✅ 已完成 {{ completed_threads }}/{{ total_threads }} 个线程"
    },
    "index_file_removed": {
        "en": "🗑️ Removed non-existent file index: {{ file_path }}",
        "zh": "🗑️ 已移除不存在的文件索引：{{ file_path }}"
    },
    "index_file_saved": {
        "en": "💾 Saved index file, updated {{ updated_files }} files, removed {{ removed_files }} files, input_tokens: {{ input_tokens }}, output_tokens: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}",
        "zh": "💾 已保存索引文件，更新了 {{ updated_files }} 个文件，移除了 {{ removed_files }} 个文件，输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}"
    },
    "task_cancelled_by_user": {
        "en": "Task was cancelled by user",
        "zh": "任务被用户取消"
    },
    "cancellation_requested": {
        "en": "Cancellation requested, waiting for thread to terminate...",
        "zh": "已请求取消，正在等待线程终止..."
    },
    "force_terminating_thread": {
        "en": "Force terminating thread after timeout",
        "zh": "线程超时强制终止"
    },
    "force_raising_keyboard_interrupt": {
        "en": "Force raising KeyboardInterrupt after timeout",
        "zh": "超时强制抛出键盘中断异常"
    },
    "thread_terminated": {
        "en": "Thread terminated",
        "zh": "线程已终止"
    },
    "human_as_model_instructions": {
        "en": "You are now in Human as Model mode. The content has been copied to your clipboard.\nThe system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\nUse '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again.",
        "zh": "您现在处于人类作为模型模式。内容已复制到您的剪贴板。\n系统正在等待您的输入。完成后，在新行输入'EOF'提交。\n使用'/break'退出此模式。如果复制粘贴有问题，使用'/clear'清理并重新粘贴。"
    },
    "clipboard_not_supported": {
        "en": "pyperclip not installed or clipboard is not supported, instruction will not be copied to clipboard.",
        "zh": "未安装pyperclip或不支持剪贴板，指令将不会被复制到剪贴板。"
    },
    "human_as_model_instructions_no_clipboard": {
        "en": "You are now in Human as Model mode. [bold red]The content could not be copied to your clipboard.[/bold red]\nbut you can copy prompt from output.txt file.\nThe system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\nUse '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again.",
        "zh": "您现在处于人类作为模型模式。[bold red]内容无法复制到您的剪贴板。[/bold red]\n但您可以从output.txt文件复制提示。\n系统正在等待您的输入。完成后，在新行输入'EOF'提交。\n使用'/break'退出此模式。如果复制粘贴有问题，使用'/clear'清理并重新粘贴。"
    },
    "phase1_processing_sources": {
        "en": "Phase 1: Processing REST/RAG/Search sources...",
        "zh": "阶段 1: 正在处理 REST/RAG/Search 源..."
    },
    "phase2_building_index": {
        "en": "Phase 2: Building index for all files...",
        "zh": "阶段 2: 正在为所有文件构建索引..."
    },
    "phase6_file_selection": {
        "en": "Phase 6: Processing file selection and limits...",
        "zh": "阶段 6: 正在处理文件选择和限制..."
    },
    "phase7_preparing_output": {
        "en": "Phase 7: Preparing final output...",
        "zh": "阶段 7: 正在准备最终输出..."
    },
    "chat_human_as_model_instructions": {
        "en": "Chat is now in Human as Model mode.\nThe question has been copied to your clipboard.\nPlease use Web version model to get the answer.\nOr use /conf human_as_model:false to close this mode and get the answer in terminal directlyPaste the answer to the input box below, use '/break' to exit, '/clear' to clear the screen, '/eof' to submit.",
        "zh": "\n============= Chat 处于 Human as Model 模式 =============\n问题已复制到剪贴板\n请使用Web版本模型获取答案\n或者使用 /conf human_as_model:false 关闭该模式直接在终端获得答案。将获得答案黏贴到下面的输入框，换行后，使用 '/break' 退出，'/clear' 清屏，'/eof' 提交。"
    },
    "code_generation_start": {
        "en": "Auto generate the code...",
        "zh": "正在自动生成代码..."
    },
    "code_generation_complete": {
        "en": "{{ model_names}} Code generation completed in {{ duration }} seconds (sampling_count: {{ sampling_count }}), input_tokens_count: {{ input_tokens }}, generated_tokens_count: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}, speed: {{ speed }} tokens/s",
        "zh": "{{ model_names}} 代码生成完成，耗时 {{ duration }} 秒 (采样数: {{ sampling_count }}), 输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}, 速度: {{ speed }} tokens/秒"
    },
    "generate_max_rounds_reached": {
        "en": "⚠️ Generation stopped after reaching the maximum allowed rounds ({{ count }}/{{ max_rounds }}). Current generated content length: {{ generated_tokens }}. If the output is incomplete, consider increasing 'generate_max_rounds' in configuration.",
        "zh": "⚠️ 生成已停止，因为达到了最大允许轮数 ({{ count }}/{{ max_rounds }})。当前生成内容长度: {{ generated_tokens }} tokens。如果输出不完整，请考虑在配置中增加 'generate_max_rounds'。"
    },
    "code_merge_start": {
        "en": "Auto merge the code...",
        "zh": "正在自动合并代码..."
    },
    "code_execution_warning": {
        "en": "Content(send to model) is {{ content_length }} tokens (you may collect too much files), which is larger than the maximum input length {{ max_length }}",
        "zh": "发送给模型的内容长度为 {{ content_length }} tokens（您可能收集了太多文件），超过了最大输入长度 {{ max_length }}"
    },
    "quick_filter_start": {
        "en": "{{ model_name }} Starting filter context(quick_filter)...",
        "zh": "{{ model_name }} 开始查找上下文(quick_filter)..."
    },
    "normal_filter_start": {
        "en": "{{ model_name }} Starting filter context(normal_filter)...",
        "zh": "{{ model_name }} 开始查找上下文(normal_filter)..."
    },
    "pylint_check_failed": {
        "en": "⚠️ Pylint check failed: {{ error_message }}",
        "zh": "⚠️ Pylint 检查失败: {{ error_message }}"
    },
    "pylint_error": {
        "en": "❌ Error running pylint: {{ error_message }}",
        "zh": "❌ 运行 Pylint 时出错: {{ error_message }}"
    },
    "unmerged_blocks_warning": {
        "en": "⚠️ Found {{ num_blocks }} unmerged blocks, the changes will not be applied. Please review them manually then try again.",
        "zh": "⚠️ 发现 {{ num_blocks }} 个未合并的代码块，更改将不会被应用。请手动检查后重试。"
    },
    "pylint_file_check_failed": {
        "en": "⚠️ Pylint check failed for {{ file_path }}. Changes not applied. Error: {{ error_message }}",
        "zh": "⚠️ {{ file_path }} 的 Pylint 检查失败。更改未应用。错误: {{ error_message }}"
    },
    "merge_success": {
        "en": "✅ Merged changes in {{ num_files }} files {{ num_changes }}/{{ total_blocks }} blocks.",
        "zh": "✅ 成功合并了 {{ num_files }} 个文件中的更改 {{ num_changes }}/{{ total_blocks }} 个代码块。"
    },
    "no_changes_made": {
        "en": "⚠️ No changes were made to any files.",
        "zh": "⚠️ 未对任何文件进行更改。这个原因可能是因为coding函数生成的文本块格式有问题，导致无法合并进项目"
    },
    "files_merged": {
        "en": "✅ Merged {{ total }} files into the project.",
        "zh": "✅ 成功合并了 {{ total }} 个文件到项目中。"
    },
    "merge_failed": {
        "en": "❌ Merge file {{ path }} failed: {{ error }}",
        "zh": "❌ 合并文件 {{ path }} 失败: {{ error }}"
    },
    "files_merged_total": {
        "en": "✅ Merged {{ total }} files into the project.",
        "zh": "✅ 合并了 {{ total }} 个文件到项目中。"
    },
    "ranking_skip": {
        "en": "Only 1 candidate, skip ranking",
        "zh": "只有1个候选项，跳过排序"
    },
    "ranking_start": {
        "en": "Start ranking {{ count }} candidates using model {{ model_name }}",
        "zh": "开始对 {{ count }} 个候选项进行排序,使用模型 {{ model_name }} 打分"
    },
    "ranking_failed_request": {
        "en": "Ranking request failed: {{ error }}",
        "zh": "排序请求失败: {{ error }}"
    },
    "ranking_all_failed": {
        "en": "All ranking requests failed",
        "zh": "所有排序请求都失败"
    },
    "ranking_complete": {
        "en": "{{ model_names }} Ranking completed in {{ elapsed }}s, total voters: {{ total_tasks }}, best candidate index: {{ best_candidate }}, scores: {{ scores }}, input_tokens: {{ input_tokens }}, output_tokens: {{ output_tokens }}, input_cost: {{ input_cost }}, output_cost: {{ output_cost }}, speed: {{ speed }} tokens/s",
        "zh": "{{ model_names }} 排序完成，耗时 {{ elapsed }} 秒，总投票数: {{ total_tasks }}，最佳候选索引: {{ best_candidate }}，得分: {{ scores }}，输入token数: {{ input_tokens }}，输出token数: {{ output_tokens }}，输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}，速度: {{ speed }} tokens/秒"
    },
    "ranking_process_failed": {
        "en": "Ranking process failed: {{ error }}",
        "zh": "排序过程失败: {{ error }}"
    },
    "ranking_failed": {
        "en": "Ranking failed in {{ elapsed }}s, using original order",
        "zh": "排序失败，耗时 {{ elapsed }} 秒，使用原始顺序"
    },
    "begin_index_source_code": {
        "en": "🚀 Begin to index source code in {{ source_dir }}",
        "zh": "🚀 开始为 {{ source_dir }} 中的源代码建立索引"
    },
    "stream_out_stats": {
        "en": "Model: {{ model_name }}, Total time: {{ elapsed_time }} seconds, First token time: {{ first_token_time }} seconds, Speed: {{ speed }} tokens/s, Input tokens: {{ input_tokens }}, Output tokens: {{ output_tokens }}, Input cost: {{ input_cost }}, Output cost: {{ output_cost }}",
        "zh": "模型: {{ model_name }},总耗时 {{ elapsed_time }} 秒,首token时间: {{ first_token_time }} 秒, 速度: {{ speed }} tokens/秒, 输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}"
    },
    "quick_filter_stats": {
        "en": "{{ model_names }} Quick filter completed in {{ elapsed_time }} seconds, input tokens: {{ input_tokens }}, output tokens: {{ output_tokens }}, input cost: {{ input_cost }}, output cost: {{ output_cost }} speed: {{ speed }} tokens/s",
        "zh": "{{ model_names }} Quick Filter 完成耗时 {{ elapsed_time }} 秒，输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }} 速度: {{ speed }} tokens/秒"
    },
    "upsert_file": {
        "en": "✅ Updated file: {{ file_path }}",
        "zh": "✅ 更新文件: {{ file_path }}"
    },
    "unmerged_blocks_title": {
        "en": "Unmerged Blocks",
        "zh": "未合并代码块"
    },
    "merged_blocks_title": {
        "en": "Merged Changes",
        "zh": "合并的更改"
    },
    "quick_filter_title": {
        "en": "{{ model_name }} is analyzing how to filter context...",
        "zh": "{{ model_name }} 正在分析如何筛选上下文..."
    },
    "quick_filter_failed": {
        "en": "❌ Quick filter failed: {{ error }}. ",
        "zh": "❌ 快速过滤器失败: {{ error }}. "
    },
    "unmerged_file_path": {
        "en": "File: {{file_path}}",
        "zh": "文件: {{file_path}}"
    },
    "unmerged_search_block": {
        "en": "Search Block({{similarity}}):",
        "zh": "Search Block({{similarity}}):"
    },
    "unmerged_replace_block": {
        "en": "Replace Block:",
        "zh": "Replace Block:"
    },
    "unmerged_blocks_total": {
        "en": "Total unmerged blocks: {{num_blocks}}",
        "zh": "未合并代码块数量: {{num_blocks}}"
    },
    "git_init_required": {
        "en": "⚠️ auto_merge only applies to git repositories.\n\nPlease try using git init in the source directory:\n\n```shell\ncd {{ source_dir }}\ngit init.\n```\n\nThen run auto - coder again.\nError: {{ error }}",
        "zh": "⚠️ auto_merge 仅适用于 git 仓库。\n\n请尝试在源目录中使用 git init:\n\n```shell\ncd {{ source_dir }}\ngit init.\n```\n\n然后再次运行 auto-coder。\n错误: {{ error }}"
    },
    "quick_filter_reason": {
        "en": "Auto get(quick_filter mode)",
        "zh": "自动获取(quick_filter模式)"
    },
    "quick_filter_too_long": {
        "en": "⚠️ index file is too large ({{ tokens_len }}/{{ max_tokens }}). The query will be split into {{ split_size }} chunks.",
        "zh": "⚠️ 索引文件过大 ({{ tokens_len }}/{{ max_tokens }})。查询将被分成 {{ split_size }} 个部分执行。"
    },
    "quick_filter_tokens_len": {
        "en": "📊 Current index size: {{ tokens_len }} tokens",
        "zh": "📊 当前索引大小: {{ tokens_len }} tokens"
    },
    "estimated_chat_input_tokens": {
        "en": "Estimated chat input tokens: {{ estimated_input_tokens }}",
        "zh": "对话输入token预估为: {{ estimated_input_tokens }}"
    },
    "estimated_input_tokens_in_generate": {
        "en": "Estimated input tokens in generate ({{ generate_mode }}): {{ estimated_input_tokens_in_generate }}",
        "zh": "生成代码({{ generate_mode }})预计输入token数: {{ estimated_input_tokens_in_generate }}"
    },
    "model_has_access_restrictions": {
        "en": "{{model_name}} has access restrictions, cannot use the current function",
        "zh": "{{model_name}} 有访问限制，无法使用当前功能"
    },
    "auto_command_not_found": {
        "en": "Auto command not found: {{command}}. Please check your input and try again.",
        "zh": "未找到自动命令: {{command}}。请检查您的输入并重试。"
    },
    "auto_command_failed": {
        "en": "Auto command failed: {{error}}. Please check your input and try again.",
        "zh": "自动命令执行失败: {{error}}。请检查您的输入并重试。"
    },
    "command_execution_result": {
        "en": "{{action}} execution result",
        "zh": "{{action}} 执行结果"
    },
    "satisfied_prompt": {
        "en": "Requirements satisfied, no further action needed",
        "zh": "已满足需求，无需进一步操作"
    },
    "auto_command_analyzed": {
        "en": "Selected command",
        "zh": "被选择指令"
    },
    "invalid_enum_value": {
        "en": "Value '{{value}}' is not in allowed values ({{allowed}})",
        "zh": "值 '{{value}}' 不在允许的值列表中 ({{allowed}})"
    },
    "conversation_pruning_start": {
        "en": "⚠️ Conversation pruning started, total tokens: {{total_tokens}}, safe zone: {{safe_zone}}",
        "zh": "⚠️ 对话长度 {{total_tokens}} tokens 超过安全阈值 {{safe_zone}}，开始修剪对话。"
    },
    "invalid_file_number": {
        "en": "⚠️ Invalid file number {{file_number}}, total files: {{total_files}}",
        "zh": "⚠️ 无效的文件编号 {{file_number}}，总文件数为 {{total_files}}"
    },
    "all_merge_results_failed": {
        "en": "⚠️ All merge attempts failed, returning first candidate",
        "zh": "⚠️ 所有合并尝试都失败，返回第一个候选"
    },
    "only_one_merge_result_success": {
        "en": "✅ Only one merge result succeeded, returning that candidate",
        "zh": "✅ 只有一个合并结果成功，返回该候选"
    },
    "conf_import_success": {
        "en": "Successfully imported configuration: {{path}}",
        "zh": "成功导入配置: {{path}}"
    },
    "conf_export_success": {
        "en": "Successfully exported configuration: {{path}}",
        "zh": "成功导出配置: {{path}}"
    },
    "conf_import_error": {
        "en": "Error importing configuration: {{error}}",
        "zh": "导入配置出错: {{error}}"
    },
    "conf_export_error": {
        "en": "Error exporting configuration: {{error}}",
        "zh": "导出配置出错: {{error}}"
    },
    "conf_import_invalid_format": {
        "en": "Invalid import configuration format, expected 'key:value'",
        "zh": "导入配置格式无效, 应为 'key:value' 格式"
    },
    "conf_export_invalid_format": {
        "en": "Invalid export configuration format, expected 'key:value'",
        "zh": "导出配置格式无效, 应为 'key:value' 格式"
    },
    "conf_import_file_not_found": {
        "en": "Import configuration file not found: {{file_path}}",
        "zh": "未找到导入配置文件: {{file_path}}"
    },
    "conf_export_file_not_found": {
        "en": "Export configuration file not found: {{file_path}}",
        "zh": "未找到导出配置文件: {{file_path}}"
    },
    "conf_import_file_empty": {
        "en": "Import configuration file is empty: {{file_path}}",
        "zh": "导入配置文件为空: {{file_path}}"
    },
    "conf_export_file_empty": {
        "en": "Export configuration file is empty: {{file_path}}",
        "zh": "导出配置文件为空: {{file_path}}"
    },
    "generated_shell_script": {
        "en": "Generated Shell Script",
        "zh": "生成的 Shell 脚本"
    },
    "confirm_execute_shell_script": {
        "en": "Do you want to execute this shell script?",
        "zh": "您要执行此 shell 脚本吗？"
    },
    "shell_script_not_executed": {
        "en": "Shell script was not executed",
        "zh": "Shell 脚本未执行"
    },
    "index_export_success": {
        "en": "Index exported successfully: {{path}}",
        "zh": "索引导出成功: {{path}}"
    },
    "index_import_success": {
        "en": "Index imported successfully: {{path}}",
        "zh": "索引导入成功: {{path}}"
    },
    "edits_title": {
        "en": "edits",
        "zh": "编辑块"
    },
    "diff_blocks_title": {
        "en": "diff blocks",
        "zh": "差异块"
    },
    "index_exclude_files_error": {
        "en": "index filter exclude files fail: {{ error }}",
        "zh": "索引排除文件时出错: {{error}}"
    },
    "file_sliding_window_processing": {
        "en": "File {{ file_path }} is too large ({{ tokens }} tokens), processing with sliding window...",
        "zh": "文件 {{ file_path }} 过大 ({{ tokens }} tokens)，正在使用滑动窗口处理..."
    },
    "file_snippet_processing": {
        "en": "Processing file {{ file_path }} with code snippet extraction...",
        "zh": "正在对文件 {{ file_path }} 进行代码片段提取..."
    },
    "context_pruning_start": {
        "en": "⚠️ Context pruning started. Total tokens: {{ total_tokens }} (max allowed: {{ max_tokens }}). Applying strategy: {{ strategy }}.",
        "zh": "⚠️ 开始上下文剪枝。总token数: {{ total_tokens }} (最大允许: {{ max_tokens }})。正在应用策略: {{ strategy }}。"
    },
    "context_pruning_reason": {
        "en": "Context length exceeds maximum limit ({{ total_tokens }} > {{ max_tokens }}). Pruning is required to fit within the model's context window.",
        "zh": "上下文长度超过最大限制 ({{ total_tokens }} > {{ max_tokens }})。需要进行剪枝以适配模型的上下文窗口。"
    },
    "rank_code_modification_title": {
        "en": "{{model_name}} ranking codes",
        "zh": "模型{{model_name}}对代码打分"
    },
    "sorted_files_message": {
        "en": "Reordered files:\n{% for file in files %}- {{ file }}\n{% endfor %}",
        "zh": "重新排序后的文件路径:\n{% for file in files %}- {{ file }}\n{% endfor %}"
    },
    "estimated_input_tokens_in_ranking": {
        "en": "estimate input token {{ estimated_input_tokens }} when ranking",
        "zh": "排序预计输入token数: {{ estimated_input_tokens }}"
    },
    "file_snippet_procesed": {
        "en": "{{ file_path }} processed with tokens: {{ tokens }} => {{ snippet_tokens }}. Current total tokens: {{ total_tokens }}",
        "zh": "文件 {{ file_path }} 处理后token数: {{ tokens }} => {{ snippet_tokens }} 当前总token数: {{ total_tokens }}"
    },
    "tool_ask_user": {
        "en": "Your Reply: ",
        "zh": "您的回复: "
    },
    "tool_ask_user_accept": {
        "en": "Your Response received",
        "zh": "收到您的回复"
    },
    "auto_web_analyzing": {
        "en": "Analyzing web automation task...",
        "zh": "正在分析网页自动化任务..."
    },
    "auto_web_analyzed": {
        "en": "Web automation task analysis completed",
        "zh": "网页自动化任务分析完成"
    },
    "executing_web_action": {
        "en": "Executing action: {{action}} - {{description}}",
        "zh": "执行操作: {{action}} - {{description}}"
    },
    "executing_step": {
        "en": "Executing step {{step}}: {{description}}",
        "zh": "执行步骤 {{step}}: {{description}}"
    },
    "operation_cancelled": {
        "en": "Operation cancelled",
        "zh": "操作已取消"
    },
    "element_not_found": {
        "en": "Element not found: {{element}}",
        "zh": "未找到元素: {{element}}"
    },
    "analyzing_results": {
        "en": "Analyzing execution results...",
        "zh": "分析执行结果..."
    },
    "next_steps_determined": {
        "en": "Next steps determined",
        "zh": "已确定下一步操作"
    },
    "max_iterations_reached": {
        "en": "Max iterations reached ({max_iterations})",
        "zh": "已达到最大迭代次数 {{max_iterations}}"
    },
    "action_verification_failed": {
        "en": "Action verification failed: {{action}} - {{reason}}",
        "zh": "操作验证失败: {{action}} - {{reason}}"
    },
    "action_succeeded": {
        "en": "Action succeeded: {{action}}",
        "zh": "操作成功: {{action}}"
    },
    "replanned_actions": {
        "en": "Replanned {{count}} actions",
        "zh": "已重新规划 {{count}} 个操作"
    },
    "web_automation_ask_user": {
        "en": "Your answer: ",
        "zh": "您的回答: "
    },
    "filter_mode_normal": {
        "en": "Using normal filter mode for index processing...",
        "zh": "正在使用普通过滤模式处理索引..."
    },
    "filter_mode_big": {
        "en": "Index file is large ({{ tokens_len }} tokens), using big_filter mode for processing...",
        "zh": "索引文件较大 ({{ tokens_len }} tokens)，正在使用 big_filter 模式处理..."
    },
    "filter_mode_super_big": {
        "en": "Index file is very large ({{ tokens_len }} tokens), using super_big_filter mode for processing...",
        "zh": "索引文件非常大 ({{ tokens_len }} tokens)，正在使用 super_big_filter 模式处理..."
    },
    "super_big_filter_failed": {
        "en": "❌ Super big filter failed: {{ error }}.",
        "zh": "❌ 超大过滤器失败: {{ error }}."
    },
    "super_big_filter_stats": {
        "en": "{{ model_names }} Super big filter completed in {{ elapsed_time }} seconds, input tokens: {{ input_tokens }}, output tokens: {{ output_tokens }}, input cost: {{ input_cost }}, output cost: {{ output_cost }}, speed: {{ speed }} tokens/s, chunk_index: {{ chunk_index }}",
        "zh": "{{ model_names }} 超大过滤器完成耗时 {{ elapsed_time }} 秒，输入token数: {{ input_tokens }}, 输出token数: {{ output_tokens }}, 输入成本: {{ input_cost }}, 输出成本: {{ output_cost }}, 速度: {{ speed }} tokens/秒, 块索引: {{ chunk_index }}"
    },
    "super_big_filter_splitting": {
        "en": "⚠️ Index file is extremely large ({{ tokens_len }}/{{ max_tokens }}). The query will be split into {{ split_size }} chunks for processing.",
        "zh": "⚠️ 索引文件极其庞大 ({{ tokens_len }}/{{ max_tokens }})。查询将被分成 {{ split_size }} 个部分进行处理。"
    },
    "super_big_filter_title": {
        "en": "{{ model_name }} is analyzing how to filter extremely large context...",
        "zh": "{{ model_name }} 正在分析如何过滤极大规模上下文..."
    },
    "mcp_server_info_error": {
        "en": "Error getting MCP server info: {{ error }}",
        "zh": "获取MCP服务器信息时出错: {{ error }}"
    },
    "mcp_server_info_title": {
        "en": "Connected MCP Server Info",
        "zh": "已连接的MCP服务器信息"
    },
    "no_commit_file_name": {
        "en": "Cannot get the file name of the commit_id in the actions directory: {{commit_id}}",
        "zh": "无法获取commit_id关联的actions 目录下的文件名: {{commit_id}}"
    },
    "yaml_update_success": {
        "en": "✅ Successfully updated YAML file: {{yaml_file}}",
        "zh": "✅ 成功更新YAML文件: {{yaml_file}}"
    },
    "yaml_save_error": {
        "en": "❌ Error saving YAML file {{yaml_file}}: {{error}}",
        "zh": "❌ 保存YAML文件出错 {{yaml_file}}: {{error}}"
    },
    "active_context_background_task": {
        "en": "🔄 Active context generation started in background (task ID: {{task_id}})",
        "zh": "🔄 正在后台生成活动上下文 (任务ID: {{task_id}})"
    },
    "conf_not_found": {
        "en": "Configuration not found: {{path}}",
        "zh": "未找到配置文件: {{path}}"
    },
    "code_generate_title": {
        "en": "{{model_name}} is generating code",
        "zh": "{{model_name}}正在生成代码"
    },
    "generating_initial_code": {
        "en": "Generating initial code...",
        "zh": "正在生成初始代码..."
    },
    "generation_failed": {
        "en": "Code generation failed",
        "zh": "代码生成失败"
    },
    "no_files_to_lint": {
        "en": "No files to lint",
        "zh": "没有需要检查的文件"
    },
    "no_lint_errors_found": {
        "en": "No lint errors found",
        "zh": "未发现代码质量问题"
    },
    "lint_attempt_status": {
        "en": "Lint attempt {{attempt}}/{{max_correction_attempts}}: {{error_count}} errors found. {{ formatted_issues }}",
        "zh": "代码质量检查尝试 {{attempt}}/{{max_correction_attempts}}: 发现 {{error_count}} 个错误. {{ formatted_issues }}"
    },
    "max_attempts_reached": {
        "en": "Maximum correction attempts reached",
        "zh": "已达到最大修复尝试次数"
    },
    "compile_success": {
        "en": "Compile success",
        "zh": "编译成功"
    },
    "compile_failed": {
        "en": "Compile failed",
        "zh": "编译失败"
    },
    "compile_attempt_status": {
        "en": "Compile attempt {{attempt}}/{{max_correction_attempts}}: {{error_count}} errors found. {{ formatted_issues }}",
        "zh": "编译尝试 {{attempt}}/{{max_correction_attempts}}: 发现 {{error_count}} 个错误. {{ formatted_issues }}"
    },
    "max_compile_attempts_reached": {
        "en": "Maximum compilation attempts reached",
        "zh": "已达到最大编译尝试次数"
    },
    "unmerged_blocks_fixed": {
        "en": "Unmerged blocks fixed successfully",
        "zh": "未合并代码块已成功修复"
    },
    "unmerged_blocks_attempt_status": {
        "en": "Fixing unmerged blocks attempt {{attempt}}/{{max_correction_attempts}}",
        "zh": "正在尝试修复未合并代码块 {{attempt}}/{{max_correction_attempts}}"
    },
    "max_unmerged_blocks_attempts_reached": {
        "en": "Maximum unmerged blocks fix attempts reached",
        "zh": "已达到最大未合并代码块修复尝试次数"
    },
    "agenticFilterContext": {
        "en": "Start to find context...",
        "zh": "开始智能查找上下文...."
    },
    "agenticFilterContextFinished": {
        "en": "End to find context...",
        "zh": "结束智能查找上下文...."
    },
    "/context/check/start":{
        "en": "Starting missing context checking process.",
        "zh": "开始缺失上下文检查过程."
    },
    "/context/check/end": {
        "en": "Finished missing context checking process.",
        "zh": "结束缺失上下文检查过程."
    },
    "/unmerged_blocks/check/start": {
        "en": "Starting unmerged blocks checking process.",
        "zh": "开始未合并代码检查过程."
    },
    "/unmerged_blocks/check/end": {
        "en": "Finished unmerged blocks checking process.",
        "zh": "结束未合并代码检查过程."
    },
    "/lint/check/start": {
        "en": "Starting lint error checking process.",
        "zh": "开始代码质量检查过程."
    },
    "/lint/check/end": {
        "en": "Finished lint error checking process.",
        "zh": "结束代码质量检查过程."
    },
    "/compile/check/start": {
        "en": "Starting compile error checking process.",
        "zh": "开始编译错误检查过程."
    },
    "/compile/check/end": {
        "en": "Finished compile error checking process.",
        "zh": "结束编译错误检查过程."
    },
    "/agent/edit/objective":{
        "en":"Objective",
        "zh":"目标"
    },
    "/agent/edit/user_query":{
        "en":"User Query",
        "zh":"用户查询"
    },
    "/agent/edit/apply_pre_changes":{
        "en":"Commit user changes",
        "zh":"检查用户是否有手动修改(如有，会自动提交)..."
    },
    "/agent/edit/apply_changes":{
        "en":"Commit the changes in preview steps",
        "zh":"提交前面步骤的修改"
    },
    "/agent/edit/pull_request/branch_name_failed": {
        "en": "Unable to get current branch name, skipping PR creation",
        "zh": "无法获取当前分支名，跳过 PR 创建"
    },
    "/agent/edit/pull_request/title": {
        "en": "AutoCoder: {{query}}",
        "zh": "AutoCoder: {{query}}"
    },
    "/agent/edit/pull_request/default_query": {
        "en": "Code auto generation",
        "zh": "代码自动生成"
    },
    "/agent/edit/pull_request/description": {
        "en": """## 🤖 AutoCoder Generated Pull Request

**Task Description**: {{query}}

### 📝 Change Summary
- Modified {{file_count}} files
- Commit Hash: `{{commit_hash}}`

### 📂 Changed Files List
{{file_list}}

### ⚙️ Generation Configuration
- Source Branch: `{{source_branch}}`
- Target Branch: `{{target_branch}}`
- Auto-generated Time: {{timestamp}}

### 🔍 Next Steps
- [ ] Code Review
- [ ] Test Verification
- [ ] Merge to Main Branch

---
*This PR was automatically created by AutoCoder*
""",
        "zh": """## 🤖 AutoCoder 自动生成的 Pull Request

**任务描述**: {{query}}

### 📝 变更摘要
- 共修改 {{file_count}} 个文件
- 提交哈希: `{{commit_hash}}`

### 📂 变更文件列表
{{file_list}}

### ⚙️ 生成配置
- 源分支: `{{source_branch}}`
- 目标分支: `{{target_branch}}`
- 自动生成时间: {{timestamp}}

### 🔍 下一步
- [ ] 代码审查
- [ ] 测试验证
- [ ] 合并到主分支

---
*此 PR 由 AutoCoder 自动创建*
"""
    },
    "/agent/edit/pull_request/creating": {
        "en": "Creating Pull Request: {{title}}",
        "zh": "正在创建 Pull Request: {{title}}"
    },
    "/agent/edit/pull_request/success": {
        "en": "✅ Pull Request created successfully",
        "zh": "✅ Pull Request 创建成功"
    },
    "/agent/edit/pull_request/failed": {
        "en": "❌ Pull Request creation failed: {{error}}",
        "zh": "❌ Pull Request 创建失败: {{error}}"
    },
    "/agent/edit/pull_request/exception": {
        "en": "❌ Exception occurred while creating Pull Request: {{error}}",
        "zh": "❌ 创建 Pull Request 时发生异常: {{error}}"
    }
}


# 新增 ReplaceInFileToolResolver 国际化消息
MESSAGES.update({
    "replace_in_file.access_denied": {
        "en": "Error: Access denied. Attempted to modify file outside the project directory: {{file_path}}",
        "zh": "错误：拒绝访问。尝试修改项目目录之外的文件：{{file_path}}"
    },
    "replace_in_file.file_not_found": {
        "en": "Error: File not found at path: {{file_path}}",
        "zh": "错误：未找到文件路径：{{file_path}}"
    },
    "replace_in_file.read_error": {
        "en": "An error occurred while reading the file for replacement: {{error}}",
        "zh": "读取待替换文件时发生错误：{{error}}"
    },
    "replace_in_file.no_valid_blocks": {
        "en": "Error: No valid SEARCH/REPLACE blocks found in the provided diff.",
        "zh": "错误：在提供的diff中未找到有效的SEARCH/REPLACE代码块。"
    },
    "replace_in_file.apply_failed": {
        "en": "Failed to apply any changes. Errors:\n{{errors}}",
        "zh": "未能应用任何更改。错误信息：\n{{errors}}"
    },
    "replace_in_file.apply_success": {
        "en": "Successfully applied {{applied}}/{{total}} changes to file: {{file_path}}.",
        "zh": "成功应用了 {{applied}}/{{total}} 个更改到文件：{{file_path}}。"
    },
    "replace_in_file.apply_success_with_warnings": {
        "en": "Successfully applied {{applied}}/{{total}} changes to file: {{file_path}}.\nWarnings:\n{{errors}}",
        "zh": "成功应用了 {{applied}}/{{total}} 个更改到文件：{{file_path}}。\n警告信息：\n{{errors}}"
    },
    "replace_in_file.write_error": {
        "en": "An error occurred while writing the modified file: {{error}}",
        "zh": "写入修改后的文件时发生错误：{{error}}"
    }
})

def get_system_language():
    try:
        return locale.getdefaultlocale()[0][:2]
    except:
        return 'en'


def get_message(key):
    lang = get_system_language()
    if key in MESSAGES:
        return MESSAGES[key].get(lang, MESSAGES[key].get("en", ""))
    return ""


def get_message_with_format(msg_key: str, **kwargs):
    return format_str_jinja2(get_message(msg_key), **kwargs)
