

"""
Auto-Coder SDK 常量定义

定义SDK中使用的各种常量，包括默认值、配置选项、错误码等。
"""

# 版本信息
SDK_VERSION = "0.1.0"

# 默认配置
DEFAULT_MAX_TURNS = 3
DEFAULT_OUTPUT_FORMAT = "text"
DEFAULT_PERMISSION_MODE = "manual"
DEFAULT_SESSION_TIMEOUT = 3600  # 1小时
DEFAULT_MODEL = "deepseek/v3"  # 默认使用的模型

# 支持的输出格式
OUTPUT_FORMATS = {
    "text": "纯文本格式",
    "json": "JSON格式",
    "stream-json": "流式JSON格式"
}

# 支持的输入格式
INPUT_FORMATS = {
    "text": "纯文本格式",
    "json": "JSON格式",
    "stream-json": "流式JSON格式"
}

# 权限模式
PERMISSION_MODES = {
    "manual": "手动确认每个操作",
    "acceptedits": "自动接受文件编辑",
    "acceptall": "自动接受所有操作"
}

# 支持的工具
ALLOWED_TOOLS = [
    "Read",       # 文件读取
    "Write",      # 文件写入
    "Bash",       # 命令执行
    "Search",     # 文件搜索
    "Index",      # 索引操作
    "Chat",       # 对话
    "Design"      # 设计
]

# CLI相关常量
CLI_COMMAND_NAME = "auto-coder.run"
CLI_EXIT_SUCCESS = 0
CLI_EXIT_ERROR = 1
CLI_EXIT_INVALID_ARGS = 2

# 会话相关常量
SESSION_DIR_NAME = ".auto-coder/sdk/sessions"
SESSION_FILE_EXTENSION = ".json"
MAX_SESSIONS_TO_KEEP = 100

# 文件和目录
DEFAULT_PROJECT_ROOT = "."
CONFIG_FILE_NAME = ".auto-coder-sdk.json"

# 网络和超时
DEFAULT_TIMEOUT = 30
MAX_RETRY_ATTEMPTS = 3

# 日志级别
LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

# 错误码
ERROR_CODES = {
    "SDK_ERROR": "SDK通用错误",
    "SESSION_NOT_FOUND": "会话未找到",
    "INVALID_OPTIONS": "无效选项",
    "BRIDGE_ERROR": "桥接层错误",
    "CLI_ERROR": "CLI错误",
    "VALIDATION_ERROR": "验证错误",
    "TIMEOUT_ERROR": "超时错误",
    "NETWORK_ERROR": "网络错误"
}

# 消息类型
MESSAGE_ROLES = {
    "user": "用户消息",
    "assistant": "助手消息",
    "system": "系统消息"
}

# 流式输出标记
STREAM_START_MARKER = "<<STREAM_START>>"
STREAM_END_MARKER = "<<STREAM_END>>"
STREAM_ERROR_MARKER = "<<STREAM_ERROR>>"

