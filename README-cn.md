
<p align="center">
  <picture>    
    <img alt="Auto-Coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder() Byzer-LLM 提供支持）
</h3>

<p align="center">
| <a href="./README.md"><b>英文</b></a> | <a href="./README-CN.md"><b>中文</b></a> |

</p>

---

*最新动态* 🔥

- [2024/03] 发布 Auto-Coder 0.1.3

---

## 全新安装

您可以使用 Byzer-LLM 提供的脚本设置 nvidia-driver/cuda 环境：

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

在设置好 nvidia-driver/cuda 环境后，可以这样安装 auto_coder：

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

### 基础用法 
> 推荐使用千义通问Max/Qwen-Max SaaS模型
> 您需要通过[Byzer-LLM](https://github.com/allwefantasy/byzer-llm)部署模型

auto-coder 提供两种方式：

1. 根据查询生成上下文，并用于 Web 版 ChatGPT 或其他 AI 模型中。
2. 直接使用 Byzer-LLM 中的模型生成结果。

>> 注意：您应确保所使用的模型支持较长的上下文长度，例如 >32k。 

auto-coder 将从源目录收集源代码，然后基于查询为目标文件生成上下文。

之后，您可以将 `output.txt` 文件中的内容复制并粘贴到 Web 版 ChatGPT 或其他 AI 模型中：

例如：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何让这个系统可以通过 auto-coder 命令执行？" 
```

如果您想使用来自 Byzer-LLM 的模型，则可以使用以下命令：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --execute --query "重新生成一个 is_likely_useful_file 方法，满足reactjs+typescript 组合的项目。" 
```

在上述命令中，我们提供了一个模型并启用了执行模式，auto-coder 将从源目录收集源代码，然后为查询生成上下文，接着使用模型生成结果，并将结果放入目标文件中。

### 进阶用法

> 此功能仅适用于来自 Byzer-LLM 的模型。

翻译项目中的 markdown 文件：

```shell

auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model_max_length 2000 --model qianwen_chat 
```
当您想要翻译某些文件时，必须指定 model 参数。而 project_type 是一个组合参数，包含以下内容：

- translate: 项目类型
- 中文: 您希望翻译成的目标语言
- .md: 您想要翻译的文件扩展名
- cn: 新创建的翻译内容文件后缀。例如，如果原始文件是 README.md，新文件将是 README-cn.md

所以最终的 project_type 为 "translate/中文/.md/cn"

如果您的模型足够强大，您可以使用以下命令完成相同任务：

```shell
auto-coder --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --model_max_length 2000 --query "把项目中的markdown文档翻译成中文"
```

模型将从查询中提取 "translate/中文/.md/cn" 并执行与上一命令相同的任务。

注意：model_max_length 用于控制模型的生成长度，如果不设置该值，默认值为 1024。
您应根据对翻译长度的预估来调整这个值。

### Python 项目特有功能

为了减少 auto-coder 收集的上下文长度，如果您正在处理 Python 项目，可以使用以下命令：


```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py-script --query "帮我实现script模块中还没有实现的方法"

```

在上述命令中，我们提供了 script 路径和包名称，其中 script_path 是您当前正在处理的 Python 文件，package_name 是您关心的包名，auto-coder 只会从此 package_name 和被 script_path 文件导入的部分收集上下文，这将显著减少上下文长度。

当您在 `--query` 中提到 `script 模块` 时，指的是 script_path 文件。

任务完成后，您可以将 output.txt 中的提示复制并粘贴到 Web 版 ChatGPT 或其他 AI 模型中。

如果您指定了模型，auto-coder 将使用该模型生成结果，然后将结果放入目标文件中。

```shell
auto-coder --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/YOUR_PROJECT/xxx.py --package_name xxxx --project_type py-script --model qianwen_chat --execute --query "帮我实现script模块中还没有实现的方法" 
```

## TypeScript 项目

只需尝试将 project_type 设置为 ts-script。