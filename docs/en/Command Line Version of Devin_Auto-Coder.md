# The Command Line Version of Devin Arrives: Auto-Coder

## Introduction

Starting from last Thursday, we implemented the first usable version within an extreme ten hours. During this period, we successfully achieved bootstrapping, meaning we used Auto-coder's fundamental functions to assist in the development of Auto-coder itself, thus the remarkable speed.

Today, this article will introduce the value Auto-Coder can bring to programmers.

## Is GitHub Copilot Enough?

GitHub Copilot is essentially a derivative of IDE tools, a more "intelligent" code suggestion. Its provided Copilot Chat is merely integrating a chat box into the IDE, no different from integrating a search box into an IDE tool. It remains a product of classical product thinking.

More specifically, I can analyze from three dimensions:

The first dimension is GitHub Copilot's positioning. I have been a hardcore user of GitHub Copilot, but its positioning as only a code suggestion tool dictates that it must pursue response time over effectiveness. Hence, its biggest issue is the inability to implement new code based on the entire project's source code (this would cause unacceptable delays and too high costs).

The second dimension is GitHub Copilot's inability to simulate human development behavior. In actual development, we usually base it on existing functionalities and develop according to some "documentation," "third-party code," and "search engines."

For example, if Byzer-LLM wants to interface with the Qwen-vl multimodal large model, as a developer, I need to prepare three things:

1. First, we need to understand and refer to how Byzer-LLM previously interfaced with various models.
2. Secondly, I need to find the API documentation of Qwen-VL to understand its API.
3. I might also need to search and refer to how others have interfaced with it, and if I used a third-party SDK, I would need its documentation or code.

Only after obtaining this information can we write reliable code. But can GitHub Copilot do these? Obviously not.

The third dimension is that I cannot replace the model, meaning I can only use the model behind GitHub Copilot, even if I have a web subscription to GPT-4/Claude3-Opus. If it's used by a company, how can we ensure the model's private deployment?

Therefore, the essence of the GitHub Copilot product determines that it is just a smarter suggestion tool, not simulating human programming. Although it's not against the AGI trend, it's indeed not enough AI Native, not making full use of AI.

Based on the above issues, Auto-Coder was developed.

The purely human part of programming involves:

1. Understanding requirements
2. Searching to see how others solve similar problems and clarifying thoughts
3. Reviewing existing project codes
4. Studying the source code or documentation of the third-party libraries to be used

AutoCoder assists in reading existing code, referring to documentation, automatically using search engines to gather relevant information, and finally trying to understand the programmer's requirements. With this information, it can generate sufficiently good code.

Let's look at some typical scenarios of Auto-Coder.

## Typical Scenarios of Auto-Coder

### Case 1: Adding a Feature to an Existing Project

The first typical case is adding a feature to an existing project, with the general requirement of adding a command-line parameter and having a class named HttpDoc handle this new parameter. You can refer to the query part below for detailed requirements.

```yml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

query: |
  Add a new command-line parameter --urls that can specify multiple HTTP links separated by commas
  Implement an HttpDoc class, retrieve the specified HTTP links, obtain the content of the links, and return a list of SourceCode objects
  In the HttpDoc class, implement a method to extract the main body of content using the llm.chat_oai method
```

The first line, `source_dir`, specifies the current project, and the second line, `target_file`, indicates that AutoCoder will save the generated prompt into this file after collecting project details and user requirements.

Then, you just need to run:

```bash
auto-coder -f actions/add_urls_command_parameter.yml
```

This will generate the appropriate prompt into the `output.txt` file. Then, you can drag this file into web interfaces like GPT4/Claude/KimiChat, etc., and they will generate the code, which you just need to copy and paste into your project.

Of course, if you wish the system to automatically complete code generation, you can add two more parameters:

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
  Add a new command-line parameter --urls that can specify multiple HTTP links separated by commas
  Implement an HttpDoc class, retrieve the specified HTTP links, obtain the content of the links, and return a list of SourceCode objects
  In the HttpDoc class, implement a method to extract the main body of content using the llm.chat_oai method
```

Here, two new parameters were added: one is `model`, configuring a large model that AutoCoder can directly call, and the other is `execute`. This way, AutoCoder will automatically call the model to answer your question and save the results in the `output.txt` file.

If you are confident enough in the code generated by AutoCoder, you can configure the `auto_merge` parameter, allowing AutoCoder to automatically merge the changes into your existing project code.

### Case 2: Adding a Feature to an Existing Project, But Need to Refer to a Document

The second case: Referencing an API document, then adding an interface to the existing code based on that. This is a common task for programmers.

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
urls: https://help.aliyun.com/zh/dashscope/developer-reference/tongyi-qianwen-vl-plus-api?disableWebsiteRedirect=true
query: |
  Study the Tongyi Qianwen VL documentation, then implement a saas/qianyi_vl based on the interface specification in saas/qianwen.
```

Here we added a `urls` parameter to specify the document address. The system will automatically collect your existing source code and API document, then store them with your question in the `output.txt` file. You can then drag this file into web interfaces like GPT4/Claude/KimiChat, etc., and they will generate the code for you to copy and paste into your project.

### Case 3: Adding a Feature to an Existing Project, Including Referring to a Document and a Third-party Library's Source Code

