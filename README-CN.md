<p align="center">
  <picture>    
    <img alt="auto-coder" src="./logo/auto-coder.jpeg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder (由Byzer-LLM提供支持)
</h3>

<p align="center">
| <a href="./docs/en"><b>英文</b></a> | <a href="./docs/zh"><b>中文</b></a> |

</p>

---

*最新消息* 🔥

- [2024/05] 发布 Auto-Coder 0.1.73
- [2024/04] 发布 Auto-Coder 0.1.46
- [2024/03] 发布 Auto-Coder 0.1.25
- [2024/03] 发布 Auto-Coder 0.1.24

---

Auto-Coder 是一个基于YAML配置的命令行工具，可以根据您的需求自动开发现有项目。

使用Auto-Coder编程体验类似于从马车驾驶员升级为汽车驾驶员。您需要耐心学习如何使用自动编码器作为专业技能和工具。通常需要几周甚至几个月的时间，并且需要改变许多驾驶习惯，才能真正实现显著的（可能是3-5倍）生产率提升。

您的开发新方式是：

1. 编写一个YAML文件来描述您的需求，Auto-Coder将生成代码并将代码合并到您的项目中。
2. 检查Auto-Coder的提交，并在vscode或其他IDE中审查代码。
3. 如果提交是正确的，您可能仍需要使用github copilot或其他工具手动修改代码。
4. 如果提交代码不满足你需求，您需要撤销提交并修改YAML文件，以使Auto-Coder贴近正确的代码。
5. 重复上述步骤，直到您对Auto-Coder生成的代码满意。

## 安装

```shell
conda create --name autocoder python=3.10.11
conda activate autocoder
pip install -U auto-coder
## 如果您想使用私有/开源模型，请取消注释此行。
# pip install -U vllm
ray start --head
```

## 教程

1. [设置Auto-Coder](./docs/en/000-AutoCoder_Prepare_Journey.md)
2. [AutoCoder_准备旅程](./docs/zh/000-AutoCoder_准备旅程.md)


## 示例项目https://github.com/allwefantasy/auto-coder.example