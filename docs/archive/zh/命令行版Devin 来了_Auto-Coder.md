# 命令行版Devin 来了: Auto-Coder

## 前言

从上周四开始，极限十小时实现了第一个可用版本，在这期间，我们成功实现了自举，也就是利用 Auto-coder 的基础功能来帮助 Auto-coder的开发，所以才有如此神速。

今天这篇文章，我们来介绍下 Auto-Coder 到底可以给程序员带来什么价值。

## Github Copilot 够么？

Github Copilot 本质还是IDE工具的衍生，是一个更加“智能”的代码提示，而其提供的Copilot Chat 则更加只是把一个聊天框做到IDE而已，和集成一个搜索框到IDE工具没有任何区别，然还是一个古典产品的思维在做的一个产品。

更细节的，我可以从三个维度做给大家做分析：

第一个维度是 Github Copilot 的定位，我一直是 Github Copilot 的铁杆用户，但因为它的定位是只能代码提示，这决定了他需要追求响应延时而不是效果，所以他最大的问题是，它无法基于整个项目的源码去做新的代码实现（这样会导致延时增加到不可接受，并且成本太高）。

第二个维度是 Github Copilot 无法模拟人类的开发行为，我们实际做开发的时候，一般都是基于已有功能，并且根据某种“文档”，“第三方代码”和“搜索引擎”来进行开发。

比如 Byzer-LLM 要对接 Qwen-vl 多模态大模型，那么作为一个开发，我至少需要准备三个事情：

1. 首先我们需要了解和参考Byzer-LLM 之前是怎么对接各种模型的代码
2. 其次我要找到 Qwen-VL的API 文档了解 Qwen-VL 的API
3. 我可能还需要搜索下参考下别人是怎么对接的，以及如果我使用了第三方SDK，我还需要第三方SDK的文档或者代码。

只有获取了这些信息之后，我们才能写出一个靠谱的代码。但 Github copilot 能做到这些么？显然做不到。

第三个维度是，我没有办法替换模型，也就是只能用 Github Copilot 背后的模型，哪怕我有 GPT-4/Claude3-Opus的 web订阅版，如果是公司在用，如何保证模型的私有化部署呢？

所以 Github Copilot 的产品本质决定了他只是一个更加smart的提示工具，而不是模拟人去编程。这个虽然说不上逆AGI潮流，但确实不够 AI Native, 没有把AI 充分利用起来。

基于上面的问题，所以有了 Auto-Coder。



人类单纯编程部分，无非是

1.  理解需求

2. 搜索看别人怎么解决类似问题，理清思路

3. 看已有项目的代码

4. 看要用到的第三方库的源码或者文档

AutoCoder 会在阅读已有代码，参考文档，自动进行搜索引擎获取相关信息，最后尝试去理解程序员的需求，有了这些信息后，才最后进行生成代码，最终
能够生成足够好的代码。

我们来看看 Auto-Coder 的一些典型场景。

## Auto-Coder 的典型场景

### Case 1: 给已有项目加一个功能

第一个典型Case 是，就是我要给目前已有的一个项目加一个功能，大致需求是加一个命令参数，并且要有一个叫做HttpDoc类处理这个新加的参数。
大家可以看看下面 query 部分来了解详细需求。

```yml

source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

query: |
  新增一个命令行参数 --urls 可以指定按逗号分隔的多个http链接
  实现一个 HttpDoc 类，获取指定的http链接，获取链接的内容，返回 SourceCode 对象列表
  在 HttpDoc 类实现一个抽取正文的方法，llm.chat_oai 方法来完成

```
第一行 source_dir 指定了我当前所在的项目，第二行 target_file， AutoCoder 会将收集到项目详细以及用户的需求生成
一个Prompt 保存到指定了输出这个文件里。

接着，你只要运行：

```bash
auto-coder -f actions/add_urls_command_paraemeter.yml
```

就可以生成合适的Prompt到  output.txt 文件里。接着你就可以把这个文件拖拽到比如 GPT4/Claude/KimiChat 等 Web 里，他们会生成代码，你只要复制黏贴到项目里即可。

