# ... (保留原有代码)

MESSAGES = {
    "en": {
        # ... (保留原有消息)
        "quick_filter_too_long": "⚠️ index file is too large ({{ tokens_len }}/{{ max_tokens }}). Please use '/conf /drop index_filter_model' to fallback to normal_filter mode.",
        "quick_filter_title": "{{ model_name }} is analyzing how to filter context...",
        "quick_filter_failed": "❌ Quick filter failed: {{ error }}. ",
        "quick_filter_reason": "Auto get(quick_filter mode)",
        # ... (其他消息)
    },
    "zh": {
        # ... (保留原有消息)
        "quick_filter_too_long": "⚠️ 索引文件过大 ({{ tokens_len }}/{{ max_tokens }})。请使用 '/conf /drop index_filter_model' 回退到 normal_filter 模式。",
        "quick_filter_title": "{{ model_name }} 正在分析如何筛选上下文...",
        "quick_filter_failed": "❌ 快速过滤器失败: {{ error }}. ",
        "quick_filter_reason": "自动获取(quick_filter模式)",
        # ... (其他消息)
    }
}

# ... (保留其他代码)