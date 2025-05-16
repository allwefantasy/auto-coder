# LongContextRAG 工具设计文档

## 1. 背景与目标

LongContextRAG 是 AutoCoder 中的一个重要组件，用于处理大型代码库的检索增强生成。目前，LongContextRAG 的工作流程分为三个主要阶段：

1. **文档检索阶段**：根据用户查询检索相关文档
2. **文档分块阶段**：对检索到的文档进行分块和重排序
3. **答案生成阶段**：基于处理后的上下文生成回答

本设计文档旨在将 LongContextRAG 中的关键功能抽象为两个独立工具，以便在 BaseAgent 框架中使用：

- **SearchTool**：获取第一阶段处理结果中涉及的文件列表
- **RecallTool**：输出第二阶段的相关文档内容

## 2. 工具设计

### 2.1 SearchTool

#### 2.1.1 功能描述

SearchTool 将封装 LongContextRAG 的第一阶段功能，根据用户查询检索相关文档，并返回文件列表及其相关性分数。

#### 2.1.2 工具定义

```python
import os
from typing import Dict, Any, List, Optional

from autocoder.agent.base_agentic.types import BaseTool, ToolResult
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.common import AutoCoderArgs
from autocoder.rag.long_context_rag import LongContextRAG, RecallStat, ChunkStat, AnswerStat, RAGStat

class SearchTool(BaseTool):
    """搜索工具，用于获取与查询相关的文件列表"""
    query: str  # 用户查询
    max_files: Optional[int] = 10  # 最大返回文件数量
```

#### 2.1.3 解析器定义

```python
class SearchToolResolver(BaseToolResolver):
    """搜索工具解析器，实现搜索逻辑"""
    def __init__(self, agent, tool, args):
        super().__init__(agent, tool, args)
        self.tool: SearchTool = tool
        
    def resolve(self) -> ToolResult:
        """实现搜索工具的解析逻辑"""
        try:
            # 获取参数
            query = self.tool.query
            path = os.getcwd()
            max_files = self.tool.max_files
            
            # 初始化 LongContextRAG
            from autocoder.rag.long_context_rag import LongContextRAG
            from autocoder.common import AutoCoderArgs
            
            # 获取 LLM 实例
            llm = self.agent.llm
            
            # 创建 AutoCoderArgs
            args =  self.args
            
            # 初始化 LongContextRAG
            rag = LongContextRAG(llm=llm, args=args, path=self.args.doc_dir)
            
            # 构建对话历史
            conversations = [
                {"role": "user", "content": query}
            ]
            
            # 创建 RAGStat 对象
            from autocoder.rag.long_context_rag import RecallStat, ChunkStat, AnswerStat, RAGStat
            rag_stat = RAGStat(
                recall_stat=RecallStat(total_input_tokens=0, total_generated_tokens=0),
                chunk_stat=ChunkStat(total_input_tokens=0, total_generated_tokens=0),
                answer_stat=AnswerStat(total_input_tokens=0, total_generated_tokens=0)
            )
            
            # 调用文档检索处理
            generator = rag._process_document_retrieval(conversations, query, rag_stat)
            
            # 获取最终结果
            result = None
            for item in generator:
                if isinstance(item, dict) and "result" in item:
                    result = item["result"]
            
            if not result:
                return ToolResult(
                    success=False,
                    message="未找到相关文档",
                    content=[]
                )
            
            # 格式化结果
            file_list = []
            for doc in result:
                file_list.append({
                    "path": doc.path,
                    "relevance": doc.relevance.score if hasattr(doc.relevance, "score") else 0,
                    "is_relevant": doc.relevance.is_relevant if hasattr(doc.relevance, "is_relevant") else False
                })
            
            # 按相关性排序
            file_list.sort(key=lambda x: x["relevance"], reverse=True)
            
            # 限制返回数量
            file_list = file_list[:max_files]
            
            return ToolResult(
                success=True,
                message=f"成功检索到 {len(file_list)} 个相关文件",
                content=file_list
            )
            
        except Exception as e:
            import traceback
            return ToolResult(
                success=False,
                message=f"搜索工具执行失败: {str(e)}",
                content=traceback.format_exc()
            )
```

