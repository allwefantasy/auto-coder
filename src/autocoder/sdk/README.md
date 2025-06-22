
# Auto-Coder SDK

Auto-Coder SDK 是一个为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。

## 目录结构

```
src/autocoder/sdk/
├── __init__.py                 # SDK主入口，提供公共API
├── constants.py               # 常量定义（版本、默认值、配置选项等）
├── exceptions.py              # 自定义异常类
├── cli/                       # 命令行接口模块
│   ├── __init__.py
│   ├── __main__.py           # CLI模块入口点
│   ├── completion_wrapper.py # 自动补全包装器
│   ├── formatters.py         # 输出格式化器
│   ├── handlers.py           # 命令处理器（打印模式、会话模式）
│   ├── install_completion.py # 自动补全安装脚本
│   ├── main.py               # CLI主入口点
│   └── options.py            # CLI选项定义
├── core/                      # 核心功能模块
│   ├── __init__.py
│   ├── auto_coder_core.py    # AutoCoder核心封装类
│   └── bridge.py             # 桥接层，连接现有功能
├── models/                    # 数据模型
│   ├── __init__.py
│   ├── options.py            # 配置选项模型
│   ├── messages.py           # 消息模型
│   └── responses.py          # 响应模型
├── session/                   # 会话管理
│   ├── __init__.py
│   ├── session.py            # 单个会话类
│   └── session_manager.py    # 会话管理器
└── utils/                     # 工具函数
    ├── __init__.py
    ├── formatters.py         # 格式化工具
    ├── io_utils.py           # IO工具
    └── validators.py         # 验证工具
```

## 快速开始

### 0. 模型配置

编辑 `~/.auto-coder/keys/models.json` 文件，增加如下配置（这里是配置v3）：


```json
[
{
    "name": "deepseek/v3",
    "description": "DeepSeek Chat is for coding",
    "model_name": "deepseek-chat",
    "model_type": "saas/openai",
    "base_url": "https://api.deepseek.com/v1",
    "api_key_path": "api.deepseek.com",
    "is_reasoning": false,
    "input_price": 0,
    "output_price": 0,
    "average_speed": 0,
    "max_output_tokens": 8096,    
}
]
```

然后将 API KEY 放到同目录下的 `api.deepseek.com` 文件里即可。

后续你就可以使用名字 'deepseek/v3' 来引用这个模型了。

### 1. 命令行工具使用

#### 安装和基本使用

```bash
# 单次运行模式
auto-coder.run --model v3_chat "Write a function to calculate Fibonacci numbers" 

# 通过管道提供输入
echo "Explain this code" | auto-coder.run

# 指定输出格式
auto-coder.run  "Generate a hello world function" --output-format json

# 继续最近的对话
auto-coder.run --continue "继续修改xxxxx"

# Resume a specific conversation by session ID
auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000 "" 
```

#### 高级选项

```bash
# 设置最大对话轮数
auto-coder.run --max-turns 5 "Help me debug this code" 
```

### 2. Python API 使用

#### 基本查询

```python
import asyncio
from autocoder.sdk import query, query_sync, AutoCodeOptions

# 同步查询
response = query_sync("Write a function to calculate Fibonacci numbers",options = AutoCodeOptions(                
        model="v3_chat"
    ))
print(response)

# 异步查询
async def async_example():
    options = AutoCodeOptions(                
        model="v3_chat"
    )
    
    async for message in query("Explain how Python decorators work", options):
        print(f"[{message.role}] {message.content}")

asyncio.run(async_example())
```

#### 配置选项

```python
from autocoder.sdk import AutoCodeOptions

# 创建配置
options = AutoCodeOptions(
    max_turns=10,                    # 最大对话轮数
    system_prompt="You are a helpful coding assistant",  # 系统提示
    cwd="/path/to/project",          # 工作目录
    allowed_tools=["Read", "Write", "Bash"],  # 允许的工具
    permission_mode="acceptedits",    # 权限模式
    output_format="json",            # 输出格式
    stream=True,                     # 流式输出
    model="gpt-4",                   # 模型名称
    temperature=0.3,                 # 温度参数
    timeout=60,                      # 超时时间
    verbose=True,                    # 详细输出
    include_project_structure=True   # 包含项目结构
)

# 验证配置
options.validate()

# 转换为字典
config_dict = options.to_dict()

# 从字典创建
new_options = AutoCodeOptions.from_dict(config_dict)
```



