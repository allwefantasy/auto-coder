# Command Line Version of Devin: Auto-Coder

## Introduction

Since last Thursday, we've achieved the first usable version in an extreme ten-hour sprint. During this period, we successfully implemented self-bootstrapping, which means using the basic features of Auto-Coder to assist in the development of Auto-Coder itself, hence the incredible speed.

In today's article, we will introduce what value Auto-Coder can bring to programmers.

## Is Github Copilot Enough?

For this matter, I will analyze it from three dimensions.

The first dimension is the positioning of Github Copilot. I have always been a staunch user of Github Copilot, but its positioning determines that it needs to pursue response latency rather than effectiveness. Therefore, its biggest problem is that it cannot create new code implementations based on the entire project's source code (this would increase latency to an unacceptable level and the cost would be too high).

The second dimension is that Github Copilot cannot simulate human development behavior. When we actually develop, we usually base it on existing functionality and develop according to some kind of "documentation".

For example, if Byzer-LLM needs to interface with the Qwen-vl multi-modal large model, then as a developer, I at least need to prepare two things:

1. First, we need to understand and refer to how Byzer-LLM previously interfaced with various models.
2. Secondly, I need to find the API documentation for Qwen-VL.

In fact, large models also need this information to write reliable code.

The third dimension is that I cannot replace the model, which means I can only use the model behind Github Copilot. Even if I have the web subscription version of GPT-4/Claude3-Opus, I can use it, but there is no tool that can conveniently help me generate code context, preventing large models from understanding what project you are currently working on. You can only inefficiently let him help you solve some minor details and spend a lot of effort telling him what you need to accomplish and how to accomplish it. In fact, if you could give the entire project's source code to him, and then say what new features you need, the large model can quickly generate quite excellent models.

Auto-Coder can help you automatically generate a project source code Prompt for online models, which is convenient for you to paste into web versions like GPT4/Claude/KimiChat, and it can also specify an API model to help you complete complex code generation functions locally.

Based on the analysis of the above three dimensions, we have Auto-Coder.

## Typical Scenarios for Auto-Coder

The first typical case is that I want to add a feature to the current project, for example, below, I want to add a command-line argument and have an HttpDoc class that can handle this newly added argument.

```yml

source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

query: |
  Add a new command-line argument --urls that can specify multiple http links separated by commas
  Implement an HttpDoc class to get the specified http links, get the content of the links, and return a list of SourceCode objects
  Implement a method in the HttpDoc class to extract the main text, using the llm.chat_oai method to complete

```

Then I just need to specify what my current project address is, describe what I want to do, and then run the following command:

```bash
auto-coder -f actions/add_urls_command_paraemeter.yml
```

This will generate the appropriate Prompt into the output.txt file. Then you can drag and drop this file into web versions like GPT4/Claude/KimiChat, which will generate code, and you just need to copy and paste it into your project.

The second case: refer to an API documentation and then add the interface docking for an existing code. This should be something programmers often have to do.

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
urls: https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-qianwen-vl-plus-api?disableWebsiteRedirect=tru 
query: |
  Study the Tongyi Qianwen VL documentation, then refer to the interface specifications in saas/qianwen to implement a saas/qianyi_vl.

```

Here we added a urls parameter, specifying the document address, and then the system will automatically obtain your existing source code and API documentation, store them together with your question in the output.txt file, and then you can drag and drop it into web versions like GPT4/Claude/KimiChat, which will generate code, and you just need to copy and paste it into your project.

What if I have an API and don't use the web version? No problem!

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
urls: https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-qianwen-vl-plus-api?disableWebsiteRedirect=true 

model: qianwen_short_chat
model_max_length: 2000
anti_quota_limit: 5

query: |
  Study the Tongyi Qianwen VL documentation, then refer to the interface specifications in saas/qianwen to implement a saas/qianyi_vl.

```

Here, we added a new model called `qianwen_short_chat`. At this point, the model will directly combine the API documentation, your existing source code, and your question, then answer your question and save the result in the output.txt file.

The fourth case, I want to use a certain library, but this library has little (or incomplete) documentation. Can I let the large model read the source code of that library and then combine it with my existing code to implement a feature? No problem!

```yml

source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
py_packages: openai
query: |
  Reference the implementation in src/byzerllm/saas/qianwen and re-implement offical_openai. Note that offical_openai uses the openai module, you need to learn how to use this module to ensure correct use of its functionality.
```

Here I specified that Auto-Coder should pay special attention to the openai SDK library, and then I asked it to refer to my previous implementation of the interface with qianwen, using the openai library to implement the interface with the OpenAI model. Finally, the system will merge OpenAI, my own project, and my requirements into a single prompt and put it into the output.txt. If you have an API, you can also configure the model parameter, and the system will automatically call the model to answer your question.