### 2.2 RecallTool

#### 2.2.1 功能描述

RecallTool 将封装 LongContextRAG 的第二阶段功能，对检索到的文档进行分块和重排序，并返回最终的相关文档内容。

#### 2.2.2 工具定义

```python
import os
import traceback
from typing import Dict, Any, List, Optional

from autocoder.agent.base_agentic.types import BaseTool, ToolResult
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.common import AutoCoderArgs
from autocoder.rag.long_context_rag import LongContextRAG, RecallStat, ChunkStat, AnswerStat, RAGStat
from autocoder.rag.relevant_utils import RelevantDoc, DocRelevance, DocFilterResult

class RecallTool(BaseTool):
    """召回工具，用于获取与查询相关的文档内容"""
    query: str  # 用户查询
    max_tokens: Optional[int] = 4000  # 最大返回令牌数
    file_paths: Optional[List[str]] = None  # 指定要处理的文件路径列表，如果为空则自动搜索
```

#### 2.2.3 解析器定义

```python
class RecallToolResolver(BaseToolResolver):
    """召回工具解析器，实现召回逻辑"""
    def __init__(self, agent, tool, args):
        super().__init__(agent, tool, args)
        self.tool: RecallTool = tool
        
    def resolve(self) -> ToolResult:
        """实现召回工具的解析逻辑"""
        try:
            # 获取参数
            query = self.tool.query
            path = os.getcwd()
            max_tokens = self.tool.max_tokens
            file_paths = self.tool.file_paths
            
            # 初始化 LongContextRAG
            from autocoder.rag.long_context_rag import LongContextRAG
            from autocoder.common import AutoCoderArgs
            from autocoder.rag.relevant_utils import DocFilterResult
            
            # 获取 LLM 实例
            llm = self.agent.llm
            
            # 创建 AutoCoderArgs
            args =  self.args
            
            # 初始化 LongContextRAG
            rag = LongContextRAG(llm=llm, args=args, path=self.args.doc_dir)
            
            # 构建对话历史
            conversations = [
                {"role": "user", "content": query}
            ]
            
            # 创建 RAGStat 对象
            from autocoder.rag.long_context_rag import RecallStat, ChunkStat, AnswerStat, RAGStat
            rag_stat = RAGStat(
                recall_stat=RecallStat(total_input_tokens=0, total_generated_tokens=0),
                chunk_stat=ChunkStat(total_input_tokens=0, total_generated_tokens=0),
                answer_stat=AnswerStat(total_input_tokens=0, total_generated_tokens=0)
            )
            
            # 如果提供了文件路径，则直接使用；否则，执行搜索
            if file_paths:
                from autocoder.rag.relevant_utils import RelevantDoc, DocRelevance
                
                # 创建 RelevantDoc 对象
                relevant_docs = []
                for file_path in file_paths:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    doc = RelevantDoc(
                        path=file_path,
                        content=content,
                        relevance=DocRelevance(score=5, is_relevant=True)  # 默认相关性
                    )
                    relevant_docs.append(doc)
            else:
                # 调用文档检索处理
                generator = rag._process_document_retrieval(conversations, query, rag_stat)
                
                # 获取检索结果
                relevant_docs = None
                for item in generator:
                    if isinstance(item, dict) and "result" in item:
                        relevant_docs = item["result"]
                
                if not relevant_docs:
                    return ToolResult(
                        success=False,
                        message="未找到相关文档",
                        content=[]
                    )
            
            # 调用文档分块处理
            generator = rag._process_document_chunking(relevant_docs, conversations, rag_stat, 0)
            
            # 获取分块结果
            final_relevant_docs = None
            for item in generator:
                if isinstance(item, dict) and "result" in item:
                    final_relevant_docs = item["result"]
            
            if not final_relevant_docs:
                return ToolResult(
                    success=False,
                    message="文档分块处理失败",
                    content=[]
                )
            
            # 格式化结果
            doc_contents = []
            for doc in final_relevant_docs:
                doc_contents.append({
                    "path": doc.path,
                    "content": doc.content,
                    "relevance": doc.relevance.score if hasattr(doc.relevance, "score") else 0
                })
            
            return ToolResult(
                success=True,
                message=f"成功召回 {len(doc_contents)} 个相关文档片段",
                content=doc_contents
            )
            
        except Exception as e:
            import traceback
            return ToolResult(
                success=False,
                message=f"召回工具执行失败: {str(e)}",
                content=traceback.format_exc()
            )
```

