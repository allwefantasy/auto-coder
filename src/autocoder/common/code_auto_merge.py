import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs
from typing import List
import pydantic
import byzerllm
from loguru import logger

class PathAndCode(pydantic.BaseModel):
    path: str
    content: str

class CodeAutoMerge:
    def __init__(self, llm:byzerllm.ByzerLLM,args:AutoCoderArgs):
        self.llm = llm
        self.args = args

    def parse_text(self, text: str) -> List[PathAndCode]:
        parsed_blocks = []

        lines = text.split("\n")
        file_path = None
        content_lines = []

        for line in lines:
            if line.startswith("##File:") or line.startswith("## File:"):
                if file_path is not None:
                    parsed_blocks.append(PathAndCode(path=file_path,content="\n".join(content_lines)))
                    content_lines = []

                file_path = line.split(":", 1)[1].strip()
            else:
                content_lines.append(line)

        if file_path is not None:
            parsed_blocks.append(PathAndCode(path=file_path,content="\n".join(content_lines)))

        return parsed_blocks

    def merge_code(self, content: str):
        codes =  code_utils.extract_code(content)
        total = 0
        for (lang,code) in codes:            
            parsed_blocks = self.parse_text(code)

            for block in parsed_blocks:
                file_path = block.path
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "w") as f:
                    logger.info(f"Upsert path: {file_path}")
                    total += 1
                    f.write(block.content)

        logger.info(f"Merged {total} files into the project.")