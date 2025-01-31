import locale

MESSAGES = {
    "en": {
        "human_as_model_instructions": (
            "You are now in Human as Model mode. The content has been copied to your clipboard.\n"
            "The system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\n"
            "Use '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again."
        ),
        "clipboard_not_supported": (
            "pyperclip not installed or clipboard is not supported, instruction will not be copied to clipboard."
        ),
        "human_as_model_instructions_no_clipboard": (
            "You are now in Human as Model mode. [bold red]The content could not be copied to your clipboard.[/bold red]\n"
            "but you can copy prompt from output.txt file.\n"
            "The system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\n"
            "Use '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again."
        ),
        "phase1_processing_sources": "Phase 1: Processing REST/RAG/Search sources...",
        "phase2_building_index": "Phase 2: Building index for all files...",
        "phase6_file_selection": "Phase 6: Processing file selection and limits...",
        "phase7_preparing_output": "Phase 7: Preparing final output...",
        "phase1_processing_sources": "阶段 1: 正在处理 REST/RAG/Search 源...",
        "phase2_building_index": "阶段 2: 正在为所有文件构建索引...",
        "phase6_file_selection": "阶段 6: 正在处理文件选择和限制...",
        "phase7_preparing_output": "阶段 7: 正在准备最终输出...",
        "chat_human_as_model_instructions": (
            "Chat is now in Human as Model mode.\n"
            "The question has been copied to your clipboard.\n"
            "Please use Web version model to get the answer.\n"
            "Or use /conf human_as_model:false to close this mode and get the answer in terminal directly."
            "Paste the answer to the input box below, use '/break' to exit, '/clear' to clear the screen, '/eof' to submit."
        )
    },
    "zh": {
        "human_as_model_instructions": (
            "您现在处于人类作为模型模式。内容已复制到您的剪贴板。\n"
            "系统正在等待您的输入。完成后，在新行输入'EOF'提交。\n"
            "使用'/break'退出此模式。如果复制粘贴有问题，使用'/clear'清理并重新粘贴。"
        ),
        "clipboard_not_supported": (
            "未安装pyperclip或不支持剪贴板，指令将不会被复制到剪贴板。"
        ),
        "human_as_model_instructions_no_clipboard": (
            "您现在处于人类作为模型模式。[bold red]内容无法复制到您的剪贴板。[/bold red]\n"
            "但您可以从output.txt文件复制提示。\n"
            "系统正在等待您的输入。完成后，在新行输入'EOF'提交。\n"
            "使用'/break'退出此模式。如果复制粘贴有问题，使用'/clear'清理并重新粘贴。"
        ),
        "chat_human_as_model_instructions": (
            "\n============= Chat 处于 Human as Model 模式 =============\n"
            "问题已复制到剪贴板\n"
            "请使用Web版本模型获取答案\n"
            "或者使用 /conf human_as_model:false 关闭该模式直接在终端获得答案。" 
            "将获得答案黏贴到下面的输入框，换行后，使用 '/break' 退出，'/clear' 清屏，'/eof' 提交。"           
        ),
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