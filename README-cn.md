 <p align="center">
  <picture>    
    <img alt="auto-coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder (由 Byzer-LLM 支持)
</h3>

<p align="center">
| <a href="./README.md"><b>英文</b></a> | <a href="./README-CN.md"><b>中文</b></a> |

</p>

---

*最新消息* 🔥

- [2024/03] 发布 Auto-Coder 0.1.4

---



🚀 注意开发者们！🚨 改变游戏规则的 Auto-Coder 已经到来，它将把您的 AI 编程提升到一个全新的水平！🌟

由 Byzer-LLM 不可思议的力量驱动，这款命令行工具功能丰富，将让您大吃一惊：

📂 告别手动上下文收集！Auto-Coder 根据源代码目录的上下文智能生成代码。就像拥有一个知道您确切需求的天才助手一样！ 两种模式，无限可能！为网络大型模型生成完美的提示，或直接通过Byzer-LLM与私有模型一起使用Auto-Coder发挥其魔力。选择权在你手中，结果总是令人惊艳！

💻 Python？TypeScript？没问题！Auto-Coder支持编程界所有备受欢迎的编程语言。

🌍 走向全球轻而易举！Auto-Coder自动翻译您的项目文件，让您的代码征服世界！

🤖 Copilot模式来了，它是您的新最佳朋友！凭借其内置的shell/Jupyter引擎，Auto-Coder为您分解任务、设置环境、创建项目，甚至为您修改代码。就像拥有一个永不知疲倦的超级智能助手！

🧑‍💻 开发者们，准备好让你们的思维被震撼吧！Auto-Coder与ChatGPT等最热门的AI模型无缝集成，将您的开发过程加速到闪电般的速度！🚀 🌟 不要再等一秒！立即体验Auto-Coder的原始实力，让AI成为您的终极编程伙伴！https://github.com/allwefantasy/auto-coder 🔥

#AutoCoder #AI编程 #游戏改变者 #ByzerLLM #开发工具

## 目录

- [全新安装](#全新安装)
- [现有安装](#现有安装)
- [使用说明](#使用说明)
  - [基础](#基础)
  - [高级](#高级)
  - [仅限Python项目功能](#仅限python项目功能)
  - [TypeScript项目](#typescript项目)
  - [实时自动](#实时自动)

## 全新安装

您可以使用Byzer-LLM提供的脚本设置nvidia驱动程序/cuda环境：

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

设置好nvidia驱动程序/cuda环境后，您可以像这样安装auto_coder：

```shell
pip install -U auto-coder
```

## 现有安装

```shell
# 或 https://gitcode.com/allwefantasy11/auto-coder.git    
git clone https://github.com/allwefantasy/auto-coder.git
pip install -r requirements.txt
## 如果您想使用私有/开源模型，请取消注释此行。
# pip install -U vllm
pip install -U byzerllm
pip install -U auto-coder
```

## 使用方法

### 基础
> 建议使用千义通问Max/Qwen-Max-longcontext SaaS模型
> 您应该通过[Byzer-LLM](https://github.com/allwefantasy/byzer-llm)部署模型

Auto-Coder 提供两种方式：

1. 为查询生成上下文，并在ChatGPT Web或其他AI模型中使用。
2. 直接使用Byzer-LLM中的模型生成结果。

>> 注意：您应确保模型支持较长的上下文长度，例如 >32k。

Auto-Coder 将从源目录收集源代码，然后根据查询将上下文生成到目标文件中。

然后，您可以复制`output.txt`的内容并粘贴到ChatGPT Web或其他AI模型中：

例如：

```shell    
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何让这个系统可以通过 auto-coder 命令执行？" 
```

您还可以将所有参数放入一个 yaml 文件中:


```yaml
# /home/winubuntu/projects/ByzerRawCopilot/auto-coder.yaml
source_dir: /home/winubuntu/projects/ByzerRawCopilot
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt
query: |
  如何让这个系统可以通过 auto-coder 命令执行？
```
  
然后使用以下命令:

```shell
auto-coder --file /home/winubuntu/projects/ByzerRawCopilot/auto-coder.yaml
``` 

如果您想使用 Byzer-LLM 中的模型，您可以使用以下命令:

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --execute --query "重新生成一个 is_likely_useful_file 方法，满足reactjs+typescript 组合的项目。" 
``` 在上述命令中，我们提供了一个模型并启用执行模式，Auto-Coder 将从源目录收集源代码，然后为查询生成上下文，接着使用模型生成结果，然后将结果放入目标文件。

### 高级

> 此功能仅适用于 Byzer-LLM 的模型。

翻译项目中的 Markdown 文件：

```shell

auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat 
```
当你想要翻译一些文件时，必须指定 model 参数。而 project_type 有点复杂，它是以下参数的组合：

- translate：项目类型
- 中文：你想要翻译成的目标语言
- .md：你想要翻译的文件扩展名 请从这里开始翻译。

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py-script --query "帮我实现script模块中还没有实现方法"

```

在上述命令中，我们提供了一个脚本路径和一个包名称，script_path 是您当前正在处理的Python文件，而 package_name 是您关心的名称。然后，自动编码器仅从 package_name 和通过 script_path 文件导入的上下文中收集内容，这将显著减少上下文长度。

当您在 `--query` 中引用 `script module` 时，意味着您正在谈论 script_path 文件。

任务完成后，您可以将 output.txt 中的提示复制并粘贴到ChatGPT Web或其他AI模型中。 如果您指定了模型，Auto-Coder 将使用该模型生成结果，然后将结果放入目标文件中。

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/YOUR_PROJECT/xxx.py --package_name xxxx --project_type py-script --model qianwen_chat --execute --query "帮我实现script模块中还没有实现方法" 
```

## TypeScript 项目

尝试将 project_type 设置为 ts-script。

## Real-Auto

以下是一个示例：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat  --query "帮我创建一个名字叫t-copilot 的python项目，生成的目录需要符合包装的python项目结构"

```

这个项目类型将根据查询自动创建一个 python 项目，然后根据查询生成结果。

您可以在 `output.txt` 文件中查看所有日志。

Auto-Coder 还支持 python 代码解释器，请尝试以下操作：

```shell     
``` 请将以下内容翻译成中文：

auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat  --query "用python打印你好，中国"

output.txt 文件的内容将是：

```text
=================CONVERSATION==================

user: 
根据用户的问题，对问题进行拆解，然后生成执行步骤。

环境信息如下:
操作系统: linux 5.15.0-48-generic  
Python版本: 3.10.11
Conda环境: byzerllm-dev 
支持Bash

用户的问题是：用python打印你好，中国

每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。

assistant: 
{
  "code": "print('你好，中国')",
  "lang": "python",
  "total_steps": 1,
  "cwd": "",
  "env": {},
  "timeout": -1,
  "ignore_error": false
}

是否继续？
user: 继续
=================RESULT==================

Python 代码:
print('你好，中国')
输出:
你好，中国
--------------------
```

您要求 Auto-Coder 修改一个 python 文件：

```shell    
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot/.py --model_max_length 2000 --model qianwen_chat --查询 "优化copilot中的get_suffix_from_project_type函数并更新原文件"
``` 