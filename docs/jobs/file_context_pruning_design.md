# 大文件剪枝设计方案

## 1. 背景

在处理大型代码文件时，经常会遇到文件内容超过 token 限制的情况。目前系统中有两个相关的组件：
- `context_pruner.py`: 提供了文件内容剪枝的核心功能
- `read_file_tool_resolver.py`: 负责文件读取的基础功能

我们需要将这两个组件结合，实现对大文件的智能剪枝功能。

## 2. 设计目标

1. 对超过 30k token 的文件进行自动剪枝
2. 保持文件内容的语义完整性
3. 支持多种剪枝策略
4. 与现有的 shadow 系统兼容

## 3. 具体设计


### 3.2 修改 ReadFileToolResolver

在 `ReadFileToolResolver` 中添加剪枝功能：

```python
class ReadFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ReadFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ReadFileTool = tool
        self.shadow_manager = self.agent.shadow_manager if self.agent else None
        self.context_pruner = PruneContext(
            max_tokens=self.args.context_prune_safe_zone_tokens,
            args=self.args,
            llm=self.agent.context_prune_llm
        )

    def _prune_file_content(self, content: str, file_path: str) -> str:
        """对文件内容进行剪枝处理"""
        if not self.args.enable_file_pruning:
            return content

        # 计算 token 数量
        tokens = count_tokens(content)
        if tokens <= self.args.file_pruning_threshold:
            return content

        # 创建 SourceCode 对象
        source_code = SourceCode(
            module_name=file_path,
            source_code=content,
            tokens=tokens
        )

        # 使用 context_pruner 进行剪枝
        pruned_sources = self.context_pruner.handle_overflow(
            file_sources=[source_code],
            conversations=self.agent.current_conversations if self.agent else [],
            strategy=self.args.context_prune_strategy
        )

        if not pruned_sources:
            return content

        return pruned_sources[0].source_code

    def _read_file_content(self, file_path_to_read: str) -> str:
        """读取文件内容并进行剪枝处理"""
        content = ""
        ext = os.path.splitext(file_path_to_read)[1].lower()

        # 原有的文件读取逻辑
        if ext == '.pdf':
            logger.info(f"Extracting text from PDF: {file_path_to_read}")
            content = extract_text_from_pdf(file_path_to_read)
        elif ext == '.docx':
            logger.info(f"Extracting text from DOCX: {file_path_to_read}")
            content = extract_text_from_docx(file_path_to_read)
        elif ext in ('.pptx', '.ppt'):
            logger.info(f"Extracting text from PPT/PPTX: {file_path_to_read}")
            slide_texts = []
            for slide_identifier, slide_text_content in extract_text_from_ppt(file_path_to_read):
                slide_texts.append(f"--- Slide {slide_identifier} ---\n{slide_text_content}")
            content = "\n\n".join(slide_texts) if slide_texts else ""
        else:
            logger.info(f"Reading plain text file: {file_path_to_read}")
            with open(file_path_to_read, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

        # 对内容进行剪枝处理
        return self._prune_file_content(content, file_path_to_read)
```

### 3.3 剪枝策略说明

1. **extract 策略**（默认）：
   - 使用滑动窗口分割大文件
   - 对每个窗口使用 LLM 提取相关代码片段
   - 合并重叠的代码片段
   - 保留最相关的代码部分

2. **score 策略**：
   - 使用 LLM 对文件内容进行相关性评分
   - 保留评分最高的部分
   - 适合需要保持文件整体性的场景

3. **delete 策略**：
   - 直接删除超出 token 限制的部分
   - 适合对文件内容要求不高的场景

