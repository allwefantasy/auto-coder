
from byzerllm.utils import format_str_jinja2
import locale

MESSAGES = {
    # 原有内容保持不变
    ...
    # 新增replace_in_file相关国际化
    "replace_access_denied": {
        "en": "Error: Access denied. Attempted to modify file outside the project directory: {{file_path}}",
        "zh": "错误：拒绝访问。试图修改项目目录之外的文件：{{file_path}}"
    },
    "replace_file_not_found": {
        "en": "Error: File not found at path: {{file_path}}",
        "zh": "错误：未找到文件，路径为：{{file_path}}"
    },
    "replace_read_error": {
        "en": "An error occurred while reading the file for replacement: {{error}}",
        "zh": "读取文件时发生错误：{{error}}"
    },
    "replace_invalid_diff": {
        "en": "Error: No valid SEARCH/REPLACE blocks found in the provided diff.",
        "zh": "错误：在提供的diff中未找到有效的搜索/替换块。"
    },
    "replace_apply_failed": {
        "en": "Failed to apply any changes. Errors:\n{{errors}}",
        "zh": "未能应用任何更改。错误信息：\n{{errors}}"
    },
    "replace_success": {
        "en": "Successfully applied {{applied_count}}/{{total_blocks}} changes to file: {{file_path}}.",
        "zh": "成功将 {{applied_count}}/{{total_blocks}} 处更改应用到文件：{{file_path}}。"
    },
    "replace_write_error": {
        "en": "An error occurred while writing the modified file: {{error}}",
        "zh": "写入修改后的文件时发生错误：{{error}}"
    },
}

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
