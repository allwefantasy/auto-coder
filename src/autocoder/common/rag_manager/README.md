# RAGManager 使用说明

RAGManager 是用于管理和配置 RAG（Retrieval-Augmented Generation）服务器的组件，支持项目级别和全局级别的配置。

## 配置文件格式

### 项目级别配置

优先级：高

路径：`{项目根目录}/.auto-coder/auto-coder.web/rags/rags.json`

格式：
```json
{
  "data": [
    {
      "name": "uv知识库",
      "base_url": "http://127.0.0.1:8107/v1",
      "api_key": "xxxx",
      "description": "uv知识库"
    },
    {
      "name": "Python文档",
      "base_url": "http://127.0.0.1:8108/v1",
      "api_key": "yyyy",
      "description": "Python官方文档知识库"
    }
  ]
}
```

### 全局级别配置

优先级：低（仅在项目级别配置不存在时使用）

路径：`~/.auto-coder/keys/rags.json`

格式：
```json
{
  "moonbit": {
    "name": "moonbit",
    "port": 8109,
    "host": "127.0.0.1",
    "doc_dir": "/Users/allwefantasy/projects/rags/moonbit-docs",
    "model": "ark_v3_0324_chat",
    "description": "MoonBit语言文档知识库"
  },
  "rust": {
    "name": "rust",
    "port": 8110,
    "host": "127.0.0.1",
    "doc_dir": "/Users/allwefantasy/projects/rags/rust-docs",
    "model": "qwen2-7b",
    "description": "Rust语言文档知识库"
  }
}
```

注意：全局配置中的 `host` 和 `port` 会被自动组合为 `http://{host}:{port}/v1` 格式的 server_name。

## 使用方式

### 在代码中使用

```python
from autocoder.common.rag_manager import RAGManager
from autocoder.common import AutoCoderArgs

# 初始化
args = AutoCoderArgs(source_dir="/path/to/project")
rag_manager = RAGManager(args)

# 检查是否有配置
if rag_manager.has_configs():
    # 获取所有配置
    configs = rag_manager.get_all_configs()
    
    # 根据名称获取特定配置
    config = rag_manager.get_config_by_name("uv知识库")
    
    # 获取配置信息字符串
    info = rag_manager.get_config_info()
    print(info)
```

### 在 AgenticEdit 中使用

RAGManager 已经集成到 AgenticEdit 中，可以通过 `use_rag_tool` 工具使用：

```xml
<use_rag_tool>
<server_name>uv知识库</server_name>
<query>如何安装和使用 uv？</query>
</use_rag_tool>
```

如果不指定 `server_name`，将使用第一个可用的 RAG 配置。

## API 参考

### RAGConfig

RAG 配置项模型：

- `name: str` - 配置名称
- `server_name: str` - 服务器地址
- `api_key: Optional[str]` - API 密钥（可选）
- `description: Optional[str]` - 描述信息（可选）

### RAGManager

主要方法：

- `get_all_configs() -> List[RAGConfig]` - 获取所有配置
- `get_config_by_name(name: str) -> Optional[RAGConfig]` - 根据名称获取配置
- `get_server_names() -> List[str]` - 获取所有服务器地址
- `get_config_info() -> str` - 获取格式化的配置信息
- `has_configs() -> bool` - 检查是否有可用配置

## 错误处理

RAGManager 会自动处理以下错误情况：

1. 配置文件不存在 - 记录警告信息
2. JSON 格式错误 - 记录错误信息并跳过该配置
3. 配置项缺少必要字段 - 记录错误信息并跳过该项

所有错误都会通过 loguru 记录，不会中断程序执行。 