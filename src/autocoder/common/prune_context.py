from typing import List, Dict, Any
from autocoder.index.types import IndexItem
from loguru import logger
from autocoder.rag.token_counter import count_tokens

class PruneContext:
    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens

    def _delete_overflow_files(self, validated_file_numbers: List[int], index_items: List[IndexItem]):
        # 拼接所有文件内容并计算总token数
        total_tokens = 0
        selected_files = []
        for file_number in validated_file_numbers:
            file_path = get_file_path(index_items[file_number].module_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    token_count = count_tokens(content)
                    if total_tokens + token_count <= self.max_tokens:
                        total_tokens += token_count
                        selected_files.append(file_number)
                    else:
                        # 如果加上当前文件后超过max_tokens，则停止添加
                        break
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                selected_files.append(file_number)
                continue 

        return selected_files

    def _extract_code_snippets_from_overflow_files(self, validated_file_numbers: List[int], index_items: List[IndexItem], conversations: List[Dict[str, str]]):
        token_count = 0        
        selected_files = []
        selected_file_contents = []
        full_file_tokens = int(self.max_tokens * 0.8)
        for file_number in validated_file_numbers:
            file_path = get_file_path(index_items[file_number].module_name)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tokens = count_tokens(content)
            if token_count + tokens <= full_file_tokens:
                selected_files.append(file_number)
                selected_file_contents.append(content)
                token_count += tokens
            else:
                # 对超出部分抽取代码片段
                try:
                    extracted_info = (
                        self.extract_code_snippets_from_files.options(
                            {"llm_config": {"max_length": 100}}
                        )
                        .with_llm(self.index_manager.index_filter_llm)
                        .run(conversations, [content])
                    )
                    json_str = extract_code(extracted_info)[0][1]
                    json_objs = json.loads(json_str)

                    new_content = ""

                    if json_objs:                        
                        for json_obj in json_objs:
                            start_line = json_obj["start_line"] - 1
                            end_line = json_obj["end_line"]
                            chunk = "\n".join(content.split("\n")[start_line:end_line])
                            new_content += chunk + "\n"

                        token_count += count_tokens(new_content)
                        if token_count >= self.max_tokens:
                            break
                        else:
                            selected_files.append(file_number)
                            selected_file_contents.append(new_content)
                except Exception as e:
                    logger.error(f"Failed to extract code snippets from {file_path}: {e}")
        return selected_files

    def handle_overflow_files(
        self,
        index_items: List[IndexItem],
        conversations: List[Dict[str, str]],
        strategy: str = "delete",
    ) -> List[IndexItem]:
        """
        处理超出token限制的文件，提供两种策略：
        1. delete: 直接删除后面的文件
        2. extract: 对超出部分的文件抽取相关代码片段

        Args:
            index_items: 需要处理的文件列表
            conversations: 对话历史
            strategy: 处理策略，可选值为 "delete" 或 "extract"

        Returns:
            处理后的文件列表
        """
        if strategy == "delete":
            # 简单删除后面的文件
            return self._delete_overflow_files(index_items)
        elif strategy == "extract":
            # 对超出部分的文件抽取代码片段
            return self._extract_code_snippets_from_overflow_files(index_items, conversations)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

def get_file_path(file_path):
    if file_path.startswith("##"):
        return file_path.strip()[2:]
    return file_path
