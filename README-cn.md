<p align="center">
  <picture>    
    <img alt="Auto-Coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
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

- [2024/03] 发布 Auto-Coder 0.1.4 版本

---

🎉 Auto-Coder 震撼发布,开启 AI 编程新时代!🚀

Auto-Coder 由 Byzer-LLM 强力驱动的一个命令行工具,为开发者带来:
📂 根据源目录智能生成上下文相关代码
💡 可以结合上下文生成合适的 prompt 到指定文件，方便用户黏贴到 web 版 大模型。也通过Byzer-LLM支持指定私有模型直接完成工作。两种模式任君选择。
💻 支持 Python、TypeScript 等主流语言项目
🌍 自动翻译项目文件,让你的代码触达全球
🤖 Copilot 模式:内置shell/jupyter 引擎，可自动拆解任务并且执行相关任务，完成诸如自动搭建环境与创建项目,修改代码

🧑‍💻 开发者们,是时候提升编程效率了!Auto-Coder 支持与 ChatGPT 等知名 AI 模型无缝对接,为你的开发流程增速🚀

🌟 即刻体验 Auto-Coder,让 AI 成为你编程路上的得力助手! https://github.com/allwefantasy/auto-coder 🔥

#AutoCoder #AI编程 #效率提升 #ByzerLLM #开发者工具


## 目录


