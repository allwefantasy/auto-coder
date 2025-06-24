# AC Style Command Parser

这是一个用于解析命令行风格查询字符串的模块，主要用于AutoCoder项目中处理复杂的命令和参数组合。

## 功能特性

- 支持多种命令格式解析
- 支持带引号的参数值（包含空格）
- 智能区分路径和命令
- 支持键值对参数
- 支持多命令组合

## 支持的命令格式

1. **基本命令格式**
   ```
   /command arg1 arg2
   ```

2. **键值对参数**
   ```
   /command key1=value1 key2=value2
   ```

3. **混合参数**
   ```
   /command arg1 key1=value1
   ```

4. **多命令组合**
   ```
   /command1 arg1 /command2 arg2
   /command1 /command2 arg2
   /command1 /command2 key=value
   ```

5. **带引号的参数（支持空格）**
   ```
   /command key="value with spaces"
   /command key='value with spaces'
   /command "argument with spaces"
   ```

6. **路径处理**
   ```
   /command /path/to/file.txt  # /path/to/file.txt不会被识别为命令
   ```

## 在AutoCoder中的使用

### 主要使用场景

在`auto_coder_runner.py`中，CommandParser主要用于解析以下场景的命令：

1. **聊天命令解析（chat函数）**
   ```python
   # 解析查询命令
   commands_infos = CommandParser.parse_query(query)
   
   # 检查是否包含特定命令
   if "query" in commands_infos:
       query = " ".join(commands_infos["query"]["args"])
   
   # 检查是否是新会话
   is_new = "new" in commands_infos
   
   # 特殊命令处理
   if "learn" in commands_infos:
       commands_infos["no_context"] = {}
   
   if "review" in commands_infos:
       commands_infos["no_context"] = {}
   ```

2. **活动上下文管理（active_context函数）**
   ```python
   # 解析命令参数
   commands_infos = CommandParser.parse_query(query)
   command = "list"  # 默认命令
   
   if len(commands_infos) > 0:
       if "list" in commands_infos:
           command = "list"
       if "run" in commands_infos:
           command = "run"
   ```

### 常见使用模式

1. **提取命令参数**
   ```python
   commands = parse_query("/learn hello world /commit 123456")
   # 结果: {
   #     'learn': {'args': ['hello', 'world'], 'kwargs': {}},
   #     'commit': {'args': ['123456'], 'kwargs': {}}
   # }
   ```

2. **检查命令存在性**
   ```python
   if "new" in commands_infos:
       # 处理新会话逻辑
       pass
   ```

3. **获取命令参数**
   ```python
   if "run" in commands_infos:
       file_name = commands_infos["run"]["args"][-1]
   ```

## API参考

### 类和函数

#### `CommandParser`类

主要的命令解析器类。

**方法：**
- `parse(query: str) -> Dict[str, Any]`: 解析命令字符串
- `parse_command(query: str, command: str) -> Optional[Dict[str, Any]]`: 解析特定命令
- `_parse_params(params_str: str) -> Tuple[List[str], Dict[str, str]]`: 内部参数解析方法

#### 便捷函数

- `parse_query(query: str) -> Dict[str, Any]`: 解析命令的便捷函数（推荐使用）
- `has_command(query: str, command: str) -> bool`: 检查是否包含特定命令
- `get_command_args(query: str, command: str) -> List[str]`: 获取命令的位置参数
- `get_command_kwargs(query: str, command: str) -> Dict[str, str]`: 获取命令的键值对参数

## 使用示例

### 基本使用

```python
from autocoder.common.ac_style_command_parser import parse_query

# 解析命令
result = parse_query("/learn hello world /commit 123456")
print(result)
# 输出:
# {
#     'learn': {'args': ['hello', 'world'], 'kwargs': {}},
#     'commit': {'args': ['123456'], 'kwargs': {}}
# }
```

### 高级使用

```python
from autocoder.common.ac_style_command_parser import (
    parse_query, has_command, get_command_args
)

query = '/learn msg="hello world" /commit commit_id=123456'

# 解析完整命令
commands = parse_query(query)

# 检查命令存在
if has_command(query, "learn"):
    print("Found learn command")

# 获取特定命令的参数
commit_args = get_command_args(query, "commit")
print(f"Commit args: {commit_args}")
```

### 在AutoCoder项目中的典型用法

```python
# 在chat函数中的使用模式
def chat(query: str):
    # 解析命令
    commands_infos = parse_query(query)
    
    # 提取查询内容
    if "query" in commands_infos:
        query = " ".join(commands_infos["query"]["args"])
    else:
        # 如果没有显式的query命令，使用其他命令的参数
        temp_query = ""
        for (command, command_info) in commands_infos.items():
            if command_info["args"]:
                temp_query = " ".join(command_info["args"])
        query = temp_query
    
    # 检查特殊标志
    is_new = "new" in commands_infos
    
    # 特殊命令处理
    if "learn" in commands_infos:
        commands_infos["no_context"] = {}
    
    if "review" in commands_infos:
        commands_infos["no_context"] = {}
    
    # 继续处理...
```

## 注意事项

1. **路径 vs 命令**: 解析器会智能区分路径（如`/path/to/file`）和命令（如`/command`）
2. **引号处理**: 支持双引号和单引号，引号内的空格会被保留
3. **参数类型**: 返回的参数分为位置参数（args）和键值对参数（kwargs）
4. **命令名限制**: 命令名只能包含字母、数字和下划线

## 迁移说明

此模块从`src/autocoder/command_parser.py`迁移而来，位于`src/autocoder/common/ac_style_command_parser/`目录下。

如果你的代码中使用了旧的导入方式，请更新为：

```python
# 旧的导入方式
from autocoder.command_parser import CommandParser, parse_query

# 新的导入方式
from autocoder.common.ac_style_command_parser import CommandParser, parse_query
``` 