The third case, I need to use a certain library, but the library's documentation is scarce (or incomplete), and I need to develop a feature based on this library. Can the large model read the library's source code on its own, then, combining my existing code, implement a feature? No problem!

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
py_packages: openai
query: |
  Refer to the implementation in src/byzerllm/saas/qianwen, reimplement offical_openai. Note that offical_openai
  uses the openai module, you need to learn how to use this module, ensuring its correct functionality.
```

Here, I specified AutoCoder to pay special attention to the `openai` SDK library. Then, I asked it to reference my previous implementation interfacing with Qianwen, using the openai library to interface with the OpenAI model. Eventually, the system will combine OpenAI, my project, and my requirements into a prompt, then put it in `output.txt`. If you have an API, you can also configure the model parameter, and the system will automatically call the model to answer questions.

### Case 4: Creating a New Project

The fourth case, I want to create a project with reactjs+typescript, but I forgot how to do it exactly. Can the large model automatically help me create it? No problem.

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
  Help me create a project composed of typescript + reactjs in the /tmp/ directory, named t-project
```

Two additional configurations are needed here: one to configure a model and another for a search engine. Auto-Coder will operate as follows:

1. Use the search engine to find related operations.
2. The large model reads the search results and identifies the most suitable content.
3. Extract the main content from the document, understand it.
4. Extract the steps needed to solve the problem and generate code.
5. Use the built-in Shell/Python executor to execute the steps.

This allows you to see the internal log:

```text
User attempt: UserIntent.CREATE_NEW_PROJECT
search SearchEngine.BING for "Help me create aproject composed of TypeScript + ReactJS in the /tmp/ directory, named t-project"...
re-ranking the search result by snippets...
fetching https://blog.csdn.net/weixin_42429718/article/details/117402097 and answering the question based on the full content...
user: 
You are familiar with various programming languages and the corresponding project structures for related frameworks. Now, based on the information provided, you need to decompose the user's question, generate execution steps, and help create a project structure that meets the specifications of the corresponding programming language and framework.
The entire process can only use Python/shell.

Environmental info as follows:
Operating system: Linux 5.15.0-48-generic  
Python version: 3.10.11
Conda environment: byzerllm-dev 
Supports Bash

Now, please refer to the following content:

Since the provided context information is unrelated to creating a TypeScript and ReactJS project in a Linux environment using the command line, I'll give a general solution.

To create a project composed of TypeScript and ReactJS in the `/tmp/` directory, named `t-project`, follow these steps:

1. First, ensure you have globally installed the Node.js package manager (npm) and the `create-react-app` scaffolding tool. If not installed, you can install them with the following command:
   
   npm install -g create-react-app   

2. Since `create-react-app` doesn't support TypeScript by default, you need to use the `--template typescript` parameter to specify a TypeScript template:

   
   npx create-react-app t-project --template typescript
   

   This command will create a new React project named `t-project` in the `/tmp/` directory, configured to use TypeScript.

3. After creation, enter the project directory and start the development server:

   
   cd /tmp/t-project
   npm start
   

This successfully creates a project based on TypeScript and ReactJS in the `/tmp/` directory.

The user's question was: Help me create a project composed of TypeScript + ReactJS in the /tmp/ directory, named t-project.

Each time a step is generated, ask me if I want to continue. When I reply to continue, generate the next step.


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


Please confirm if the `create-react-app` tool is already installed globally. If confirmed or after completion, please reply "continue".

user: continue


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


Please execute this command in the `/tmp` directory to create a TypeScript-based ReactJS project. If the project is created, please reply "continue".

user: continue


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


Please switch to the newly created `t-project` directory in the terminal. If successfully switched, reply "continue" to proceed with the next operation, which is to start the project development server.

user: continue
```

As can be seen, three steps are sufficient to solve the user's problem.

### What if the Project is Very Large?

The essence of this issue is:
1. Tokens are expensive.
2. Large models can only accept limited information at a time.

Auto-Coder can index your project. After indexing, it will automatically find the files that may need modification based on your question. Based on these files, it will determine which other files they use, and then only compile this file information and your question into a prompt, which is then answered by the large model.

Enabling indexing is also simple, just add a `skip_build_index` parameter.

It's worth noting that building the index depends on a large model with an API, so you must configure the `model` parameter, otherwise it will not take effect.

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt

skip_build_index: false

model: qianwen_short_chat
model_max_length: 2000
anti_quota_limit: 5

query: |
  Refer to the implementation in src/byzerllm/saas/qianwen, and reimplement official_openai. Note that official_openai
  uses the openai module, you need to learn how to use this module, ensuring its correct functionality.
```

Once indexing is enabled, Auto-Coder will automatically build an index and, based on the user's requirement description, will:

1. Automatically filter relevant source code files.
2. From those selected source files, further filter out the files they depend on.

In general, after such filtering, there should be only a few or a dozen files, which should meet most of the needs for code generation.

## In Summary

Using Auto-Coder, it can read the source code you've written, API documentation, and the code of third-party libraries, then write code and add new features according to your requirements. It can also automatically search engines, find suitable articles to read, and then automatically complete basic tasks including project creation. It's also convenient to use, supporting command-line operations and configuration through YAML.