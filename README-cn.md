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

- [2024/03] 发布 Auto-Coder 0.1.16

---

🚀 开发者们请注意！🚨 创新的 Auto-Coder 已经到来，它将带你的人工智能编程体验达到全新高度！🌟

得益于 Byzer-LLM 的强大能力，这款命令行工具拥有令人惊叹的功能：

📂 不再需要手动收集上下文信息！Auto-Coder 能够根据源目录的上下文智能生成代码。就像拥有一位能准确理解你需求的天才助手一样！

---💡 两种模式，无限可能！生成完美的提示以粘贴到基于网络的大规模模型中，或者让 Auto-Coder 直接通过 Byzer-LLM 与私有模型配合施展魔法。选择权在你手中，结果总是令人惊艳！

💻 Python？TypeScript？没问题！Auto-Coder 支持编程街区上所有酷炫的语言。

🌍 走向全球变得轻而易举！Auto-Coder 自动翻译你的项目文件，让你的代码能够征服世界！

🤖 Copilot 模式已上线，它将成为你的新好朋友！凭借其内置的 shell/Jupyter 引擎，Auto-Coder 能够分解任务、设置环境、创建项目，甚至为你修改代码。就像拥有一个永不休息的超级智能副手！

🧑‍💻 开发者们，准备好被震撼吧！Auto-Coder 无缝集成最热门的 AI 模型如 ChatGPT，将你的开发过程加速到闪电般的速度！🚀🌟 别再犹豫了！立即体验 Auto-Coder 的强大功能，让 AI 成为你的终极编程伙伴！访问 https://github.com/allwefantasy/auto-coder 🔥

#AutoCoder #AI编程 #变革者 #ByzerLLM #开发者工具

## 目录

