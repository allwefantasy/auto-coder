<p align="center">
  <picture>    
    <img alt="auto-coder" src="./logo/auto-coder.jpeg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder (由Byzer-LLM提供支持)
</h3>

<p align="center">
| <a href="./docs/en"><b>English</b></a> | <a href="./docs/zh"><b>中文</b></a> |

</p>

---

*最新消息* 🔥

- [2024/05] 发布 Auto-Coder 0.1.68
- [2024/04] 发布 Auto-Coder 0.1.46
- [2024/03] 发布 Auto-Coder 0.1.25
- [2024/03] 发布 Auto-Coder 0.1.24

---

Auto-Coder 是一个基于YAML配置的命令行工具，可以根据您的需求自动修改项目。

Auto-Coder旨在帮助开发人员更高效地开发现有项目。

## 安装

```shell
conda create --name autocoder python=3.10.11
conda activate autocoder
pip install -U auto-coder
## 如果您想使用私有/开源模型，请取消注释此行。
# pip install -U vllm
ray start --head
```

## 示例项目

https://github.com/allwefantasy/auto-coder.example