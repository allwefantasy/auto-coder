

# Auto-Coder CLI 自动补全功能

Auto-Coder CLI 提供了强大的命令行自动补全功能，支持 Bash、Zsh 和 Fish shell。

## 功能特性

- **参数补全**: 自动补全命令行选项和参数
- **工具名称补全**: 为 `--allowed-tools` 参数提供可用工具列表
- **会话ID补全**: 为 `--resume` 参数提供会话ID建议
- **提示内容补全**: 为 prompt 参数提供常用提示模板
- **多Shell支持**: 支持 Bash、Zsh 和 Fish shell

## 安装自动补全

### 自动安装（推荐）

使用内置的安装脚本：

```bash
# 安装自动补全
python -m autocoder.sdk.cli install

# 强制重新安装
python -m autocoder.sdk.cli install --force
```

### 手动安装

#### Bash

将以下内容添加到 `~/.bashrc` 或 `~/.bash_profile`:

```bash
# Auto-Coder CLI 自动补全
eval "$(register-python-argcomplete auto-coder.run)"
```

#### Zsh

将以下内容添加到 `~/.zshrc`:

```bash
# 启用 bash 兼容模式用于补全
autoload -U +X bashcompinit && bashcompinit
# Auto-Coder CLI 自动补全
eval "$(register-python-argcomplete auto-coder.run)"
```

#### Fish

将以下内容添加到 `~/.config/fish/config.fish`:

```fish
# Auto-Coder CLI 自动补全
register-python-argcomplete --shell fish auto-coder.run | source
```

## 使用自动补全

安装完成后，重新加载 shell 配置：

```bash
# Bash/Zsh
source ~/.bashrc  # 或 ~/.zshrc

# Fish
source ~/.config/fish/config.fish
```

然后就可以使用 Tab 键进行自动补全了：

```bash
# 补全命令选项
auto-coder.run --<TAB>

# 补全工具名称
auto-coder.run --allowed-tools <TAB>

# 补全提示内容
auto-coder.run -p <TAB>

# 补全会话ID
auto-coder.run --resume <TAB>
```

## 补全功能详解

### 1. 命令选项补全

支持所有命令行选项的补全：
- `-p, --print`: 单次运行模式
- `-c, --continue`: 继续最近的对话
- `-r, --resume`: 恢复特定会话
- `--output-format`: 输出格式选择
- `--input-format`: 输入格式选择
- `--max-turns`: 最大对话轮数
- `--allowed-tools`: 允许使用的工具列表
- `--permission-mode`: 权限模式

### 2. 工具名称补全

为 `--allowed-tools` 参数提供可用工具列表：
- `execute_command`
- `read_file`
- `write_to_file`
- `replace_in_file`
- `search_files`
- `list_files`
- `list_code_definition_names`
- `ask_followup_question`
- `attempt_completion`
- `list_package_info`
- `mcp_tool`
- `rag_tool`

### 3. 提示内容补全

为 prompt 参数提供常用提示模板：
- "Write a function to calculate Fibonacci numbers"
- "Explain this code"
- "Generate a hello world function"
- "Create a simple web page"
- "Write unit tests for this code"
- "Refactor this function"
- "Add error handling"
- "Optimize this algorithm"
- "Document this code"
- "Fix the bug in this code"

### 4. 会话ID补全

为 `--resume` 参数提供会话ID格式示例（实际使用中会从会话存储中获取真实的会话ID）。

## 管理自动补全

### 测试自动补全

```bash
# 测试自动补全功能是否正常工作
python -m autocoder.sdk.cli test
```

### 卸载自动补全

```bash
# 卸载自动补全功能
python -m autocoder.sdk.cli uninstall
```

## 故障排除

### 1. 自动补全不工作

检查以下几点：
- 确保 `argcomplete` 包已安装：`pip install argcomplete`
- 确保 `register-python-argcomplete` 命令可用
- 重新加载 shell 配置文件
- 检查 shell 配置文件中的补全脚本是否正确

### 2. 权限问题

如果遇到权限问题，确保有写入 shell 配置文件的权限。

### 3. 多个 Python 环境

如果使用多个 Python 环境（如 conda、virtualenv），确保在正确的环境中安装了 `argcomplete` 和 `auto-coder`。

## 高级配置

### 自定义补全器

可以通过修改 `src/autocoder/sdk/cli/main.py` 中的 `_setup_completers` 方法来自定义补全行为。

### 环境变量

可以通过以下环境变量控制补全行为：
- `_ARGCOMPLETE_COMPLETE`: argcomplete 内部使用
- `_ARGCOMPLETE_IFS`: 补全项分隔符

## 示例

```bash
# 基本使用
auto-coder.run -p "Write a hello world function"

# 使用自动补全选择工具
auto-coder.run --allowed-tools read_file write_to_file -p "Refactor this code"

# 使用自动补全选择输出格式
auto-coder.run -p "Generate documentation" --output-format json

# 恢复会话（使用补全选择会话ID）
auto-coder.run --resume <TAB选择会话ID>
```

通过这些自动补全功能，您可以更高效地使用 Auto-Coder CLI 工具！


