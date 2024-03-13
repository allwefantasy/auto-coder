
<p align="center">
  <picture>    
    <img alt="auto-coder" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto Coder
</h3>

<p align="center">
| <a href="./README.md"><b>English</b></a> | <a href="./README-CN.md"><b>中文</b></a> |

</p>

---

*Latest News* 🔥

- [2024/03] Release Auto-Coder 0.1.0

---


## Brand new Installation

You can use the script provided by Byzer-LLM to setup the nvidia-driver/cuda environment:

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

After the nvidia-driver/cuda environment is set up, you can install byzer-evaluation like this:

```shell
pip install -U byzercopilot
```

## Existing Installation


```shell
# or https://gitcode.com/allwefantasy11/byzer-copilot.git
git clone https://github.com/allwefantasy/byzer-copilot.git
pip install -r requirements.txt
pip install -U vllm
pip install -U byzerllm
pip install -U byzer-autocoder
```

## Usage 

### Command Line

```shell
python auto-coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "请仿照PyProject 实现一个 TypeScriptProject" 
```

```shell
python auto-coder.py --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py_spy-script 
```