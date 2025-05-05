<p align="center">
  <picture>    
    <img alt="auto-coder" src="./logo/auto-coder.jpeg" width=55%>
  </picture>
</p>

<h3 align="center">
Auto-Coder (powered by Byzer-LLM)
</h3>

<p align="center">
<a href="https://uelng8wukz.feishu.cn/wiki/QIpkwpQo2iSdkwk9nP6cNSPlnPc"><b>中文</b></a> |

</p>

---

*Latest News* 🔥
- [2025/01] Release Auto-Coder 0.1.208
- [2024/09] Release Auto-Coder 0.1.163
- [2024/08] Release Auto-Coder 0.1.143
- [2024/07] Release Auto-Coder 0.1.115
- [2024/06] Release Auto-Coder 0.1.82
- [2024/05] Release Auto-Coder 0.1.73
- [2024/04] Release Auto-Coder 0.1.46
- [2024/03] Release Auto-Coder 0.1.25
- [2024/03] Release Auto-Coder 0.1.24

---

## Installation

```shell
conda create --name autocoder python=3.10.11
conda activate autocoder
pip install -U auto-coder
auto-coder.chat
```

## Tutorial

0. [Auto-Coder.Chat: 通向智能编程之路](https://uelng8wukz.feishu.cn/wiki/QIpkwpQo2iSdkwk9nP6cNSPlnPc)

# RAG 上下文检索工具

`RagContextTool` 是一个集成了 LongContextRAG 系统的搜索工具，可以从源代码项目中检索与查询相关的上下文文档。该工具提供了 RAG 系统的前两个阶段（文档召回和文档分块）的功能，不包含第三阶段（问答生成）。

## 功能特点

- 🔍 基于语义理解的文档检索：根据用户查询提取关键内容，找出最相关的源代码文件。
- 🧩 智能文档分块与重排序：将检索到的文档进行智能分块和相关性排序。
- 📊 详细的统计信息：提供检索过程的统计数据，包括令牌使用量和文档数量。
- 🛠️ 可配置性：支持设置最大文档数量和相关性阈值等参数。

## 使用方法

在 AgenticEdit 系统中，使用 `rag_context` 工具标签来调用此工具：

```xml
<rag_context>
<query>我想找出所有与文件监控相关的代码</query>
<path>.</path>
<max_docs>10</max_docs>
<relevance_threshold>0.7</relevance_threshold>
</rag_context>
```

### 参数说明

- `query`（必需）：搜索查询，用于寻找相关文档。
- `path`（必需）：要搜索的项目路径，相对于当前工作目录。
- `max_docs`（可选）：返回的最大文档数量，默认为 10。
- `relevance_threshold`（可选）：文档相关性阈值，默认为 0.7。

### 返回结果

工具返回一个包含如下内容的结构化数据：

```json
{
  "results": [
    {
      "index": 1,
      "path": "src/module/file.py",
      "relevance": 0.85,
      "content": "源代码内容...",
      "metadata": { ... }
    },
    ...
  ],
  "stats": {
    "total_docs_found": 25,
    "docs_returned": 10,
    "input_tokens": 5000,
    "generated_tokens": 1000
  }
}
```

## 技术实现

该工具基于 `autocoder.rag.long_context_rag` 中的 `LongContextRAG` 类实现，抽取了其中的文档检索和分块功能，形成了一个独立的工具。

工具遵循了 AgenticEdit 的标准工具开发模式，由两部分组成：
- `RagContextTool`：定义工具接口和参数规范。
- `RagContextToolResolver`：实现工具的核心逻辑。

## 示例应用场景

1. 大型项目代码理解：在分析大型代码库时，可以快速找出相关模块。
2. 文档生成：为特定功能生成文档时，可以找出所有相关代码片段。
3. 缺陷分析：查找与特定问题相关的所有代码文件。
4. 代码重构：在进行代码重构前，找出所有可能受影响的相关代码。


