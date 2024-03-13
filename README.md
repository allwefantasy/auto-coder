
<p align="center">
  <picture>    
    <img alt="auto-coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder (based on Byzer-LLM)
</h3>

<p align="center">
| <a href="./README.md"><b>English</b></a> | <a href="./README-CN.md"><b>中文</b></a> |

</p>

---

*Latest News* 🔥

- [2024/03] Release Auto-Coder 0.1.2

---


## Brand new Installation

You can use the script provided by Byzer-LLM to setup the nvidia-driver/cuda environment:

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

After the nvidia-driver/cuda environment is set up, you can install auto_coder like this:

```shell
pip install -U auto-coder
```

## Existing Installation


```shell
# or https://gitcode.com/allwefantasy11/auto-coder.git
git clone https://github.com/allwefantasy/auto-coder.git
pip install -r requirements.txt
## if you want to use private/open-source models, uncomment this line.
# pip install -U vllm
pip install -U byzerllm
pip install -U auto-coder
```

## Usage 

### Basic 
> Recommend to use 千义通问Max/Qwen-Max SaaS model
> You should deploy the model by [Byzer-LLM](https://github.com/allwefantasy/byzer-llm)


The auto-coder provide two ways:

1. Generate context for the query and used in Web of ChatGPT or other AI models.
2. Use the model from Byzer-LLM to generate the result directly.

>> Note: You should make sure the model has a long context length support, e.g. >32k. 

The auto-coder will collect the source code from the source directory, and then generate context into the target file based on the query.

Then you can copy the content of `output.txt` and paste it to Web of ChatGPT or other AI models:

For example:

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何让这个系统可以通过 auto-coder 命令执行？" 
```

If you want to use the model from Byzer-LLM, you can use the following command:

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --execute --query "重新生成一个 is_likely_useful_file 方法，满足reactjs+typescript 组合的项目。" 
```

In the above command, we provide a model and enable the execute mode, the auto-coder will collect the source code from the source directory, and then generate context for the query, and then use the model to generate the result, then put the result into the target file.

### Advanced

> This feature only works with the model from Byzer-LLM.

Translate the markdown file in the project:

```shell

auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat 
```
When you want to translate some files, you must specify the model parameter. And the project_type is a litle bit complex, it's a combination of the following parameters:

- translate: the project type
- 中文: the target language you want to translate to
- .md: the file extension you want to translate
- cn: the new file suffix created with the translated content. for example, if the original file is README.md, the new file will be README-cn.md

So the final project_type is "translate/中文/.md/cn"

If your model is powerful enough, you can use the following command to do the same task:

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --model_max_length 2000 --query "把项目中的markdown文档翻译成中文"
```

The model will extract "translate/中文/.md/cn" from the query and then do the same thing as the previous command.

Note: The model_max_length is used to control the model's generation length, if the model_max_length is not set, the default value is 1024.
You should change the value based on your esitmating on the length of the translation.


### Python Project Only Features

In order to reduce the context length collected by the auto-coder, if you are dealing with a python project, you can use the following command:


```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py-script --query "帮我实现script模块中还没有实现方法"

```

In the above command, we provide a script path and a package name, the script_path is the python file you are working on now, and the package_name 
is you cares about, then the auto-coder only collect the context from the package_name and imported by the script_path file, this will significantly reduce the context length.

When you refer `script module` in `--query`, you means you are talking about script_path file.

After the job is done, you can copy the prompt from the output.txt and paste it to Web of ChatGPT or other AI models.

If you specify the model, the auto-coder will use the model to generate the result, then put the result into the target file.

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/YOUR_PROJECT/xxx.py --package_name xxxx --project_type py-script --model qianwen_chat --execute --query "帮我实现script模块中还没有实现方法" 
```

## TypeScript Project

Just try to set the project_type to ts-script.
