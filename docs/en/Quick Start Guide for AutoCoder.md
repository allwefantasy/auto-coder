# Quick Start Guide for AutoCoder

Yesterday, after I released the command-line version of Devin: Auto-Coder, many people contacted me for discussion. So, making it easy for everyone to get started is the top priority. Therefore, from last night to today, I've quickly released two new versions of Byzer-LLM/AutoCoder to support this article.

## Installation

The installation part is actually quite simple, just install the following Python libraries:

```bash
conda create --name autocoder python==3.10.11
conda activate autocoder
pip install -U auto-coder
ray start --head
```

Now, you can start using AutoCoder.

## Web Version Model

For example, if you have a web subscription or free usage rights for products like Claude3, ChatGPT, Kimi, but do not have API subscriptions for these models, then AutoCoder is equivalent to a Code Pack tool, helping you package code and questions into a text file for easy drag-and-drop onto these products' interfaces, and then assisting with code generation.

You can use auto-coder to view some common command options.

```bash
auto-coder -h
```

Let me share a practical case. I wanted to add command-line support to the byzer-llm project. Here is the yaml configuration file I wrote:

```yml
source_dir: /home/winubuntu/projects/byzer-llm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt

urls: https://raw.githubusercontent.com/allwefantasy/byzer-llm/master/README.md 

search_engine: bing
search_engine_token: ENV {{BING_SEARCH_TOKEN}}

query: |
  Add a byzerllm.py file in the src/byzerllm directory. Use args to implement command-line support in this file. Refer to the usage in README.md to add command-line arguments.
  Main support:
  1. Deployment model related parameters
  2. Running inference related statements

  For example, the deployment code is usually like this:

  ```python
  ray.init(address="auto",namespace="default",ignore_reinit_error=True)
  llm = ByzerLLM()

  llm.setup_gpus_per_worker(4).setup_num_workers(1)
  llm.setup_infer_backend(InferBackend.transformers)

  llm.deploy(model_path="/home/byzerllm/models/openbuddy-llama2-13b64k-v15",
            pretrained_model_type="custom/llama2",
            udf_name="llama2_chat",infer_params={})
  ```
  At this point, you need address, num_workers, gpus_per_worker, model_path, pretrained_model_type, udf_name, infer_params, and these parameters can be passed through the command line.

  The final form is:

  byzerllm deploy --model_path /home/byzerllm/models/openbuddy-llama2-13b64k-v15 --pretrained_model_type custom/llama2 --udf_name llama2_chat --infer_params {}

  Similarly for inference. For example, the general inference code is:

  ```python
  llm_client = ByzerLLM()
  llm_client.setup_template("llama2_chat","auto")

  v = llm.chat_oai(model="llama2_chat",conversations=[{
      "role":"user",
      "content":"hello",
  }])
  print(v[0].output)
  ```
  At this point, you need model, conversations, and these parameters can be passed through the command line.

  Your command line form is:

  byzerllm query --model llama2_chat --query "hello" --template "auto"
```

urls specifies the documents that the large model needs to refer to, source_dir defines the code that the large model needs to read, and target_file specifies the location of the generated prompt. The query is what I specifically want the large model to help me with. Now execute this configuration file:

```bash
auto-coder --file test.yml
```

Then drag and drop output.txt onto the large model web interface, click to execute, and the large model starts working.

![](./images/image1.png)

You can see that it is very detailed, telling you what the new file path is and the corresponding code. You just need to copy and paste it into your project.

## Based on Large Model API

We recommend you apply for Qwen at https://dashscope.console.aliyun.com/model which has a large amount of free tokens and good results. After you apply for the Token, deploy it on your local machine with the following command:

```bash

byzerllm deploy  --pretrained_model_type saas/qianwen \
--infer_params saas.api_key=xxxxxxx saas.model=qwen-max \
--model qianwen_chat
```

After the operation is complete, you will have a model instance called qianwen_chat. You can verify whether the deployment is successful with the following command:

```bash

byzerllm query --model qianwen_chat --query "你好"
```

If it outputs normally, it means it is successful. If it fails, you need to uninstall and redeploy. The uninstallation method is:

```bash
byzerllm undeploy --model qianwen_chat
```

Once the model is ready, you can do two things:

1. Let the large model execute directly, then write the result to the target_file.
2. Unlock some new features, such as indexing, organizing and extracting content from urls.

Let's take a look at each one.

The first example is that I hope to use the just deployed model instance qianwen_chat to help optimize a program problem. But because this project is very large, and the maximum input of qianwen_chat is 6000 characters, I can't give all the project files to the large model, and I need to intelligently reduce the input of the large model. Here is a more reasonable configuration:

```yml

project_type: py
source_dir: /home/winubuntu/projects/byzer-llm
target_file: /home/winubuntu/projects/byzer-llm/output.txt

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

skip_build_index: false

search_engine: bing
search_engine_token: ENV {{BING_SEARCH_TOKEN}}

query: |
  Optimize StoreNestedDict in byzerllm.py to be able to parse standard KEY="VALUE" or KEY=VALUE strings
```

Here, we set the model we want to use, as well as the maximum output and input. In addition, we also enabled the indexing feature through skip_build_index.

So, when we run this file for the first time, it will build an index of your project files, then filter out the code related to your current problem to generate prompts.

```bash

auto-coder --file optimize_command_line.yml
```

In this command, we just use the qwen_chat model to generate a prompt of the right size (build index, filter suitable code, if urls are configured, format and extract content from urls, etc.). If you hope qwen_chat can also directly generate code, you can add a parameter:

```bash

auto-coder --file optimize_command_line.yml --execute
```

At this time, the content in target_file is the generated code instead of the prompt.

So you can see, we can make auto-coder more intelligent by configuring our model to generate prompts, and then let the web version of the model actually write the code. Of course, we can also let your configured model directly complete the code writing, which can be controlled by the --execute parameter.

## Let the large model read your code, third-party package code, and API documentation simultaneously, then answer your questions and write code

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
py_packages: openai
urls: https://raw.githubusercontent.com/allwefantasy/byzer-llm/master/README.md 

query: |
  Reference the implementation in src/byzerllm/saas/qianwen to re-implement offical_openai. Note that offical_openai uses the openai module, you need to learn how to use this module to ensure its correct use.
```

Here, your source code is configured through source_dir, your third-party packages are configured through py_packages, and your documentation is configured through urls. Finally, you let the large model answer your questions (query) based on this information. The stronger the model's capabilities, the more impressive the generation effect. If the project is too large, you can configure a model as before to intelligently filter code:

```yml
source_dir: /home/winubuntu/projects/byzer-llm/src/byzerllm/saas
target_file: /home/winubuntu/projects/byzer-llm/output.txt
py_packages: openai
urls: https://raw.githubusercontent.com/allwefantasy/byzer-llm/master/README.md 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

skip_build_index: false

query: |
  Reference the implementation in src/byzerllm/saas/qianwen to re-implement offical_openai. Note that offical_openai uses the openai module, you need to learn how to use this module to ensure its correct use.
```

In fact, we also support integration with search engines, which can give the large model the following capabilities to complete your goals:

1. Read your project source code.
2. Read third-party libraries.
3. Read the documentation links you provide.
4. Search for more reference documents.

We will introduce this separately later.

## Conclusion

What are you waiting for? Get started now. If you encounter any problems, you can leave a message on github.