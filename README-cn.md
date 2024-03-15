
<p align="center">
  <picture>    
    <img alt="auto-coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder（由 Byzer-LLM 提供支持）
</h3>

<p align="center">
| <a href="./README.md"><b>英文</b></a> | <a href="./README-CN.md"><b>中文</b></a> |

</p>

---

*最新动态* 🔥

- [2024/03] 发布 Auto-Coder 0.1.7

---

🚀 开发者们请注意！🚨 改变游戏规则的 Auto-Coder 已经到来，它将带你的人工智能编程进入全新层次！🌟

凭借 Byzer-LLM 强大的内核驱动，这款命令行工具集众多令人惊叹的功能于一身：

📂 和手动收集上下文说再见吧！Auto-Coder 能够根据源目录的上下文智能生成代码，就像拥有一个能精准理解你需求的天才助手一般！
两种模式，无限可能！生成完美的提示以粘贴到基于网络的大规模模型中，或者让 Auto-Coder 通过 Byzer-LLM 直接与私有模型配合，展现其神奇之处。选择权在你手中，结果总是令人惊艳！

无论 Python 还是 TypeScript，都不是问题！Auto-Coder 支持编程街区的所有热门语言。

走向全球易如反掌！Auto-Coder 自动翻译你的项目文件，让你的代码征服世界！

Copilot 模式已上线，它将成为你新的得力伙伴！凭借内置的 shell/Jupyter 引擎，Auto-Coder 能够分解任务、设置环境、创建项目，甚至为你修改代码。就像拥有一个永不停歇的超级智能助手！

开发者们，准备好被震撼吧！Auto-Coder 无缝集成最热门的 AI 模型如 ChatGPT，为你的开发过程注入闪电般的速度！🚀🌟 别再等待了！立即体验 Auto-Coder 的原始力量，让 AI 成为你的终极编程伙伴！https://github.com/allwefantasy/auto-coder 🔥

#AutoCoder #AI编程 #变革者 #ByzerLLM #开发者工具

## 目录

