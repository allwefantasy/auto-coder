
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

After the nvidia-driver/cuda environment is set up, you can install auto_coder like this:

```shell
pip install -U auto_coder
```

## Existing Installation


```shell
# or https://gitcode.com/allwefantasy11/byzer-copilot.git
git clone https://github.com/allwefantasy/byzer-copilot.git
pip install -r requirements.txt
pip install -U vllm
pip install -U byzerllm
pip install -U auto_coder
```

## Usage 

### Command Line

```shell
python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "如何让这个系统可以通过 auto_coder 命令执行？" 
```

```shell
python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "重新生成一个 is_likely_useful_file 方法，满足reactjs+typescript 组合的项目。" 


python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --project_type "translate/中文/.md/cn" --model sparkdesk_chat --execute
```

```shell
python auto_coder.py --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --script_path /home/winubuntu/projects/ByzerRawCopilot/xxx --package_name byzer_copilot --project_type py_spy-script 
```

python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat  --query "优化 src 目录外的auto_coder.py, 生成一个新的pydantic model, 提供一个方法自动将 argparse 参数转换为 pydantic model。"