当然，如果你希望能够系统自动完成代码生成，则可以新增两参数：

```yml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 100000
anti_quota_limit: 5

execute: true
auto_merge: true

query: |
  新增一个命令行参数 --urls 可以指定按逗号分隔的多个http链接
  实现一个 HttpDoc 类，获取指定的http链接，获取链接的内容，返回 SourceCode 对象列表
  在 HttpDoc 类实现一个抽取正文的方法，llm.chat_oai 方法来完成
```

这里新增加了两个参数，一个是 model 配置一个 AutoCoder可以直接调用的大模型， 一个是 execute。这样 Auto-Coder 会自动调用模型回答你的问题，并且把结果保存到 output.txt 文件里。

如果你对 AutoCoder 生成的代码足够放心，你可以配置 auto_merge 参数，这样 AutoCoder 会把修改自动合并代码到你已有的项目代码里去。

### Case 2: 给已有项目加一个功能，除了已有项目，还需要参考一个文档才行

第二个Case: 参考一个API文档，然后根据已有代码新增某个接口的对接。这个应该是程序员经常要做的事情。

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
urls: https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-qianwen-vl-plus-api?disableWebsiteRedirect=tru
query: |
  学习通义千问VL文档，然后参考 saas/qianwen 中的接口规范实现，实现一个 saas/qianyi_vl。

```

这里我们新增了一个 urls 参数，指定文档地址，然后系统会自动获取你现有的源码以及API文档，然后和你的问题一起存储到 output.txt 文件里，然后你就可以拖拽到比如 GPT4/Claude/KimiChat 等 Web 里，他们会生成代码，你只要复制黏贴到项目里即可。

### Case 3: 给已有项目加一个功能，除了已有项目，还需要参考一个文档，还需要参考一个第三方库的源码

第三个case, 我要使用某个库，但是这个库的文档比较少（或者不全），我需要基于这个库开发一个功能，能不能让大模型自己阅读那个库的源码，然后结合我现有的代码，实现一个功能？没问题！

```yml

source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
py_packages: openai
query: |
  参考 src/byzerllm/saas/qianwen 中的实现，重新实现 offical_openai。注意 offical_openai 中
  使用的是openai 这个模块，你需要学习这个模块的使用方法，保证正确的使用其功能。
```

这里我指定 Auto-Coder 要特别关注 openai 这个 SDK库，然后我让他参考以前我实现对 qianwen的对接，用openai 这个库，实现对 OpenAI 模型的对接。最终系统会把 OpenAI, 我自己的项目，以及我的要求合并成一个prompt,然后放到 output.txt里。如果你有API，也可以配置下 model参数，然后系统会自动调用模型回答问题。

### Case 4: 创建一个新项目
第四个case，我想创建一个 reactjs+typescript 的项目，但是我忘了具体怎么弄了，能不能让大模型自动帮我创建？没问题的

```yml

source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_short_chat
model_max_length: 2000
anti_quota_limit: 5

search_engine: bing
search_engine_token: xxxxxxx

project_type: "copilot"
query: |
  帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project

```

这里需要额外配置两个：第一个是配置一个模型，第二个是配置一个搜索引擎。Auto-Coder 会按如下逻辑进行操作：

1. 通过搜索引擎检索相关的操作。
2. 大模型会对检索结果进行阅读，并且找到最合适的那篇内容
3. 取到那篇文档，并且提取正文，进行理解
4. 抽取解决这个问题需要的步骤，生成代码 

5. 利用内置的Shell/Python 执行器按步骤执行。

可以给大家看看内部的日志：

```text
用户尝试: UserIntent.CREATE_NEW_PROJECT
search SearchEngine.BING for 帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project...
reraking the search result by snippets...
fetch https://blog.csdn.net/weixin_42429718/article/details/117402097 and answer the quesion (帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project) based on the full content...
user: 
你熟悉各种编程语言以及相关框架对应的项目结构。现在，你需要
根据用户的问题，根据提供的信息，对问题进行拆解，然后生成执行步骤，当执行完所有步骤，最终帮生成一个符合对应编程语言规范以及相关框架的项目结构。
整个过程只能使用 python/shell。

