<p align="center">
  <picture>    
    <img alt="auto-coder" src="./logo/auto-coder.jpeg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder (powered by Byzer-LLM)
</h3>

<p align="center">
<a href="https://uelng8wukz.feishu.cn/wiki/QIpkwpQo2iSdkwk9nP6cNSPlnPc"><b>中文</b></a> |

</p>

---

*Latest News* 🔥
- [2025/01] Release Auto-Coder 0.1.208
- [2024/09] Release Auto-Coder 0.1.163
- [2024/08] Release Auto-Coder 0.1.143
- [2024/07] Release Auto-Coder 0.1.115
- [2024/06] Release Auto-Coder 0.1.82
- [2024/05] Release Auto-Coder 0.1.73
- [2024/04] Release Auto-Coder 0.1.46
- [2024/03] Release Auto-Coder 0.1.25
- [2024/03] Release Auto-Coder 0.1.24

---

## 安装

### 方法一：使用 pip 安装（推荐）

```shell
# 创建虚拟环境（推荐）
conda create --name autocoder python=3.10.11
conda activate autocoder

# 或者使用 venv
python -m venv autocoder
source autocoder/bin/activate  # Linux/macOS
# autocoder\Scripts\activate  # Windows

# 安装 auto-coder
pip install -U auto-coder
```

### 方法二：从源码安装

```shell
# 克隆仓库
git clone https://github.com/allwefantasy/auto-coder.git
cd auto-coder

# 创建虚拟环境
conda create --name autocoder python=3.10.11
conda activate autocoder

# 安装依赖
pip install -r requirements.txt

# 安装项目
pip install -e .
```

### 系统要求

- Python 3.10, 3.11 或 3.12
- 操作系统：Windows、macOS、Linux
- 内存：建议 4GB 以上
- 磁盘空间：建议 2GB 以上

### 验证安装

安装完成后，可以通过以下命令验证安装是否成功：

```shell
# 检查版本
auto-coder --version

# 启动聊天模式
auto-coder.chat

# 运行单次命令
auto-coder.run -p "Hello, Auto-Coder!"
```

## 使用指南

### 1. 聊天模式（推荐新手使用）

```shell
# 启动交互式聊天界面
auto-coder.chat

# 或者使用别名
chat-auto-coder
```

聊天模式提供友好的交互界面，支持：
- 实时对话
- 代码生成和修改
- 文件操作
- 项目管理

### 2. 命令行模式

#### 单次运行模式

```shell
# 基本用法
auto-coder.run -p "编写一个计算斐波那契数列的函数"

# 从管道读取输入
echo "解释这段代码的功能" | auto-coder.run -p

# 指定输出格式
auto-coder.run -p "生成一个 Hello World 函数" --output-format json

# 使用详细输出
auto-coder.run -p "创建一个简单的网页" --verbose
```

#### 会话模式

```shell
# 继续最近的对话
auto-coder.run --continue

# 恢复特定会话
auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000
```

#### 高级选项

```shell
# 限制对话轮数
auto-coder.run -p "优化这个算法" --max-turns 5

# 指定系统提示
auto-coder.run -p "写代码" --system-prompt "你是一个专业的Python开发者"

# 限制可用工具
auto-coder.run -p "读取文件内容" --allowed-tools read_file write_to_file

# 设置权限模式
auto-coder.run -p "修改代码" --permission-mode acceptEdits
```

### 3. 核心模式

```shell
# 启动核心模式（传统命令行界面）
auto-coder

# 或者使用别名
auto-coder.core
```

### 4. 服务器模式

```shell
# 启动 Web 服务器
auto-coder.serve

# 或者使用别名
auto-coder-serve
```

### 5. RAG 模式

```shell
# 启动 RAG（检索增强生成）模式
auto-coder.rag
```

### 常用命令示例

```shell
# 代码生成
auto-coder.run -p "创建一个 Flask Web 应用"

# 代码解释
auto-coder.run -p "解释这个函数的作用" < code.py

# 代码重构
auto-coder.run -p "重构这段代码，提高可读性"

# 错误修复
auto-coder.run -p "修复这个 bug" --verbose

# 文档生成
auto-coder.run -p "为这个项目生成 README 文档"

# 测试生成
auto-coder.run -p "为这个函数编写单元测试"
```

### 自动补全

Auto-Coder 支持命令行自动补全功能：

```shell
# 安装自动补全（bash）
echo 'eval "$(register-python-argcomplete auto-coder.run)"' >> ~/.bashrc
source ~/.bashrc

# 安装自动补全（zsh）
echo 'eval "$(register-python-argcomplete auto-coder.run)"' >> ~/.zshrc
source ~/.zshrc
```

## 卸载

### 完全卸载

```shell
# 卸载 auto-coder
pip uninstall auto-coder

# 删除虚拟环境（如果使用了虚拟环境）
conda remove --name autocoder --all
# 或者
rm -rf autocoder  # 如果使用 venv 创建的环境

# 清理缓存文件（可选）
rm -rf ~/.autocoder  # 用户配置和缓存目录
```

### 重新安装

```shell
# 卸载旧版本
pip uninstall auto-coder

# 清理缓存
pip cache purge

# 安装最新版本
pip install -U auto-coder
```

## 配置

### 环境变量

```shell
# 设置 API 密钥
export OPENAI_API_KEY="your-api-key"
export ANTHROPIC_API_KEY="your-api-key"

# 设置模型配置
export AUTOCODER_MODEL="gpt-4"
export AUTOCODER_BASE_URL="https://api.openai.com/v1"
```

### 配置文件

Auto-Coder 支持多种配置方式：

- `.autocoderrc`：项目级配置
- `~/.autocoder/config.yaml`：用户级配置
- 环境变量：系统级配置

## 故障排除

### 常见问题

1. **安装失败**
   ```shell
   # 升级 pip
   pip install --upgrade pip
   
   # 清理缓存重新安装
   pip cache purge
   pip install auto-coder
   ```

2. **权限错误**
   ```shell
   # 使用用户安装
   pip install --user auto-coder
   ```

3. **依赖冲突**
   ```shell
   # 使用虚拟环境
   python -m venv autocoder_env
   source autocoder_env/bin/activate
   pip install auto-coder
   ```

4. **命令未找到**
   ```shell
   # 检查 PATH
   echo $PATH
   
   # 重新安装
   pip uninstall auto-coder
   pip install auto-coder
   ```

### 获取帮助

```shell
# 查看帮助信息
auto-coder.run --help

# 查看版本信息
auto-coder --version

# 启用详细输出进行调试
auto-coder.run -p "test" --verbose
```

## 教程

0. [Auto-Coder.Chat: 通向智能编程之路](https://uelng8wukz.feishu.cn/wiki/QIpkwpQo2iSdkwk9nP6cNSPlnPc)



