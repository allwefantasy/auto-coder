import locale
from byzerllm.utils import format_str_jinja2

MESSAGES = {
    "en": {
        "rag_error_title": "RAG Error",
        "rag_error_message": "Failed to generate response: {{error}}",
        "rag_searching_docs": "Searching documents with {{model}}...",
        "rag_docs_filter_result": "{{model}} found {{docs_num}} documents, cost {{filter_time}} seconds, input tokens: {{input_tokens}}, output tokens: {{output_tokens}}",
        "dynamic_chunking_start": "Dynamic chunking start with {{model}}",
        "dynamic_chunking_result": "Dynamic chunking result with {{model}}, first round cost {{first_round_time}} seconds, second round cost {{sencond_round_time}} seconds, input tokens: {{input_tokens}}, output tokens: {{output_tokens}}, first round full docs: {{first_round_full_docs}}, second round extracted docs: {{second_round_extracted_docs}}",
        "send_to_model": "Send to model {{model}} with {{tokens}} tokens",
    },
    "zh": {
        "rag_error_title": "RAG 错误",
        "rag_error_message": "生成响应失败: {{error}}",
        "rag_searching_docs": "正在使用 {{model}} 搜索文档...",
        "rag_docs_filter_result": "{{model}} 找到 {{docs_num}} 个文档, 耗时 {{filter_time}} 秒, 输入 tokens: {{input_tokens}}, 输出 tokens: {{output_tokens}}",
        "dynamic_chunking_start": "使用 {{model}} 进行动态分块",
        "dynamic_chunking_result": "使用 {{model}} 进行动态分块, 第一轮耗时 {{first_round_time}} 秒, 第二轮耗时 {{sencond_round_time}} 秒, 输入 tokens: {{input_tokens}}, 输出 tokens: {{output_tokens}}, 第一轮全量文档: {{first_round_full_docs}}, 第二轮提取文档: {{second_round_extracted_docs}}",
        "send_to_model": "发送给模型 {{model}} 的 tokens 数量预估为 {{tokens}}",
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


def get_message_with_format(msg_key: str, **kwargs):
    return format_str_jinja2(get_message(msg_key), **kwargs)
