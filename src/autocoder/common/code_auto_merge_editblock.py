import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs, git_utils
from typing import List
import pydantic
import byzerllm
from loguru import logger
import hashlib


class PathAndCode(pydantic.BaseModel):
    path: str
    content: str


class CodeAutoMergeEditBlock:
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
        fence_0: str = "```",
        fence_1: str = "```",
    ):
        self.llm = llm
        self.args = args
        self.fence_0 = fence_0
        self.fence_1 = fence_1

    def parse_whole_text(self, text: str) -> List[PathAndCode]:
        lines = text.split("\n")
        lines_len = len(lines)
        start_marker_count = 0
        inline_start_marker_count = 0
        block = []
        path_and_code_list = []

        def guard(index):
            return index + 1 < lines_len

        def start_marker(line, index):
            return (
                line.startswith(self.fence_0)
                and guard(index)
                and lines[index + 1].startswith("##File:")
            )

        def inline_start_marker(line, index):
            return line.startswith(self.fence_0) and line.strip() != self.fence_0

        def end_marker(line, index):
            return line.startswith(self.fence_1) and line.strip() == self.fence_1

        for index, line in enumerate(lines):
            if start_marker(line, index) and start_marker_count == 0:
                start_marker_count += 1
            elif (
                start_marker(line, index) or inline_start_marker(line, index)
            ) and start_marker_count > 0:
                inline_start_marker_count += 1
                block.append(line)
            elif (
                end_marker(line, index)
                and start_marker_count == 1
                and inline_start_marker_count == 0
            ):
                start_marker_count -= 1
                if block:
                    path = block[0].split(":", 1)[1].strip()
                    content = "\n".join(block[1:])
                    block = []
                    path_and_code_list.append(PathAndCode(path=path, content=content))
            elif end_marker(line, index) and inline_start_marker_count > 0:
                inline_start_marker_count -= 1
                block.append(line)
            elif start_marker_count > 0:
                block.append(line)

        return path_and_code_list

    @byzerllm.prompt()
    def git_require_msg(self, source_dir: str, error: str) -> str:
        """
        auto_merge only works for git repositories.

        Try to use git init in the source directory.

        ```shell
        cd {{ source_dir }}
        git init .
        ```

        Then try to run auto-coder again.
        Error: {{ error }}
        """

    def get_edits(self, content: str):
        edits = self.parse_whole_text(content)
        HEAD = "<<<<<<< SEARCH"
        DIVIDER = "======="
        UPDATED = ">>>>>>> REPLACE"
        result = []
        for edit in edits:
            heads = []
            updates = []
            c = edit.content
            in_head = False
            in_updated = False
            for line in c.splitlines():
                if line.strip() == HEAD:
                    in_head = True
                    continue
                if line.strip() == DIVIDER:
                    in_head = False
                    in_updated = True
                    continue
                if line.strip() == UPDATED:
                    in_head = False
                    in_updated = False
                    continue
                if in_head:
                    heads.append(line)
                if in_updated:
                    updates.append(line)
            result.append((edit.path, "\n".join(heads), "\n".join(updates)))
        return result

    def merge_code(self, content: str, force_skip_git: bool = False):
        file_content = open(self.args.file).read()
        md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
        # get the file name
        file_name = os.path.basename(self.args.file)

        if not force_skip_git:
            try:
                git_utils.commit_changes(
                    self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}"
                )
            except Exception as e:
                logger.error(
                    self.git_require_msg(source_dir=self.args.source_dir, error=str(e))
                )
                return

        codes = self.get_edits(content)
        updated_files = []
        for block in codes:
            file_path = block[0]
            updated_files.append(file_path)
            head = block[1]
            update = block[2]
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    logger.info(f"Upsert path: {file_path}")
                    f.write(update)
                continue
            with open(file_path, "r") as f:
                existing_content = f.read()

            log_message = f"""in:\n {file_path}
    {"replace:" if head else "append:"}\n{head if head else update}
    {"with:" if head else ""}\n{update if head else ""}"""
            logger.info(log_message)

            if head:
                existing_content = existing_content.replace(head, update, 1)
            else:
                existing_content = existing_content + "\n" + update
            logger.info(f"Upsert Result: {existing_content}")
            with open(file_path, "w") as f:
                f.write(existing_content)

        logger.info(f"Merged {len(set(updated_files))} files into the project.")
        if not force_skip_git:
            git_utils.commit_changes(
                self.args.source_dir, f"auto_coder_{file_name}_{md5}"
            )
