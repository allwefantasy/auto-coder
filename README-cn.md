<p align="center">
  <picture>    
    <img alt="自动编码器" src="https://github.com/allwefantasy/byzer-llm/blob/master/docs/source/assets/logos/logo.jpg" width=55%>
  </picture>
</p>

<h3 align="center">
自动编码器
</h3>

<p align="center">
| <a href="./README.md"><b>英文</b></a> | <a href="./README-CN.md"><b>中文</b></a> |
</p>

---

*最新动态* 🔥

- [2024/03] 发布 Auto-Coder 0.1.0

---

##全新安装

您可以使用 Byzer-LLM 提供的脚本来设置 nvidia-driver/cuda 环境：

1. [CentOS 8 / Ubuntu 20.04 / Ubuntu 22.04](https://docs.byzer.org/#/byzer-lang/zh-cn/byzer-llm/deploy)

在 nvidia-driver/cuda 环境设置完成后，您可以按照以下方式安装 auto_coder：

```shell
pip install -U auto_coder
```

##已有安装

```shell
# 或者 https://gitcode.com/allwefantasy11/byzer-copilot.git
git clone https://github.com/allwefantasy/byzer-copilot.git
pip install -r requirements.txt
pip install -U vllm
pip install -U byzerllm
pip install -U auto_coder
```

## 使用方法 
###命令行

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

```python
python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat  --query "优化 src 目录外的auto_coder.py, 生成一个新的pydantic model, 提供一个方法自动将 argparse 参数转换为 pydantic model。"

python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --model qianwen_chat --project_type translate --query "把项目中的markdown文档翻译成中文"

python auto_coder.py --source_dir /home/winubuntu/projects/ByzerRawCopilot --target_file /home/winubuntu/projects/ByzerRawCopilot/output.txt --query "对Dispacher类进行重构，将所有的Action组成一个调用链，然后依次调用，检查调用结果，如果False表示继续往下调用，否则停止调用" 
```