- [安装](#安装)
- [全新安装](#原始元机器安装)
- [使用方法](#使用)
  - [基础](#基础)
  - [高级](#高级)
  - [仅限 Python 项目功能](#仅限-python-项目的功能)
  - [TypeScript 项目](#typescript-项目)
  - [真·自动模式](#真·自动)
    - [结合搜索引擎的真·自动模式](#结合搜索引擎的真·自动)

## 安装

```shell
conda create --name autocoder python=3.10.11
conda activate autocoder
pip install -U auto-coder
## 如果你想使用私有/开源模型，请取消注释这一行。
# pip install -U vllm
ray start --head
```

## 原始元机器安装

你可以通过 Byzer-LLM 提供的脚本来设置 nvidia-driver/cuda 环境：在NVIDIA驱动/CUDA环境设置完毕后，您可以按照以下方式安装Auto-Coder：

```shell
pip install -U auto-coder
```


## 使用方法

### LLM模型

> 推荐使用千义通问Max/Qwen-Max SaaS模型
> 请确保您的模型至少有8k的上下文。

尝试使用以下命令部署Qwen-Max：

```shell
byzerllm deploy  --pretrained_model_type saas/qianwen \
--infer_params saas.api_key=xxxxxxx saas.model=qwen-max \
--model qianwen_chat 
```

然后您可以使用以下命令测试模型：

```shell
byzerllm query --model qianwen_chat --query "你好"
```

如果您想要卸载模型：

```shell
byzerllm undeploy --model qianwen_chat
```

如果您想部署您的私有/开源模型，请尝试访问[此链接](https://github.com/allwefantasy/byzer-llm)

### 基础功能

Auto-Coder 提供两种方式：1. 根据查询生成上下文，并将其复制粘贴到 ChatGPT/Claud3/Kimi 的 Web 界面中。
2. 直接使用 Byzer-LLM 模型生成结果。

>> 注意：您需要确保模型支持较长的上下文长度，例如 >32k。

自动编码器将从源目录收集源代码，然后根据查询在目标文件中生成上下文。

然后您可以复制 `output.txt` 文件的内容并将其粘贴到 ChatGPT/Claud3/Kimi 的 Web 界面中：

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
auto-coder --config /home/winubuntu/projects/ByzerRawCopilot/auto-coder.yaml
```auto-coder --file /home/winubuntu/projects/ByzerRawCopilot/auto-coder.yaml

如果你想使用来自 Byzer-LLM 的模型，可以使用以下命令：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --execute --query "为满足reactjs+typescript 组合的项目重新生成一个 is_likely_useful_file 方法。"
```

在上述命令中，我们提供了一个模型并启用了执行模式，auto-coder 将从源目录收集源代码，然后为查询生成上下文，接着使用模型生成结果，并将结果放入目标文件中。

### 如何减少上下文长度？

你可能知道，auto-coder 会从源目录收集源代码，然后为查询生成上下文。如果源目录太大，上下文就会过长，模型可能无法处理这种情况。

有两种方法可以减少上下文长度：1. 将 source_dir 更改为项目下的子目录。
2. 启用 Auto-Coder 的索引功能。

为了使用索引功能，您需要配置一些额外的参数：

1. skip_build_index: false
2. model

例如：

```yaml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 13

skip_build_index: false

project_type: "copilot/.py"
query: |
  优化 copilot 中的 get_suffix_from_project_type 函数并更新原文件
```

这里我们添加了一个新参数 `skip_build_index`，默认情况下，该值为 true。如果您将其设置为 false 并同时提供一个模型，那么 Auto-Coder 将使用该模型为源代码生成索引（这可能会消耗大量令牌），生成的索引文件将存储在源目录下的名为 `.auto-coder` 的目录中。一旦索引创建完成，Auto-Coder 将利用该索引过滤文件并减少上下文长度。请注意，过滤操作也会使用模型，并且可能会消耗令牌，因此您应谨慎使用。

### 高级功能

> 本功能仅适用于 Byzer-LLM 模型。

在项目中翻译 Markdown 文件：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat
```

当您想要翻译某些文件时，必须指定 `model` 参数。而 `project_type` 参数较为复杂，它是由以下参数组合而成的：

- translate：项目类型
- 中文：您想要翻译成的目标语言
- .md：您想要翻译的文件扩展名
- cn：使用翻译后内容创建的新文件后缀。例如，如果原始文件是 README.md，则新文件将会是 README-cn.md因此，最终的 project_type 是 "translate/中文/.md/cn"

如果您的模型足够强大，您可以使用以下命令执行相同任务：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --model_max_length 2000 --query "将项目中的markdown文档翻译成中文"
```

该模型会从查询中提取出 "translate/中文/.md/cn"，然后执行与上一个命令相同的操作。

注意：model_max_length 用于控制模型生成文本的长度，如果不设置 model_max_length，默认值为 1024。您应根据对翻译文本长度的预估来调整这个值。

### 仅适用于Python项目的特性

为了减少自动编码器收集的上下文长度，如果您正在处理的是Python项目，可以使用以下命令：

```shell 

（由于您未提供具体的Python项目相关命令行代码，此处无法给出相应翻译，请补充相关命令后我将为您完成翻译。）在上述命令中，我们提供了脚本路径和包名，其中 script_path 是您当前正在处理的 Python 文件，而 package_name 是您所关注的包名。这样一来，auto-coder 只会从 package_name 中以及由 script_path 文件导入的部分收集上下文信息，这将显著减少上下文长度。

当您在 `--query` 中提及 `script module` 时，您是指的是 script_path 文件。

任务完成后，您可以从 output.txt 文件中复制生成的提示，并将其粘贴到 ChatGPT 或其他 AI 模型的网页中。

如果您指定了模型，auto-coder 将使用该模型生成结果，然后将结果放入目标文件中。auto-coder --目标文件 /home/winubuntu/projects/ByzerRawCopilot/output.txt --脚本路径 /home/winubuntu/projects/YOUR_PROJECT/xxx.py --包名 xxxx --项目类型 py-script --模型 qianwen_chat --执行 --查询 "帮我实现script模块中还没有实现的方法"

```typescript 项目

尝试将项目类型设置为 ts-script。

## 真实自动模式

以下是一个示例：

```shell
auto-coder --源目录 /home/winubuntu/projects/ByzerRawCopilot --目标文件 /home/winubuntu/projects/ByzerRawCopilot/output.txt --项目类型 copilot --模型最大长度 2000 --模型 qianwen_chat --查询 "帮我创建一个名为t-copilot 的python项目，生成的目录需要符合打包的python项目结构"

```

此项目类型会根据查询自动创建一个Python项目，并基于查询生成结果。

您可以在 `output.txt` 文件中查看所有日志。

auto-coder 还支持Python代码解释器，可以尝试以下命令：  

（由于您未提供具体的Python代码解释器相关命令行示例，请等待您提供后继续翻译。）auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat --query "用python打印你好，中国"

输出文件output.txt的内容将会是：

```text
=================会话内容==================

用户：
根据用户的问题，对问题进行拆解，并生成执行步骤。

环境信息如下：
操作系统：linux 5.15.0-48-generic  
Python版本：3.10.11
Conda环境：byzerllm-dev 
支持Bash

用户提出的问题是：用python打印你好，中国

每次生成一个执行步骤后，询问我是否继续。当我回复“继续”时，继续生成下一个执行步骤。

AI助手：
{
  "code": "print('你好，中国')",
  "lang": "python",
  "总步骤数": 1,
  "当前工作目录": "",
  "环境变量": {},
  "超时时间（秒）": -1,
  "是否忽略错误": false
}

是否继续？
用户：继续
=================结果==================

Python代码：
print('你好，中国')
输出：
你好，中国
--------------------
```

### 结合搜索引擎实现更稳定的结果

若想获得更稳定的结果，应当引入搜索引擎：

```yaml
source_dir: /home/winubuntu/projects/ByzerRawCopilot目标文件：/home/winubuntu/projects/ByzerRawCopilot/output.txt

模型：qianwen_short_chat
模型最大长度：2000
防止配额限制：5

搜索引擎：bing
搜索引擎令牌：xxxxxx

项目类型："copilot"
查询：
```
在/tmp/目录下帮我创建一个由typescript和reactjs组成的项目，项目名为t-project
```

此处我们添加了新参数`search_engine`和`search_engine_token`，搜索引擎将提供更多上下文信息给模型，模型会利用这些上下文信息生成结果。

目前，我们支持bing/google搜索引擎。如果您使用bing，请尝试从[这里](https://www.microsoft.com/zh-cn/bing/apis/bing-web-search-api)获取令牌。

基本工作流程如下：

1. 搜索查询内容
2. 通过片段对搜索结果进行重新排序
3. 获取首个搜索结果，并基于完整内容回答问题
4. 根据查询内容和完整内容生成最终结果
5. 根据结果获取执行步骤
6. 使用auto-coder中的ShellClient/PythonClient执行这些步骤

以下是输出内容：用户尝试：UserIntent.CREATE_NEW_PROJECT
搜索 SearchEngine.BING，内容为“帮我在/tmp/目录下创建一个由typescript + reactjs 组成的项目，项目名字叫 t-project...”
重新排序搜索结果，按片段进行...
获取并依据全文内容回答问题（在/tmp/目录下创建一个由typescript + reactjs 组成的项目，项目名字叫 t-project）的链接是 https://blog.csdn.net/weixin_42429718/article/details/117402097...

用户：
你需熟悉各类编程语言及其对应框架的项目结构。现在，你的任务是
根据用户的问题和提供的信息，对问题进行拆解，并生成执行步骤。当所有步骤执行完毕后，最终帮助生成一个符合相应编程语言规范及所用框架的项目结构。
整个过程仅能使用 python/shell。

当前环境信息如下：
操作系统：linux 5.15.0-48-generic  
Python版本：3.10.11
Conda环境：byzerllm-dev 
支持Bash

现在请参照以下内容：

鉴于提供的上下文信息与在Linux环境下通过命令行创建TypeScript和ReactJS项目并不直接相关，我将基于一般操作流程给出解答。

要在Linux系统的 `/tmp/` 目录下创建一个名为`t-project`的由TypeScript和ReactJS组成的项目，请按照以下步骤操作：

1. 首先，请确保您已在全局环境中安装了Node.js包管理器（npm）以及用于创建React应用的脚手架工具 `create-react-app`。如果尚未安装，可通过以下命令完成安装：
   ```
   npm install -g create-react-app
   ```2. 接下来，由于默认情况下 `create-react-app` 不支持 TypeScript，需要安装 `create-react-app` 的 TypeScript 版本，即 `react-scripts-ts`。但请注意，`react-scripts-ts` 已经停止维护，当前推荐的做法是直接使用 `create-react-app` 并通过添加 `--template typescript` 参数来指定 TypeScript 模板：

   ```shell
   npx create-react-app t-project --template typescript
   ```

   这条命令会在 `/tmp/` 目录下创建一个名为 `t-project` 的新 React 项目，并配置为使用 TypeScript。

3. 创建完成后，进入该项目目录并启动开发服务器：

   ```shell
   cd /tmp/t-project
   npm start
   ```

这样便成功在 `/tmp/` 目录下基于 TypeScript 和 ReactJS 创建了一个项目。[信息缺失]关于如何在 Linux 系统中具体使用命令行创建项目的详细步骤，因为上下文中并未提供相关指导。

针对用户的需求：在 `/tmp/` 目录下创建一个由 TypeScript + ReactJS 构成的项目，项目名称为 `t-project`。

每次展示一个执行步骤，并询问我是否继续。当我回复“继续”时，将生成下一个执行步骤。```json
{
  "lang": "shell",
  "总步骤数": 3,
  "当前步骤": 2,
  "工作目录": "/tmp",
  "环境变量": {},
  "超时时间": null,
  "忽略错误": false
}
```
请在 `/tmp` 目录下执行此命令以创建基于 TypeScript 的 ReactJS 项目。若项目创建成功，请回复“继续”。

user: 继续

```json
{
  "命令": "cd t-project",
  "lang": "shell",
  "总步骤数": 3,
  "当前步骤": 3,
  "工作目录": "/tmp",
  "环境变量": {},
  "超时时间": null,
  "忽略错误": false
}
```
请在终端中切换到刚创建的 `t-project` 目录。若切换成功，请回复“继续”以进行下一步操作，即启动项目开发服务器。

user: 继续

Auto-Coder 中的 ShellClient 将按照上述三个步骤来最终执行新建项目的过程。