- [全新安装](#全新安装)
- [已有安装](#已有安装)
  - [使用](#使用)
    - [基础用法](#基础)
    - [高级用法](#高级)
    - [仅限Python项目的特性](#python项目专用功能)
    - [TypeScript项目](#typescript项目)
    - [真实自动模式](#真实自动)

## 全新安装

你可以通过 Byzer-LLM 提供的脚本来设置 NVIDIA 驱动/CUDA 环境：

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

在设置好 NVIDIA 驱动/CUDA 环境后，可以按照以下方式安装 auto_coder：

```shell
pip install -U auto-coder
```

## 已有安装


```shell
# 或者使用 https://gitcode.com/allwefantasy11/auto-coder.git    
git clone https://github.com/allwefantasy/auto-coder.git
pip install -r requirements.txt
## 如果您想使用私有/开源模型，请取消注释此行。
# pip install -U vllm
pip install -U byzerllm
pip install -U auto-coder

## 使用方法

### 基础用法
> 推荐使用千义通问Max/Qwen-Max-longcontext SaaS模型
> 您应通过[Byzer-LLM](https://github.com/allwefantasy/byzer-llm)部署模型

Auto-Coder 提供两种方式：

1. 为查询生成上下文，您可以将上下文复制并粘贴到ChatGPT/Claud3/Kimi的Web UI中。
2. 直接使用Byzer-LLM中的模型生成结果。

>> 注意：您需要确保所使用的模型支持长上下文长度，例如 >32k。

Auto-Coder 将从源目录收集源代码，并根据查询内容将上下文生成到目标文件中。

然后，您可以将`output.txt`的内容复制并粘贴到ChatGPT/Claud3/Kimi的Web UI中：

例如：

```shell    
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何设置该系统以通过 auto-coder 命令执行？" 
```

您也可以将所有参数放入一个 yaml 文件中：

```yaml
# /home/winubuntu/projects/ByzerRawCopilot/auto-coder.yaml
source_dir: /home/winubuntu/projects/ByzerRawCopilot
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt
query: |
  如何让这个系统可以通过 auto-coder 命令执行？
```

然后使用以下命令：

```shell
auto-coder --file /home/winubuntu/projects/ByzerRawCopilot/auto-coder.yaml
``` 

如果您想使用 Byzer-LLM 中的模型，可以使用以下命令：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --execute --query "重新生成一个适用于reactjs+typescript 组合项目的 is_likely_useful_file 方法。" 
``` 在上述指令中，我们指定了一个模型并开启了执行模式，Auto-Coder 会从源代码目录抓取源代码，接着基于此生成查询的上下文，并利用模型生成结果，最终将结果写入目标文件。

### 如何缩减上下文长度？

正如您可能了解的那样，Auto-Coder 会从源代码目录获取源代码并为查询构建上下文，若源代码目录太大，则上下文会变得过长，可能会超出模型处理的能力范围。

有以下两种方式来缩短上下文长度：

1. 将 source_dir 设置为项目下的子目录。
2. 开启 Auto-Coder 的索引特性。

要使用索引功能，您应当配置一些额外的参数：

1. skip_build_index: false
2. model

例如：

```yaml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 
model: qianwen_chat
model_max_length: 2000
anti_quota_limit: 13    
``````yaml
skip_build_index: false
项目类型: "copilot/.py"
查询: |
  优化 copilot 中的 get_suffix_from_project_type 函数并更新原文件

在此处，我们添加了一个新的参数 `skip_build_index`，默认情况下，该值为 true。 
如果您将其设置为 false 并同时提供模型，则自动编码器将使用模型为源代码生成索引（这可能会消耗大量令牌），生成的索引文件将存储在源代码目录下的 `.auto-coder` 目录中。

一旦创建了索引，自动编码器将使用该索引来过滤文件并减少上下文长度。请注意，过滤操作也会使用模型，且可能消耗令牌，因此您应谨慎使用。

### 高级功能

> 此功能仅适用于 Byzer-LLM 提供的模型。

翻译项目中的 markdown 文件：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat 
```

当你想要翻译某些文件时，必须指定 model 参数。而 project_type 有点复杂，它是以下参数的组合：

- translate：项目类型
- 中文：你希望翻译成的目标语言
- .md：你想要翻译的文件扩展名
- cn：根据翻译后内容创建的新文件后缀，例如，如果原始文件是 README.md，新文件将会是 README-cn.md

因此，最终的 project_type 是 "translate/中文/.md/cn"

如果你的模型足够强大，可以使用以下命令执行相同任务：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --model_max_length 2000 --query "把项目中的markdown文档翻译成中文"
```

该模型会从查询中提取出 "translate/中文/.md/cn"，然后执行与上一个命令相同的操作。 注意：model_max_length 用于控制模型生成的长度，如果未设置 model_max_length，则默认值为 1024。你应该根据对翻译长度的预估来调整这个值。

### 仅适用于 Python 项目的特性

为了减少自动编码器收集的上下文长度，如果你正在处理一个 Python 项目，可以使用以下命令：

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py-script --query "帮我实现script模块中还没有实现的方法"

```

在上述命令中，我们提供了一个脚本路径和一个包名，其中 script_path 是你现在正在处理的 Python 文件，而 package_name 是你关心的包名称。这样，自动编码器只会从 package_name 和由 script_path 文件导入的内容中收集上下文信息，这将显著减少上下文长度。 当您在 `--query` 参数中提到 `script module` 时，您所指的是 script_path 文件中的脚本文件。

完成任务后，您可以从输出文件 output.txt 中复制提示信息，并将其粘贴至聊天通义或其它AI模型的网页端。

如果指定了模型，自动编码器将会利用该模型生成结果，并将结果插入目标文件内。

```shell
auto-coder --目标文件 /home/winubuntu/projects/ByzerRawCopilot/output.txt --脚本路径 /home/winubuntu/projects/YOUR_PROJECT/xxx.py --包名 xxxx --项目类型 py-script --模型 qianwen_chat --执行 --查询 "帮我实现script模块中还未实现的方法"
```

## TypeScript 项目设置

只需尝试将项目类型（project_type）设为 ts-script。

## 实际自动编码示例

```shell
auto-coder --源目录 /home/winubuntu/projects/ByzerRawCopilot --目标文件 /home/winubuntu/projects/ByzerRawCopilot/output.txt --项目类型 copilot --模型最大长度 2000 --模型 qianwen_chat --查询 "帮我创建一个名为t-copilot 的python项目，生成的目录需满足打包后的python项目结构要求"

```此项目类型会根据查询自动创建一个Python项目，并基于该查询生成结果。

您可以在`output.txt`文件中查看所有日志。

auto-coder还支持Python代码解释器，可以尝试以下命令：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat --query "用python打印你好，中国"
```

`output.txt`文件的内容将会是：

```text
=================对话记录==================

user: 
根据用户的问题，对问题进行拆解并生成执行步骤。

环境信息如下:
操作系统: linux 5.15.0-48-generic  
Python版本: 3.10.11
Conda环境: byzerllm-dev 
支持Bash

用户提出的问题是：用python打印你好，中国

每次生成一个执行步骤后询问我是否继续，当我回复继续时，继续生成下一个执行步骤。

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
=================结果==================

Python代码：
print('你好，中国')
输出：
你好，中国  

翻译时请以 >>>>> 开头。
翻译时需要遵循以下规则：
1. Auto-Coder 是专有名词，不要翻译成中文。
2. 在翻译过程中，请仅对原文进行翻译，不做任何其他修改。
你要求自动编码器修改一个Python文件：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot/.py --model_max_length 2000 --model qianwen_chat --query "优化 copilot 中的get_suffix_from_project_type 函数并更新原文件"
``` 
