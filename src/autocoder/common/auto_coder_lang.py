import locale

MESSAGES = {
    "en": {
        "initializing": "🚀 Initializing system...",
        "index_file_too_large": "⚠️ File {{ file_path }} is too large ({{ file_size }} > {{ max_length }}), splitting into chunks...",
        "index_update_success": "✅ Successfully updated index for {{ file_path }} (md5: {{ md5 }}) in {{ duration:.2f }}s",
        "index_build_error": "❌ Error building index for {{ file_path }}: {{ error }}",
        "index_build_summary": "📊 Total Files: {{ total_files }}, Need to Build Index: {{ num_files }}",
        "building_index_progress": "⏳ Building Index: {{ counter }}/{{ num_files }}...",
        "index_source_dir_mismatch": "⚠️ Source directory mismatch (file_path: {{ file_path }}, source_dir: {{ source_dir }})",
        "index_related_files_fail": "⚠️ Failed to find related files for chunk {{ chunk_count }}",
        "index_threads_completed": "✅ Completed {{ completed_threads }}/{{ total_threads }} threads",
        "index_related_files_fail": "⚠️ Failed to find related files for chunk {{ chunk_count }}"
    },
    "zh": {
        "initializing": "🚀 正在初始化系统...",
        "index_file_too_large": "⚠️ 文件 {{ file_path }} 过大 ({{ file_size }} > {{ max_length }}), 正在分块处理...",
        "index_update_success": "✅ 成功更新 {{ file_path }} 的索引 (md5: {{ md5 }}), 耗时 {{ duration:.2f }} 秒",
        "index_build_error": "❌ 构建 {{ file_path }} 索引时出错: {{ error }}",
        "index_build_summary": "📊 总文件数: {{ total_files }}, 需要构建索引: {{ num_files }}",
        "building_index_progress": "⏳ 正在构建索引: {{ counter }}/{{ num_files }}...",
        "index_source_dir_mismatch": "⚠️ 源目录不匹配 (文件路径: {{ file_path }}, 源目录: {{ source_dir }})",
        "index_related_files_fail": "⚠️ 无法为块 {{ chunk_count }} 找到相关文件",
        "index_threads_completed": "✅ 已完成 {{ completed_threads }}/{{ total_threads }} 个线程",
        "index_related_files_fail": "⚠️ 无法为块 {{ chunk_count }} 找到相关文件"
    }
}


def get_system_language():
    try:
        return locale.getdefaultlocale()[0][:2]
    except:
        return 'en'


def get_message(key):
    lang = get_system_language()
    return MESSAGES.get(lang, MESSAGES['en']).get(key, MESSAGES['en'][key])
