from typing import List, Dict, Any, Union
from pathlib import Path
import json
from loguru import logger
from autocoder.rag.token_counter import count_tokens
from autocoder.common import AutoCoderArgs
from byzerllm.utils.client.code_utils import extract_code
import byzerllm

class PruneContext:
    def __init__(self, max_tokens: int, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.max_tokens = max_tokens
        self.args = args
        self.llm = llm

    def _delete_overflow_files(self, file_paths: List[str]) -> List[str]:
        """直接删除超出 token 限制的文件"""
        total_tokens = 0
        selected_files = []

        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    token_count = count_tokens(content)
                    if total_tokens + token_count <= self.max_tokens:
                        total_tokens += token_count
                        selected_files.append(file_path)
                    else:
                        break
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                selected_files.append(file_path)

        return selected_files

    def _extract_code_snippets(self, file_paths: List[str], conversations: List[Dict[str, str]]) -> List[str]:
        """抽取关键代码片段策略"""
        token_count = 0
        selected_files = []
        full_file_tokens = int(self.max_tokens * 0.8)

        @byzerllm.prompt()
        def extract_code_snippets(content: str) -> str:
            """
            请分析以下代码文件，提取与当前对话最相关的代码片段：

            对话上下文:
            {{ conversations }}

            代码文件内容:
            {{ content }}

            返回包含关键代码片段的 JSON 数组，格式示例：
            [{
                "start_line": 1,
                "end_line": 10,
                "reason": "包含核心业务逻辑"
            }]
            """

        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                    # 完整文件优先
                    tokens = count_tokens(content)
                    if token_count + tokens <= full_file_tokens:
                        selected_files.append(file_path)
                        token_count += tokens
                        continue

                    # 抽取关键片段
                    extracted = extract_code_snippets.with_llm(self.llm).run(
                        conversations=conversations, 
                        content=content
                    )

                    if extracted:
                        json_str = extract_code(extracted)[0][1]
                        snippets = json.loads(json_str)
                        new_content = self._build_snippet_content(file_path, content, snippets)

                        snippet_tokens = count_tokens(new_content)
                        if token_count + snippet_tokens <= self.max_tokens:
                            selected_files.append(file_path)
                            token_count += snippet_tokens
                        else:
                            break
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")

        return selected_files

    def _build_snippet_content(self, file_path: str, full_content: str, snippets: List[dict]) -> str:
        """构建包含代码片段的文件内容"""
        lines = full_content.split("\n")
        header = f"# File: {file_path}\n# Snippets:\n"

        content = []
        for snippet in snippets:
            start = max(0, snippet["start_line"] - 1)
            end = min(len(lines), snippet["end_line"])
            content.append(f"# Lines {start+1}-{end} ({snippet.get('reason','')})")
            content.extend(lines[start:end])

        return header + "\n".join(content)

    def handle_overflow(
        self,
        file_paths: List[str],
        conversations: List[Dict[str, str]],
        strategy: str = "delete"
    ) -> List[str]:
        """
        处理超出 token 限制的文件
        :param file_paths: 要处理的文件路径列表
        :param conversations: 对话上下文（用于提取策略）
        :param strategy: 处理策略 (delete/extract)
        """
        if strategy == "delete":
            return self._delete_overflow_files(file_paths)
        elif strategy == "extract":
            return self._extract_code_snippets(file_paths, conversations)
        else:
            raise ValueError(f"无效策略: {strategy}. 可选值: delete/extract")
