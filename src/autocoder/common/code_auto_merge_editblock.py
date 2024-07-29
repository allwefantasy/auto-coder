import os
from byzerllm.utils.client import code_utils
from autocoder.common import AutoCoderArgs, git_utils
from autocoder.common.text import TextSimilarity
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
from typing import List
import pydantic
import byzerllm
from loguru import logger
import hashlib
import subprocess
import tempfile
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
import json


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

    def run_pylint(self, code: str) -> tuple[bool, str]:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = temp_file.name

        try:
            result = subprocess.run(
                [
                    "pylint",
                    "--disable=all",
                    "--enable=E0001,W0311,W0312",
                    temp_file_path,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            os.unlink(temp_file_path)
            if result.returncode != 0:
                error_message = result.stdout.strip() or result.stderr.strip()
                logger.warning(f"Pylint check failed: {error_message}")
                return False, error_message
            return True, ""
        except subprocess.CalledProcessError as e:
            error_message = f"Error running pylint: {str(e)}"
            logger.error(error_message)
            os.unlink(temp_file_path)
            return False, error_message

    def parse_whole_text(self, text: str) -> List[PathAndCode]:
        HEAD = "<<<<<<< SEARCH"
        DIVIDER = "======="
        UPDATED = ">>>>>>> REPLACE"
        lines = text.split("\n")
        lines_len = len(lines)
        start_marker_count = 0
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

        def end_marker(line, index):
            return line.startswith(self.fence_1) and UPDATED in lines[index - 1]

        for index, line in enumerate(lines):
            if start_marker(line, index) and start_marker_count == 0:
                start_marker_count += 1
            elif end_marker(line, index) and start_marker_count == 1:
                start_marker_count -= 1
                if block:
                    path = block[0].split(":", 1)[1].strip()
                    content = "\n".join(block[1:])
                    block = []
                    path_and_code_list.append(PathAndCode(path=path, content=content))
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
        file_name = os.path.basename(self.args.file)

        codes = self.get_edits(content)
        changes_to_make = []
        changes_made = False
        unmerged_blocks = []

        # First, check if there are any changes to be made
        file_content_mapping = {}
        for block in codes:
            file_path, head, update = block
            if not os.path.exists(file_path):
                changes_to_make.append((file_path, None, update))
                file_content_mapping[file_path] = update
                changes_made = True
            else:
                if file_path not in file_content_mapping:
                    with open(file_path, "r") as f:
                        temp = f.read()
                        file_content_mapping[file_path] = temp
                existing_content = file_content_mapping[file_path]
                new_content = (
                    existing_content.replace(head, update, 1)
                    if head
                    else existing_content + "\n" + update
                )
                if new_content != existing_content:
                    changes_to_make.append((file_path, existing_content, new_content))
                    file_content_mapping[file_path] = new_content
                    changes_made = True
                else:
                    ## If the SEARCH BLOCK is not found exactly, then try to use
                    ## the similarity ratio to find the best matching block
                    similarity, best_window = TextSimilarity(
                        head, existing_content
                    ).get_best_matching_window()
                    if similarity > self.args.editblock_similarity:
                        new_content = existing_content.replace(best_window, update, 1)
                        if new_content != existing_content:
                            changes_to_make.append(
                                (file_path, existing_content, new_content)
                            )
                            file_content_mapping[file_path] = new_content
                            changes_made = True
                    else:
                        unmerged_blocks.append((file_path, head, update, similarity))

        if unmerged_blocks:
            s = f"Found {len(unmerged_blocks)} unmerged blocks, the changes will not be applied. Please review them manually then try again."
            logger.warning(s)
            self._print_unmerged_blocks(unmerged_blocks)
            return

        ## lint check
        for file_path, new_content in file_content_mapping.items():
            if file_path.endswith(".py"):
                pylint_passed, error_message = self.run_pylint(new_content)
                if not pylint_passed:
                    logger.warning(
                        f"Pylint check failed for {file_path}. Changes not applied. Error: {error_message}"
                    )

        if changes_made and not force_skip_git:
            try:
                git_utils.commit_changes(
                    self.args.source_dir, f"auto_coder_pre_{file_name}_{md5}"
                )
            except Exception as e:
                logger.error(
                    self.git_require_msg(source_dir=self.args.source_dir, error=str(e))
                )
                return
        # Now, apply the changes
        for file_path, new_content in file_content_mapping.items():
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write(new_content)

        if self.args.request_id:
            # collect modified files
            event_data = []
            for file_path, old_block, new_block in changes_to_make:
                event_data.append(
                    {
                        "file_path": file_path,
                        "old_block": old_block,
                        "new_block": new_block,
                    }
                )

            _ = queue_communicate.send_event_no_wait(
                request_id=self.args.request_id,
                event=CommunicateEvent(
                    event_type=CommunicateEventType.CODE_MERGE_RESULT.value,
                    data=json.dumps(event_data, ensure_ascii=False),
                ),
            )

        if changes_made:
            if not force_skip_git:
                try:
                    commit_result = git_utils.commit_changes(
                        self.args.source_dir, f"auto_coder_{file_name}_{md5}"
                    )
                    git_utils.print_commit_info(commit_result=commit_result)
                except Exception as e:
                    logger.error(
                        self.git_require_msg(
                            source_dir=self.args.source_dir, error=str(e)
                        )
                    )
            logger.info(
                f"Merged changes in {len(file_content_mapping.keys())} files {len(changes_to_make)}/{len(codes)} blocks."
            )
        else:
            logger.warning("No changes were made to any files.")

    def _print_unmerged_blocks(self, unmerged_blocks: List[tuple]):
        console = Console()
        console.print("\n[bold red]Unmerged Blocks:[/bold red]")
        for file_path, head, update, similarity in unmerged_blocks:
            console.print(f"\n[bold blue]File:[/bold blue] {file_path}")
            console.print(f"\n[bold green]Search Block({similarity}):[/bold green]")
            syntax = Syntax(head, "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, expand=False))
            console.print("\n[bold yellow]Replace Block:[/bold yellow]")
            syntax = Syntax(update, "python", theme="monokai", line_numbers=True)
            console.print(Panel(syntax, expand=False))
        console.print(
            f"\n[bold red]Total unmerged blocks: {len(unmerged_blocks)}[/bold red]"
        )