- [全新安装](#brand-new-installation)
- [已有安装](#existing-installation)
- [使用方法](#usage)
  - [基础用法](#basic)
  - [高级用法](#advanced)
  - [仅限 Python 项目的功能](#python-project-only-features)
  - [TypeScript 项目](#typescript-project)
  - [全自动模式](#real-auto)


## 介绍
Auto-Coder 是一款由 Byzer-LLM 提供强大支持的工具，用于简化代码生成和项目管理流程。它能够从指定目录收集源代码，并基于用户查询生成上下文信息，这些信息可以与 ChatGPT 或其他 AI 模型配合使用。同时，Auto-Coder 还集成了 Byzer-LLM，可直接生成结果。该工具支持多种项目类型，包括 Python、TypeScript 等，并提供高级功能，如文件翻译以及在特定模块和包内进行针对性代码生成。借助 Auto-Coder，开发者可以显著提升工作效率并高效地管理项目，充分利用 AI 辅助编码的力量。

copilot 项目类型能够自动完成环境设置和项目创建，或者根据用户查询创建新的类和方法。它是开发者快速创建新项目及管理现有项目的强大工具。

## 全新安装

您可以使用 Byzer-LLM 提供的脚本来设置 nvidia-driver/cuda 环境：
在NVIDIA驱动/CUDA环境设置完毕后，您可以按照以下方式安装auto_coder：

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
```

## 使用方法

### 基本用法
> 推荐使用千义通问Max/Qwen-Max-longcontext SaaS模型
> 您应当通过[Byzer-LLM](https://github.com/allwefantasy/byzer-llm)部署模型

Auto-Coder 提供两种方式：

1. 为查询生成上下文，并用于Web中的ChatGPT或其他AI模型。
2. 直接使用Byzer-LLM中的模型生成结果。

>> 注意：您应确保所使用的模型支持长上下文长度，例如 >32k。自动编码器将从源目录中收集源代码，然后根据查询内容生成上下文并写入目标文件。

接下来，您可以复制 `output.txt` 文件中的内容，并将其粘贴到 Web of ChatGPT 或其他 AI 模型中：

例如：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何让这个系统可以通过 auto-coder 命令执行？" 
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

如果您想使用 Byzer-LLM 模型，可以使用以下命令：

```shell    
（此处由于没有提供具体的命令行示例，请参照 Byzer-LLM 文档以获取正确命令）
```在上述命令中，我们提供了一个模型并启用了执行模式。Auto-Coder 将从源目录收集源代码，然后为查询生成上下文，接着使用该模型生成结果，并将结果放入目标文件中。

### 高级功能

> 该功能仅适用于 Byzer-LLM 提供的模型。

翻译项目中的 Markdown 文件：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat 
```

当你想要翻译某些文件时，必须指定 model 参数。而 project_type 概念稍微复杂一些，它是以下参数的组合：

- translate：项目类型
- 中文：你希望翻译成的目标语言
- .md：你想要翻译的文件扩展名
- cn：根据翻译后内容创建的新文件后缀。例如，如果原始文件是 README.md，新生成的文件将会是 README-cn.md

所以最终的 project_type 为 "translate/中文/.md/cn"

如果你的模型功能足够强大，可以使用以下命令执行相同任务：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --model_max_length 2000 --query "把项目中的markdown文档翻译成中文"
```

该模型会从查询语句中提取出 "translate/中文/.md/cn"，然后执行与上一条命令相同的操作。 注意：model_max_length 用于控制模型生成的长度，如果未设置 model_max_length，则默认值为 1024。您应根据对翻译长度的预估来调整这个值。

### Python 项目专属特性

为了减少自动编码器收集的上下文长度，如果您正在处理的是一个 Python 项目，可以使用以下命令：

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py-script --query "帮我实现script模块中还没有实现的方法"

```

在上述命令中，我们提供了一个脚本路径和一个包名，其中 script_path 是您当前正在处理的 Python 文件，而 package_name 是您关心的包名。这样，自动编码器只会从 package_name 和由 script_path 文件导入的部分收集上下文信息，这将显著减少上下文长度。 当你在 `--query` 参数中提到 `script module` 时，意味着你指的是 script_path 路径下的脚本文件。

完成任务后，可以从 output.txt 文件中获取提示并将其粘贴至聊天通义或其它AI模型的网页端。

如果指定了模型，自动编码器会利用该模型生成结果，并将结果插入目标文件内。

示例：

```shell
auto-coder --目标文件路径 /home/winubuntu/projects/ByzerRawCopilot/output.txt --脚本路径 /home/winubuntu/projects/YOUR_PROJECT/xxx.py --包名 xxxx --项目类型 py-script --模型 qianwen_chat --执行 --查询指令 "帮我实现script模块中还未实现的方法"
```

## TypeScript 项目设置

只需尝试将项目类型（project_type）设为 ts-script。

## 实时自动化生成实例

```shell
auto-coder --源代码目录 /home/winubuntu/projects/ByzerRawCopilot --目标文件路径 /home/winubuntu/projects/ByzerRawCopilot/output.txt --项目类型 copilot --模型最大长度 2000 --模型 qianwen_chat --查询指令 "帮我创建一个名字叫做t-copilot 的python项目，生成的目录结构需符合打包的python项目规范" 
```

此项目类型会根据查询内容自动生成一个Python项目，并进一步基于查询结果生成输出。

您可以在 `output.txt` 文件中查看所有日志。

Auto-Coder 还支持Python代码解释器，您可以尝试以下命令：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat --query "用python打印你好，中国"
```

`output.txt` 文件中的内容将会是：

```text
=================对话记录==================

user: 
根据用户的问题，对问题进行拆解并生成执行步骤。

环境信息如下:
操作系统: linux 5.15.0-48-generic  
Python版本: 3.10.11
Conda环境: byzerllm-dev 
支持Bash

用户的问题是：用python打印你好，中国

每次生成一个执行步骤后询问我是否继续，当我回复继续时，将生成下一个执行步骤。
如果是最后一个步骤，请标注 "__END__"

assistant: ```json
{
  "code": "print('你好，中国')",
  "lang": "python",
  "total_steps": 1,
  "cwd": "",
  "env": {},
  "timeout": -1,
  "ignore_error": false
}```
是否继续？
user: 继续
=================结果区域==================
    
Python 代码：

print('你好，中国')
输出结果：
你好，中国
--------------------

你要求自动编码器修改一个 Python 文件：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot/.py --model_max_length 2000 --model qianwen_chat --query "优化 copilot 中的 get_suffix_from_project_type 函数并更新原文件"
```