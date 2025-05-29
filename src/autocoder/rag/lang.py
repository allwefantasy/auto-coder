import locale
from byzerllm.utils import format_str_jinja2

MESSAGES = {
    "rag_error_title": {
        "en": "RAG Error",
        "zh": "RAG 错误"
    },
    "rag_error_message": {
        "en": "Failed to generate response: {{error}}",
        "zh": "生成响应失败: {{error}}"
    },
    "rag_searching_docs": {
        "en": "Searching documents with {{model}}...",
        "zh": "正在使用 {{model}} 搜索文档..."
    },
    "rag_docs_filter_result": {
        "en": "{{model}} processed {{docs_num}} documents, cost {{filter_time}} seconds, input tokens: {{input_tokens}}, output tokens: {{output_tokens}}",
        "zh": "{{model}} 处理了 {{docs_num}} 个文档, 耗时 {{filter_time}} 秒, 输入 tokens: {{input_tokens}}, 输出 tokens: {{output_tokens}}"
    },
    "dynamic_chunking_start": {
        "en": "Dynamic chunking start with {{model}}",
        "zh": "使用 {{model}} 进行动态分块"
    },
    "dynamic_chunking_result": {
        "en": "Dynamic chunking result with {{model}}, first round cost {{first_round_time}} seconds, second round cost {{sencond_round_time}} seconds, input tokens: {{input_tokens}}, output tokens: {{output_tokens}}, first round full docs: {{first_round_full_docs}}, second round extracted docs: {{second_round_extracted_docs}}",
        "zh": "使用 {{model}} 进行动态分块, 第一轮耗时 {{first_round_time}} 秒, 第二轮耗时 {{sencond_round_time}} 秒, 输入 tokens: {{input_tokens}}, 输出 tokens: {{output_tokens}}, 第一轮全量文档: {{first_round_full_docs}}, 第二轮提取文档: {{second_round_extracted_docs}}"
    },
    "send_to_model": {
        "en": "Send to model {{model}} with {{tokens}} tokens",
        "zh": "发送给模型 {{model}} 的 tokens 数量预估为 {{tokens}}"
    },
    "doc_filter_start": {
        "en": "Document filtering start, total {{total}} documents",
        "zh": "开始过滤文档，共 {{total}} 个文档"
    },
    "doc_filter_progress": {
        "en": "Document filtering progress: {{progress_percent}}% processed {{relevant_count}}/{{total}} documents",
        "zh": "文档过滤进度：{{progress_percent}}%，处理了 {{relevant_count}}/{{total}} 个文档"
    },
    "doc_filter_error": {
        "en": "Document filtering error: {{error}}",
        "zh": "文档过滤错误：{{error}}"
    },
    "doc_filter_complete": {
        "en": "Document filtering complete, cost {{total_time}} seconds, found {{relevant_count}} relevant documents",
        "zh": "文档过滤完成，耗时 {{total_time}} 秒，找到 {{relevant_count}} 个相关文档"
    },
    "context_docs_names": {
        "en": "The following are the documents related to the user's question: {{context_docs_names}}",
        "zh": "以下是和用户问题相关的文档：{{context_docs_names}}"
    },
    "rag_processing": {
        "en": "Processing...\n",
        "zh": "处理中...\n"
    }
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

def get_message_with_format_and_newline(msg_key: str, **kwargs):
    return format_str_jinja2(get_message(msg_key), **kwargs) + "\n"
