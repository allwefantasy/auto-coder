from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.styles import Style

# 设置样式
style = Style.from_dict({
    'username': '#884444',
    'at': '#00aa00',
    'colon': '#0000aa',
    'pound': '#00aa00',
    'host': '#00ffff bg:#444400',
})

# 设置提示信息
prompt_message = [
    ('class:username', 'user'),
    ('class:at', '@'),
    ('class:host', 'localhost'),
    ('class:colon', ':'),
    ('class:pound', '$ '),
]

# 创建会话
session = PromptSession()

# 获取用户输入
user_input = session.prompt(FormattedText(prompt_message), style=style)

print(f"You entered: {user_input}")