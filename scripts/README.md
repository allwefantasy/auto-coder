# 测试运行工具

此目录包含帮助运行测试的工具脚本。

## run_test.sh

`run_test.sh` 是一个方便的脚本，用于运行项目的测试，它会自动设置正确的环境变量。

### 特点

- 自动设置 `autocoder_auto_init=false` 和 `auto_coder_log_stdout=true` 环境变量
- 支持按目录或特定测试文件运行测试
- 支持传递额外的 pytest 参数

### 用法

```bash
# 运行所有测试
./scripts/run_test.sh

# 运行特定目录下的测试
./scripts/run_test.sh src/autocoder/rag/

# 运行特定测试文件
./scripts/run_test.sh tests/test_file.py

# 使用额外的 pytest 参数
./scripts/run_test.sh src/autocoder/rag/ -v --log-cli-level=DEBUG
```

## run_test_completion.sh

这个脚本提供了 `run_test.sh` 的命令行补全功能，能够智能识别并列出所有包含 `test_` 开头的测试文件的目录。

### 补全功能特点

- 自动查找整个项目中包含 `test_*.py` 文件的所有目录
- 支持基于部分目录名称的智能补全（如输入 `rag` 可以补全为 `src/autocoder/rag/`）
- 提供常用 pytest 参数的补全

### 安装补全功能

将以下行添加到您的 `.bashrc` 或 `.zshrc` 文件中：

```bash
source /path/to/auto-coder/scripts/run_test_completion.sh
```

然后重新加载配置或重启终端：

```bash
source ~/.bashrc   # 对于 Bash
# 或
source ~/.zshrc    # 对于 Zsh
```

### 使用补全功能示例

1. 基于部分目录名补全：

```bash
# 如果src/autocoder/rag/目录下有测试文件
./scripts/run_test.sh rag<Tab>
# 会补全为：
./scripts/run_test.sh src/autocoder/rag/
```

2. 补全测试文件：

```bash
./scripts/run_test.sh src/autocoder/rag/test_<Tab>
# 会列出该目录下所有test_开头的Python文件
```

3. 补全pytest参数：

```bash
./scripts/run_test.sh src/autocoder/rag/ -<Tab>
# 会列出常用的pytest参数选项
```

## 使用示例

1. 运行RAG相关的所有测试，只需输入部分名称：

```bash
./scripts/run_test.sh rag<Tab>  # 补全为完整路径
./scripts/run_test.sh src/autocoder/rag/
```

2. 以详细模式运行特定测试文件：

```bash
./scripts/run_test.sh tests/test_<Tab>  # 列出所有测试文件
./scripts/run_test.sh tests/test_specific.py -v
```

3. 查找所有包含特定关键字的测试目录：

```bash
./scripts/run_test.sh rag<Tab>  # 会匹配所有包含"rag"的测试目录
``` 