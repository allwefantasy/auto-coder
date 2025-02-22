from typing import List, Dict, Any, Union
from pathlib import Path
import json
from loguru import logger
from autocoder.rag.token_counter import count_tokens
from autocoder.common import AutoCoderArgs,SourceCode
from byzerllm.utils.client.code_utils import extract_code
from autocoder.index.types import VerifyFileRelevance
import byzerllm
from concurrent.futures import ThreadPoolExecutor, as_completed

from autocoder.common.printer import Printer
from autocoder.common.auto_coder_lang import get_message_with_format

class PruneContext:
    def __init__(self, max_tokens: int, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.max_tokens = max_tokens
        self.args = args
        self.llm = llm
        self.printer = Printer()

    def _delete_overflow_files(self, file_paths: List[str]) -> List[SourceCode]:
        """直接删除超出 token 限制的文件"""
        total_tokens = 0
        selected_files = []
        token_count = 0
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    token_count = count_tokens(content)
                    if total_tokens + token_count <= self.max_tokens:
                        total_tokens += token_count
                        print(f"{file_path} {token_count} {content}")
                        selected_files.append(SourceCode(module_name=file_path,source_code=content,tokens=token_count))
                    else:
                        break
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                selected_files.append(SourceCode(module_name=file_path,source_code=content,tokens=token_count))

        return selected_files

    def _extract_code_snippets(self, file_paths: List[str], conversations: List[Dict[str, str]]) -> List[SourceCode]:
        """抽取关键代码片段策略"""
        token_count = 0
        selected_files = []
        full_file_tokens = int(self.max_tokens * 0.8)

        @byzerllm.prompt()
        def extract_code_snippets(conversations: List[Dict[str, str]], content: str) -> str:
            """
            根据提供的代码文件和对话历史提取相关代码片段。            

            处理示例：
            <examples>
            1.  代码文件：
            <code_file>
                1 def add(a, b):
                2     return a + b
                3 def sub(a, b):
                4     return a - b
            </code_file>
            <conversation_history>
                <user>: 如何实现加法？                
            </conversation_history>

            输出：
            ```json
            [
                {"start_line": 1, "end_line": 2}                
            ]
            ```

            2.  代码文件：
                1 class User:
                2     def __init__(self, name):
                3         self.name = name
                4     def greet(self):
                5         return f"Hello, {self.name}"
            </code_file>
            <conversation_history>
                <user>: 如何创建一个User对象？                
            </conversation_history>

            输出：
            ```json
            [
                {"start_line": 1, "end_line": 3}
            ]
            ```

            3.  代码文件：
            <code_file>
                1 def foo():
                2     pass
            </code_file>
            <conversation_history>
                <user>: 如何实现减法？                
            </conversation_history>

            输出：
            ```json
            []
            ```
            </examples>

            输入:
            1. 代码文件内容:
            <code_file>
            {{ content }}
            </code_file>

            2. 对话历史:
            <conversation_history>
            {% for msg in conversations %}
            <{{ msg.role }}>: {{ msg.content }}
            {% endfor %}
            </conversation_history>

            任务:
            1. 分析最后一个用户问题及其上下文。
            2. 在代码文件中找出与问题相关的一个或多个重要代码段。
            3. 对每个相关代码段，确定其起始行号(start_line)和结束行号(end_line)。
            4. 代码段数量不超过4个。

            输出要求:
            1. 返回一个JSON数组，每个元素包含"start_line"和"end_line"。
            2. start_line和end_line必须是整数，表示代码文件中的行号。
            3. 行号从1开始计数。
            4. 如果没有相关代码段，返回空数组[]。

            输出格式:
            严格的JSON数组，不包含其他文字或解释。

            ```json
            [
                {"start_line": 第一个代码段的起始行号, "end_line": 第一个代码段的结束行号},
                {"start_line": 第二个代码段的起始行号, "end_line": 第二个代码段的结束行号}
            ]
            ```            
            """

        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                    # 完整文件优先
                    tokens = count_tokens(content)
                    if token_count + tokens <= full_file_tokens:
                        selected_files.append(SourceCode(module_name=file_path,source_code=content,tokens=tokens))
                        token_count += tokens
                        continue

                    # 抽取关键片段
                    lines = content.splitlines()
                    new_content = ""

                    ## 将文件内容按行编号
                    for index,line in enumerate(lines):                        
                        new_content += f"{index+1} {line}\n"
                    
                    ## 抽取代码片段
                    extracted = extract_code_snippets.with_llm(self.llm).run(
                        conversations=conversations, 
                        content=new_content
                    )                
                    
                    ## 构建代码片段内容
                    if extracted:
                        json_str = extract_code(extracted)[0][1]
                        snippets = json.loads(json_str)
                        content_snippets = self._build_snippet_content(file_path, content, snippets)

                        snippet_tokens = count_tokens(content_snippets)
                        if token_count + snippet_tokens <= self.max_tokens:
                            selected_files.append(SourceCode(module_name=file_path,source_code=content_snippets,tokens=snippet_tokens))
                            token_count += snippet_tokens
                        else:
                            break
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                continue

        return selected_files

    def _build_snippet_content(self, file_path: str, full_content: str, snippets: List[dict]) -> str:
        """构建包含代码片段的文件内容"""
        lines = full_content.splitlines()
        header = f"Snippets:\n"

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
        strategy: str = "score"        
    ) -> List[SourceCode]:
        """
        处理超出 token 限制的文件
        :param file_paths: 要处理的文件路径列表
        :param conversations: 对话上下文（用于提取策略）
        :param strategy: 处理策略 (delete/extract/score)        
        """
        total_tokens,sources = self._count_tokens(file_paths)
        if total_tokens <= self.max_tokens:
            return sources
        # print(f"total_tokens: {total_tokens} {self.max_tokens}, 进行策略: {strategy}")
        if strategy == "score":            
            return self._score_and_filter_files(file_paths, conversations)
        if strategy == "delete":
            return self._delete_overflow_files(file_paths)
        elif strategy == "extract":
            return self._extract_code_snippets(file_paths, conversations)
        else:
            raise ValueError(f"无效策略: {strategy}. 可选值: delete/extract/score")
    
    def _count_tokens(self, file_paths: List[str]) -> int:
        """计算文件总token数"""
        total_tokens = 0
        sources = []
        for file_path in file_paths:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    sources.append(SourceCode(module_name=file_path,source_code=content,tokens=count_tokens(content)))
                    total_tokens += count_tokens(content)
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                total_tokens += 0
        return total_tokens,sources

    def _score_and_filter_files(self, file_paths: List[str], conversations: List[Dict[str, str]]) -> List[SourceCode]:
        """根据文件相关性评分过滤文件，直到token数大于max_tokens 停止追加"""
        selected_files = []
        total_tokens = 0
        scored_files = []        

        @byzerllm.prompt()
        def verify_file_relevance(file_content: str, conversations: List[Dict[str, str]]) -> str:
            """
            请验证下面的文件内容是否与用户对话相关:

            文件内容:
            {{ file_content }}

            历史对话:
            <conversation_history>
            {% for msg in conversations %}
            <{{ msg.role }}>: {{ msg.content }}
            {% endfor %}
            </conversation_history>

            相关是指，需要依赖这个文件提供上下文，或者需要修改这个文件才能解决用户的问题。
            请给出相应的可能性分数：0-10，并结合用户问题，理由控制在50字以内。格式如下:

            ```json
            {
                "relevant_score": 0-10,
                "reason": "这是相关的原因（不超过10个中文字符）..."
            }
            ```
            """

        def _score_file(file_path: str) -> dict:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    tokens = count_tokens(content)
                    result = verify_file_relevance.with_llm(self.llm).with_return_type(VerifyFileRelevance).run(
                        file_content=content,
                        conversations=conversations
                    )
                    return {
                        "file_path": file_path,
                        "score": result.relevant_score,
                        "tokens": tokens,
                        "content": content
                    }
            except Exception as e:
                logger.error(f"Failed to score file {file_path}: {e}")
                return None

        # 使用线程池并行打分
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(_score_file, file_path) for file_path in file_paths]
            for future in as_completed(futures):
                result = future.result()                
                if result:
                    self.printer.print_str_in_terminal(
                        get_message_with_format(
                            "file_scored_message",
                            file_path=result["file_path"],
                            score=result["score"]
                        )
                    )
                    scored_files.append(result)

        # 第二步：按分数从高到低排序
        scored_files.sort(key=lambda x: x["score"], reverse=True)

        # 第三步：从高分开始过滤，直到token数大于max_tokens 停止追加
        for file_info in scored_files:
            if total_tokens + file_info["tokens"] <= self.max_tokens:
                selected_files.append(SourceCode(
                    module_name=file_info["file_path"],
                    source_code=file_info["content"],
                    tokens=file_info["tokens"]
                ))
                total_tokens += file_info["tokens"]
            else:
                break

        return selected_files

