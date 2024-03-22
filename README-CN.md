<p align="center">
  <picture>    
    <img alt="auto-coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg"  width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder（由Byzer-LLM提供支持）
</h3>

<p align="center">
| <a href="./docs/en"><b>英文</b></a> | <a href="./docs/zh"><b>中文</b></a> |

</p>

---

*最新资讯* 🔥

- [2024/03] 发布Auto-Coder 0.1.18

---

🚀 注意开发者们！🚨 改变游戏规则的Auto-Coder来了，它将把你的AI编程带到一个全新的水平！🌟

借助Byzer-LLM难以置信的力量，这款命令行工具功能丰富，会让你大开眼界：

📂 告别手动收集上下文！Auto-Coder根据源目录的上下文智能生成代码。就像有一个知道你想要的一切的天才助手！

💡 两种模式，无限可能！生成完美的提示语粘贴到基于Web的大模型中，或者让Auto-Coder直接通过Byzer-LLM与私有模型一起施展魔力。选择权在你，结果总是惊人的！

💻 Python？TypeScript？没问题！Auto-Coder支持编程界的所有热门语言。

🌍 走向全球轻而易举！Auto-Coder自动翻译你的项目文件，让你的代码征服世界！

🤖 Copilot模式来了，它是你的新最佳伙伴！凭借内置的shell/Jupyter引擎，Auto-Coder分解任务，设置环境，创建项目，甚至为你修改代码。就像有一个永不知疲倦的超级智能助手！

🧑‍💻 开发者们，准备好让你们的思维被震撼吧！Auto-Coder与ChatGPT等最热门的AI模型无缝集成，将你的开发过程加速到闪电般的速度！🚀

🌟 别再等了！今天就体验Auto-Coder的原始力量，让AI成为你的终极编码伙伴！https://github.com/allwefantasy/auto-coder  🔥

#AutoCoder #AI编程 #游戏改变者 #ByzerLLM #开发工具

## 目录