环境信息如下:
操作系统: linux 5.15.0-48-generic  
Python版本: 3.10.11
Conda环境: byzerllm-dev 
支持Bash

现在请参考下面内容：

由于提供的上下文信息与在Linux环境下使用命令行创建一个TypeScript和ReactJS项目无关，我将基于一般操作步骤给出解答。

要在Linux系统的 `/tmp/` 目录下创建一个由TypeScript和ReactJS组成的项目，并命名为`t-project`，请按照以下步骤操作：

1. 首先，请确保您已全局安装了Node.js包管理器（npm）以及创建React应用的脚手架工具 `create-react-app`。如果尚未安装，可以通过以下命令安装：
   
   npm install -g create-react-app
   

2. 然后，由于`create-react-app`默认不支持 TypeScript，需要安装 `create-react-app` 的 TypeScript 版本，即 `react-scripts-ts`，但请注意，`react-scripts-ts` 已不再维护，最新推荐做法是直接使用 `create-react-app` 并通过 `--template typescript` 参数指定 TypeScript 模板：

   
   npx create-react-app t-project --template typescript
   

   这条命令会在 `/tmp/` 目录下创建名为 `t-project` 的新React项目，并配置为使用TypeScript。

3. 创建完成后，进入项目目录并启动开发服务器：

   
   cd /tmp/t-project
   npm start
   

这样就成功在 `/tmp/` 目录下创建了一个基于TypeScript和ReactJS的项目。[information is missing on]如何具体使用命令行在Linux系统中创建项目，因为上下文没有提供相关指导。

用户的问题是：帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project

每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。

assistant: 
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

请确认是否已安装全局的 `create-react-app` 工具。如果确认或执行完成，请回复“继续”。

user: 继续

assistant: 
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

请在 `/tmp` 目录下执行此命令以创建基于 TypeScript 的 ReactJS 项目。如果项目创建完成，请回复“继续”。

user: 继续

assistant: 
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

请在终端中切换到刚创建的 `t-project` 目录。若切换成功，请回复“继续”以进行下一步操作，即启动项目开发服务器。

user: 继续
```


可以看到，最终需要三个步骤就可以帮助用户解决这个问题。

### 如果项目很大怎么办

这个问题的本质是：
1. Token 很贵
2. 大模型一次能接受的信息有限

Auto-Coder 可以对你的项目做索引，做完索引后，会自动根据你的问题找到可能需要修改的文件，基于这些文件，再找这些文件会使用哪些其他文件，然后只把这些文件的信息和你的问题一起形成prompt 然后让大模型来回答。

开启索引也很简单，只要添加一个 skip_build_index 参数即可。

值得注意的事， 索引的构建需要依赖有API的大模型,所以必须配置 model参数，不然不会生效。

```yml

source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt

skip_build_index: false

model: qianwen_short_chat
model_max_length: 2000
anti_quota_limit: 5

query: |
  参考 src/byzerllm/saas/qianwen 中的实现，重新实现 offical_openai。注意 offical_openai 中
  使用的是openai 这个模块，你需要学习这个模块的使用方法，保证正确的使用其功能。
```

一旦开启索引，Auto-Coder 会自动构建索引，根据用户的需求描述,同时：

1. 自动筛选相关的源码文件。
2. 从筛选出来的源码文件，再筛选一级他们依赖的文件。

一般情况，经过这样的筛选，应该也就几个或者十几个文件，也能满足大部分代码生成的需求。

## 总结下

使用 Auto-Coder,  他可以自己阅读你已经写的源码，阅读API文档，阅读第三方类库的代码，然后根据你的要求编写代码，添加新功能。也可以自动去搜索引擎，找到合适的文章进行阅读，然后自动帮你完成包括项目创建等在内的基础工作。使用起来也很方便，支持命令行以及通过 YAML 进行配置。