## 3. 工具注册

### 3.1 SearchTool 注册

```python
def register_search_tool():
    """注册搜索工具"""
    # 准备工具描述
    description = ToolDescription(
        description="搜索与查询相关的文件",
        parameters="query: 搜索查询\nmax_files: 最大返回文件数量（可选，默认为10）",
        usage="用于根据查询找到相关的代码文件"
    )
    
    # 准备工具示例
    example = ToolExample(
        title="搜索工具使用示例",
        body="""<search>
<query>如何实现文件监控功能</query>
<max_files>5</max_files>
</search>"""
    )
    
    # 注册工具
    ToolRegistry.register_tool(
        tool_tag="search",  # XML标签名
        tool_cls=SearchTool,  # 工具类
        resolver_cls=SearchToolResolver,  # 解析器类
        description=description,  # 工具描述
        example=example,  # 工具示例
        use_guideline="此工具用于根据用户查询搜索相关代码文件，返回文件路径及其相关性分数。适用于需要快速找到与特定功能或概念相关的代码文件的场景。"  # 使用指南
    )
```

### 3.2 RecallTool 注册

```python
def register_recall_tool():
    """注册召回工具"""
    # 准备工具描述
    description = ToolDescription(
        description="召回与查询相关的文档内容",
        parameters="query: 搜索查询\nmax_tokens: 最大返回令牌数（可选，默认为4000）\nfile_paths: 指定要处理的文件路径列表（可选）",
        usage="用于根据查询获取相关文档的内容片段"
    )
    
    # 准备工具示例
    example = ToolExample(
        title="召回工具使用示例",
        body="""<recall>
<query>如何实现文件监控功能</query>
<max_tokens>4000</max_tokens>
</recall>"""
    )
    
    # 注册工具
    ToolRegistry.register_tool(
        tool_tag="recall",  # XML标签名
        tool_cls=RecallTool,  # 工具类
        resolver_cls=RecallToolResolver,  # 解析器类
        description=description,  # 工具描述
        example=example,  # 工具示例
        use_guideline="此工具用于根据用户查询召回相关文档内容，返回经过分块和重排序的文档片段。适用于需要深入了解特定功能实现细节的场景。"  # 使用指南
    )
```

## 4. 工具使用示例

### 4.1 SearchTool 使用示例

```python
# 在 Agent 中使用 SearchTool
agent.run_with_events(AgentRequest(user_input="""
请使用搜索工具查找与文件监控相关的代码文件：

<search>
<query>文件监控系统实现</query>
<max_files>5</max_files>
</search>
"""))
```

### 4.2 RecallTool 使用示例

```python
# 在 Agent 中使用 RecallTool
agent.run_with_events(AgentRequest(user_input="""
请使用召回工具获取与文件监控相关的代码内容：

<recall>
<query>文件监控系统实现</query>
<max_tokens>4000</max_tokens>
</recall>
"""))
```

## 5. 实现计划

1. 在 `src/autocoder/rag/tools` 目录下创建以下文件：
   - `__init__.py`：包初始化文件
   - `search_tool.py`：实现 SearchTool 和 SearchToolResolver
   - `recall_tool.py`：实现 RecallTool 和 RecallToolResolver


## 6. 总结

本设计文档详细描述了如何将 LongContextRAG 的核心功能抽象为两个独立工具：SearchTool 和 RecallTool。这些工具将使 BaseAgent 能够更灵活地利用 LongContextRAG 的能力，实现更精细的代码检索和内容召回功能。

通过这种模块化设计，我们可以更好地复用 LongContextRAG 的功能，同时提高系统的可维护性和可扩展性。