- [安装](#安装)
- [全新安装](#全新安装)
- [使用](#使用)
  - [基础](#基础)
  - [高级](#高级)
  - [仅Python项目特性](#仅Python项目特性)
  - [TypeScript项目](#TypeScript项目)
  - [实时自动](#实时自动)
    - [带搜索引擎的实时自动](#带搜索引擎的实时自动)

## 安装

```shell
conda create --name autocoder python=3.10.11
conda activate autocoder
pip install -U auto-coder
## 如果你想使用私有/开源模型，请取消注释以下行。
# pip install -U vllm
ray start --head
```

## 为开源/私有模型设置机器

你可以使用Byzer-LLM提供的脚本来设置nvidia驱动/cuda环境：

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy) 

设置好nvidia驱动/cuda环境后，你可以这样安装auto_coder：

```shell
pip install -U auto-coder
```

## 使用

### LLM模型

> 推荐使用千义通问Max/Qwen-Max SaaS模型
> 确保你的模型至少有8k的上下文长度。

尝试使用以下命令部署Qwen-Max：

```shell
byzerllm deploy  --pretrained_model_type saas/qianwen \
--infer_params saas.api_key=xxxxxxx saas.model=qwen-max \
--model qianwen_chat 
```

如果你的SaaS模型支持OpenAI SDK，你可以使用以下命令部署模型：

```shell
byzerllm deploy  --pretrained_model_type saas/official_openai \
--infer_params saas.api_key=xxxxxxx saas.model=yi-34b-chat-0205 saas.base_url=https://api.lingyiwanwu.com/v1  \
--model yi_chat
```

然后你可以使用以下命令测试模型：

```shell
byzerllm query --model qianwen_chat --query "你好"
```

如果你想卸载模型：

```shell
byzerllm undeploy --model qianwen_chat
```

如果你想部署你的私有/开源模型，请尝试这个[链接](https://github.com/allwefantasy/byzer-llm) 

### 基础

auto-coder提供两种方式：

1. 为查询生成上下文，你可以复制并粘贴到ChatGPT/Claud3/Kimi的Web UI。
2. 使用Byzer-LLM的模型直接生成结果。

>> 注意：你应该确保模型支持长上下文长度，例如 >32k。

auto-coder将从源目录收集源代码，然后根据查询生成目标文件中的上下文。

然后你可以复制`output.txt`的内容并粘贴到ChatGPT/Claud3/Kimi的Web UI：

例如：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何让这个系统可以通过 auto-coder 命令执行？" 
```

你也可以把所有参数放入一个yaml文件中：

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

如果你想使用Byzer-LLM的模型，你可以使用以下命令：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --execute --query "重新生成一个 is_likely_useful_file 方法，满足reactjs+typescript 组合的项目。" 
```

在上面的命令中，我们提供了一个模型并启用了执行模式，auto-coder将从源目录收集源代码，然后为查询生成上下文，然后使用模型生成结果，然后将结果放入目标文件。

### 如何减少上下文长度？

如你所知，auto-coder将从源目录收集源代码，然后为查询生成上下文，如果源目录太大，上下文也会很长，模型可能无法处理。

有两种方法可以减少上下文长度：

1. 将source_dir更改为项目的子目录。
2. 启用auto-coder的索引功能。

为了使用索引功能，你应该配置一些额外的参数：

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
  优化 copilot 里的 get_suffix_from_project_type 函数并更新原文件
```

这里我们添加了一个新的参数`skip_build_index`，默认情况下，这个值是true。
如果你将其设置为false并且同时提供了一个模型，那么auto-coder将使用模型为源代码生成索引（这可能需要大量的tokens），索引文件将存储在源目录中的一个名为`.auto-coder`的目录中。

一旦索引创建完成，auto-coder将使用索引来过滤文件并减少上下文长度。请注意，过滤操作也使用模型，并且可能需要tokens，所以你应该谨慎使用。

### 高级

> 这个特性只与Byzer-LLM的模型一起工作。

翻译项目中的markdown文件：

```shell

auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat 
```
当你想要翻译一些文件时，你必须指定model参数。而project_type有点复杂，它是以下参数的组合：

- translate：项目类型
- 中文：你想要翻译成的目标语言
- .md：你想要翻译的文件扩展名
- cn：创建的新文件后缀，包含翻译内容。例如，如果原始文件是README.md，新文件将是README-cn.md

所以最终的project_type是"translate/中文/.md/cn"

如果你的模型足够强大，你可以使用以下命令来做同样的任务：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --model_max_length 2000 --query "把项目中的markdown文档翻译成中文"
```

模型将从查询中提取"translate/中文/.md/cn"，然后做与前一个命令相同的事情。

注意：model_max_length用于控制模型生成的长度，如果未设置model_max_length，默认值是1024。
你应该根据你对翻译长度的估计来更改这个值。

### 仅Python项目特性

为了减少auto-coder收集的上下文长度，如果你正在处理一个Python项目，你可以使用以下命令：

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py-script --query "帮我实现script模块中还没有实现方法"

```

在上面的命令中，我们提供了一个script路径和一个包名，script_path是你目前正在工作的Python文件，而package_name是你关心的，然后auto-coder只从package_name和由script_path文件导入的上下文中收集上下文，这将显著减少上下文长度。

当你在`--query`中提到`script module`时，你的意思是你正在谈论script_path文件。

完成工作后，你可以从output.txt中复制提示并粘贴到ChatGPT或其他AI模型的Web上。

如果你指定了模型，auto-coder将使用模型生成结果，然后将结果放入目标文件。

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/YOUR_PROJECT/xxx.py --package_name xxxx --project_type py-script --model qianwen_chat --execute --query "帮我实现script模块中还没有实现方法" 
```

## TypeScript项目

只需尝试将project_type设置为ts-script。

## 实时自动

这里有一个例子：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat  --query "帮我创建一个名字叫t-copilot 的python项目，生成的目录需要符合包装的python项目结构"

```

这个项目类型将根据查询自动创建一个python项目，然后根据查询生成结果。

你可以在`output.txt`文件中查看所有日志。

auto-coder还支持python代码解释器，尝试这个：

```shell 
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type copilot --model_max_length 2000 --model qianwen_chat  --query "用python打印你好，中国" 
```

output.txt的内容将是：

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

Python Code:
print('你好，中国')
Output:
你好，中国
--------------------
```

### 带搜索引擎的实时自动

如果你想得到更稳定的结果，你应该引入搜索引擎：

```yaml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_short_chat
model_max_length: 2000
anti_quota_limit: 5

search_engine: bing
search_engine_token: xxxxxx

project_type: "copilot"
query: |
  帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project
```

这里我们添加了新的参数`search_engine`和`search_engine_token`，搜索引擎将为模型提供更多的上下文，模型将使用上下文生成结果。

目前，我们支持bing/google。如果你使用bing，请尝试从[这里](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api)获取token。

基本工作流程是：

1. 搜索查询
2. 通过片段对搜索结果进行重排
3. 获取第一个搜索结果，并根据完整内容回答问题。
4. 根据查询和完整内容生成结果。
5. 根据结果获取执行步骤。
6. 通过ShellClient/PythonClient在auto-coder中执行步骤。

这是输出：

```text
用户尝试: UserIntent.CREATE_NEW_PROJECT
search SearchEngine.BING for 帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project...
reraking the search result by snippets...
fetch https://blog.csdn.net/weixin_42429718/article/details/117402097  and answer the quesion (帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project) based on the full content...
user: 
你熟悉各种编程语言以及相关框架对应的项目结构。现在，你需要
根据用户的问题，根据提供的信息，对问题进行拆解，然后生成执行步骤，当执行完所有步骤，最终帮生成一个符合对应编程语言规范以及相关框架的项目结构。
整个过程只能使用python/shell。

环境信息如下:
操作系统: linux 5.15.0-48-generic  
Python版本: 3.10.11
Conda环境: byzerllm-dev 
支持Bash

现在请参考下面内容：

由于提供的上下文信息与在Linux环境下使用命令行创建一个TypeScript和ReactJS项目无关，我将基于一般操作步骤给出解答。

要在Linux系统的 `/tmp/` 目录下创建一个由TypeScript和ReactJS组成的项目，并命名为`t-project`，请按照以下步骤操作：

1. 首先，请确保您已全局安装了Node.js包管理器（npm）以及创建React应用的脚手架工具 `create-react-app`。如果尚未安装，可以通过以下命令安装：
   \```
   npm install -g create-react-app
   \```

2. 然后，由于`create-react-app`默认不支持 TypeScript，需要安装 `create-react-app` 的 TypeScript 版本，即 `react-scripts-ts`，但请注意，`react-scripts-ts` 已不再维护，最新推荐做法是直接使用 `create-react-app` 并通过 `--template typescript` 参数指定 TypeScript 模板：

   \```sh
   npx create-react-app t-project --template typescript
   \```

   这条命令会在 `/tmp/` 目录下创建名为 `t-project` 的新React项目，并配置为使用TypeScript。

3. 创建完成后，进入项目目录并启动开发服务器：

   \```sh
   cd /tmp/t-project
   npm start
  \ ```

这样就成功在 `/tmp/` 目录下创建了一个基于TypeScript和ReactJS的项目。[information is missing on]如何具体使用命令行在Linux系统中创建项目，因为上下文没有提供相关指导。

用户的问题是：帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project

每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。        

assistant: \```json
{
  "code": "npm install -g create-react-app",
  "lang": "shell",
  "total_steps": 3,
  "current_step": 1,
  "cwd": "/tmp",
  "env": {},
  "timeout": null,
  "ignore_error": false
}
\```
请确认是否已安装全局的 `create-react-app` 工具。如果确认或执行完成，请回复“继续”。

user: 继续

assistant: \```json
{
  "code": "npx create-react-app t-project --template typescript",
  "lang": "shell",
  "total_steps": 3,
  "current_step": 2,
  "cwd": "/tmp",
  "env": {},
  "timeout": null,
  "ignore_error": false
}
\```
请在 `/tmp` 目录下执行此命令以创建基于 TypeScript 的 ReactJS 项目。如果项目创建完成，请回复“继续”。

user: 继续

assistant: \```json
{
  "code": "cd t-project",
  "lang": "shell",
  "total_steps": 3,
  "current_step": 3,
  "cwd": "/tmp",
  "env": {},
  "timeout": null,
  "ignore_error": false
}
\```
请在终端中切换到刚创建的 `t-project` 目录。若切换成功，请回复“继续”以进行下一步操作，即启动项目开发服务器。

user: 继续
```