The fifth case, I want to create a reactjs+typescript project, but I forgot exactly how to do it, can I let the large model automatically help me create it? No problem!

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
  Create a project composed of typescript + reactjs in the /tmp/ directory, and name the project t-project

```

Here you need to configure two additional things: the first is to configure a model, and the second is to configure a search engine. Auto-Coder will operate according to the following logic:

1. Search the search engine for related operations.
2. The large model will read the search results and find the most suitable content.
3. Obtain the document and extract the main text for understanding.
4. Extract the steps needed to solve the problem and generate code.

5. Use the built-in Shell/Python executor to execute the steps.

Here's a look at the internal log:

```text
User attempted: UserIntent.CREATE_NEW_PROJECT
search SearchEngine.BING for Create a project composed of typescript + reactjs in the /tmp/ directory, and name the project t-project...
ranking the search result by snippets...
fetch https://blog.csdn.net/weixin_42429718/article/details/117402097 and answer the question (Create a project composed of typescript + reactjs in the /tmp/ directory, and name the project t-project) based on the full content...
user: 
You are familiar with various programming languages and the corresponding project structures of related frameworks. Now, you need to
dismantle the user's question based on the provided information, and generate execution steps. After all steps are completed, ultimately help generate a project that conforms to the norms of the corresponding programming language and related frameworks.
The entire process can only use python/shell.

Environment information is as follows:
Operating System: linux 5.15.0-48-generic  
Python version: 3.10.11
Conda environment: byzerllm-dev 
Supports Bash

Since the provided context information is not related to creating a TypeScript and ReactJS project in the Linux command line environment, I will provide an answer based on general operating steps.

To create a project composed of TypeScript and ReactJS in the `/tmp/` directory and name it `t-project`, please follow these steps:

1. First, please ensure that you have globally installed the Node.js package manager (npm) and the scaffolding tool for creating React applications, `create-react-app`. If not installed, you can install it with the following command:
   ```
   npm install -g create-react-app
   ```

2. Then, since `create-react-app` does not support TypeScript by default, you need to install the TypeScript version of `create-react-app`, which is `react-scripts-ts`. However, please note that `react-scripts-ts` is no longer maintained, and the latest recommended practice is to directly use `create-react-app` and specify the TypeScript template with the `--template typescript` parameter:

   ```sh
   npx create-react-app t-project --template typescript
   ```

   This command will create a new React project named `t-project` in the `/tmp/` directory and configure it to use TypeScript.

3. After creation, enter the project directory and start the development server:

   ```sh
   cd /tmp/t-project
   npm start
   ```

This successfully creates a TypeScript and ReactJS-based project in the `/tmp/` directory. [Information is missing on] how to specifically use the command line to create a project in the Linux system, as the context does not provide relevant guidance.

The user's question is: Help me create a typescript + reactjs project in the /tmp/ directory, and name the project t-project.

Each time a step is generated, ask me if I want to continue. When I reply "continue," continue generating the next step.

Assistant: ```json
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
```
Please confirm whether the `create-react-app` tool is installed globally. If confirmed or completed, please reply "continue."

User: Continue

Assistant: ```json
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
```
Please execute this command in the `/tmp` directory to create a ReactJS project based on TypeScript. If the project creation is completed, please reply "continue."

User: Continue

Assistant: ```json
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
```
Please switch to the newly created `t-project` directory in the terminal. If the switch is successful, please reply "continue" to proceed to the next step, which is to start the project development server.

User: Continue
```

As can be seen, ultimately, only three steps are needed to help the user solve this problem.

## What if the project is very large

The essence of this question is:
1. Tokens are expensive
2. Large models can only accept a limited amount of information at a time

Auto-Coder can index your project, and after indexing, it will automatically find the files that may need to be modified based on your question. Based on these files, it will then find which other files these files will use, and then only form a prompt with the information of these files and your question and let the large model answer.

Turning on indexing is also simple, just add a `skip_build_index` parameter.

It is worth noting that the construction of the index depends on a large model with an API, so the `model` parameter must be configured, otherwise, it will not take effect.

```yml

source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt

skip_build_index: false

model: qianwen_short_chat
model_max_length: 2000
anti_quota_limit: 5

query: |
  Reference the implementation in src/byzerllm/saas/qianwen and re-implement offical_openai. Note that offical_openai uses the openai module, you need to learn how to use this module to ensure correct use of its functionality.
```

## Summary

With Auto-Coder, it can read your existing source code, read API documentation, read the code of third-party libraries, and then write code and add new features according to your requirements. It can also automatically search the web, find suitable articles for reading, and then automatically help you complete basic tasks including project creation. It is also very convenient to use, supporting command line as well as configuration through YAML.