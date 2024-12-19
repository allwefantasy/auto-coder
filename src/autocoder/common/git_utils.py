import os
from git import Repo, GitCommandError
from loguru import logger
from typing import List, Optional
from pydantic import BaseModel
import byzerllm
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text


class CommitResult(BaseModel):
    success: bool
    commit_message: Optional[str] = None
    commit_hash: Optional[str] = None
    changed_files: Optional[List[str]] = None
    diffs: Optional[dict] = None
    error_message: Optional[str] = None


def init(repo_path: str) -> bool:
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)

    if os.path.exists(os.path.join(repo_path, ".git")):
        logger.warning(
            f"The directory {repo_path} is already a Git repository. Skipping initialization."
        )
        return False
    try:
        repo = Repo.init(repo_path)
        logger.info(f"Initialized new Git repository at {repo_path}")
        return True
    except GitCommandError as e:
        logger.error(f"Error during Git initialization: {e}")
        return False


def get_repo(repo_path: str) -> Repo:
    repo = Repo(repo_path)
    return repo


def commit_changes(repo_path: str, message: str) -> CommitResult:
    repo = get_repo(repo_path)
    if repo is None:
        return CommitResult(
            success=False, error_message="Repository is not initialized."
        )

    try:
        repo.git.add(all=True)
        if repo.is_dirty():
            commit = repo.index.commit(message)
            result = CommitResult(
                success=True,
                commit_message=message,
                commit_hash=commit.hexsha,
                changed_files=[],
                diffs={},
            )

            if commit.parents:
                changed_files = repo.git.diff(
                    commit.parents[0].hexsha, commit.hexsha, name_only=True
                ).split("\n")
                result.changed_files = [file for file in changed_files if file.strip()]

                for file in result.changed_files:
                    diff = repo.git.diff(
                        commit.parents[0].hexsha, commit.hexsha, "--", file
                    )
                    result.diffs[file] = diff
            else:
                result.error_message = (
                    "This is the initial commit, no parent to compare against."
                )

            return result
        else:
            return CommitResult(success=False, error_message="No changes to commit.")
    except GitCommandError as e:
        return CommitResult(success=False, error_message=str(e))


def get_current_branch(repo_path: str) -> str:
    repo = get_repo(repo_path)
    if repo is None:
        return ""
    branch = repo.active_branch.name
    return branch


def revert_changes(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        logger.error("Repository is not initialized.")
        return False

    try:
        # 检查当前工作目录是否有未提交的更改
        if repo.is_dirty():
            logger.warning(
                "Working directory is dirty. please commit or stash your changes before reverting."
            )
            return False

        # 通过message定位到commit_hash
        commit = repo.git.log("--all", f"--grep={message}", "--format=%H", "-n", "1")
        if not commit:
            logger.warning(f"No commit found with message: {message}")
            return False

        commit_hash = commit

        # 获取从指定commit到HEAD的所有提交
        commits = list(repo.iter_commits(f"{commit_hash}..HEAD"))

        if not commits:
            repo.git.revert(commit, no_edit=True)
            logger.info(f"Reverted single commit: {commit}")
        else:
            # 从最新的提交开始，逐个回滚
            for commit in reversed(commits):
                try:
                    repo.git.revert(commit.hexsha, no_commit=True)
                    logger.info(f"Reverted changes from commit: {commit.hexsha}")
                except GitCommandError as e:
                    logger.error(f"Error reverting commit {commit.hexsha}: {e}")
                    repo.git.revert("--abort")
                    return False

            # 提交所有的回滚更改
            repo.git.commit(message=f"Reverted all changes up to {commit_hash}")

        logger.info(f"Successfully reverted changes up to {commit_hash}")

        ## this is a mark, chat_auto_coder.py need this
        print(f"Successfully reverted changes", flush=True)

        # # 如果之前有stash，现在应用它
        # if stashed:
        #     try:
        #         repo.git.stash('pop')
        #         logger.info("Applied stashed changes.")
        #     except GitCommandError as e:
        #         logger.error(f"Error applying stashed changes: {e}")
        #         logger.info("Please manually apply the stashed changes.")

        return True

    except GitCommandError as e:
        logger.error(f"Error during revert operation: {e}")
        return False


def revert_change(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        return False
    commit = repo.git.log("--all", f"--grep={message}", "--format=%H", "-n", "1")
    if commit:
        repo.git.revert(commit, no_edit=True)
        logger.info(f"Reverted changes with commit message: {message}")
        return True
    else:
        logger.warning(f"No commit found with message: {message}")
        return False


def get_uncommitted_changes(repo_path: str) -> str:
    """
    获取当前仓库未提交的所有变更,并以markdown格式返回详细报告
    
    Args:
        repo_path: Git仓库路径
        
    Returns:
        str: markdown格式的变更报告,包含新增/修改/删除的文件列表及其差异
    """
    repo = get_repo(repo_path)
    if repo is None:
        return "Error: Repository is not initialized."
        
    try:
        # 获取所有变更
        changes = {
            'new': [],      # 新增的文件
            'modified': [], # 修改的文件 
            'deleted': []   # 删除的文件
        }
        
        # 获取未暂存的变更
        diff_index = repo.index.diff(None)
        
        # 获取未追踪的文件
        untracked = repo.untracked_files
        
        # 处理未暂存的变更
        for diff_item in diff_index:
            file_path = diff_item.a_path
            diff_content = repo.git.diff(None, file_path)            
            if diff_item.new_file:
                changes['new'].append((file_path, diff_content))
            elif diff_item.deleted_file:
                changes['deleted'].append((file_path, diff_content))
            else:
                changes['modified'].append((file_path, diff_content))
                
        # 处理未追踪的文件    
        for file_path in untracked:
            try:
                with open(os.path.join(repo_path, file_path), 'r') as f:
                    content = f.read()
                changes['new'].append((file_path, f'+++ {file_path}\n{content}'))
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                
        # 生成markdown报告
        report = ["# Git Changes Report\n"]
        
        # 新增文件
        if changes['new']:
            report.append("\n## New Files")
            for file_path, diff in changes['new']:
                report.append(f"\n### {file_path}")
                report.append("```diff")
                report.append(diff)
                report.append("```")
                
        # 修改的文件        
        if changes['modified']:
            report.append("\n## Modified Files")
            for file_path, diff in changes['modified']:
                report.append(f"\n### {file_path}")
                report.append("```diff")
                report.append(diff)
                report.append("```")
                
        # 删除的文件
        if changes['deleted']:
            report.append("\n## Deleted Files")
            for file_path, diff in changes['deleted']:
                report.append(f"\n### {file_path}")
                report.append("```diff")
                report.append(diff)
                report.append("```")
                
        # 如果没有任何变更
        if not any(changes.values()):
            return "No uncommitted changes found."
            
        return "\n".join(report)
        
    except GitCommandError as e:
        logger.error(f"Error getting uncommitted changes: {e}")
        return f"Error: {str(e)}"

@byzerllm.prompt()
def generate_commit_message(changes_report: str) -> str:
    '''
    我是一个Git提交信息生成助手。我们的目标是通过一些变更报告，倒推用户的需求，将需求作为commit message。
    commit message 需要简洁，不要超过100个字符。

    下面是一些示例：
    <examples>
    <example>    
    ## New Files
    ###  notebooks/tests/test_long_context_rag_answer_question.ipynb
    ```diff
    diff --git a/notebooks/tests/test_long_context_rag_answer_question.ipynb b/notebooks/tests/test_long_context_rag_answer_question.ipynb
    new file mode 100644
    index 00000000..c676b557
    --- /dev/null
    +++ b/notebooks/tests/test_long_context_rag_answer_question.ipynb
    @@ -0,0 +1,122 @@
    +{
    + "cells": [
    +  {
    +   "cell_type": "markdown",
    +   "metadata": {},
    +   "source": [
    +    "# Test Long Context RAG Answer Question\n",
    +    "\n",
    +    "This notebook tests the `_answer_question` functionality in the `LongContextRAG` class."
    +   ]
    +  },
    +  {
    +   "cell_type": "code",
    +   "execution_count": null,
    +   "metadata": {},
    +   "outputs": [],
    +   "source": [
    +    "import os\n",
    +    "import sys\n",
    +    "from pathlib import Path\n",
    +    "import tempfile\n",
    +    "from loguru import logger\n",
    +    "from autocoder.rag.long_context_rag import LongContextRAG\n",
    +    "from autocoder.rag.rag_config import RagConfig\n",
    +    "from autocoder.rag.cache.simple_cache import AutoCoderRAGAsyncUpdateQueue\n",
    +    "from autocoder.rag.variable_holder import VariableHolder\n",
    +    "from tokenizers import Tokenizer\n",
    +    "\n",
    +    "# Setup tokenizer\n",
    +    "VariableHolder.TOKENIZER_PATH = \"/Users/allwefantasy/Downloads/tokenizer.json\"\n",
    +    "VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(VariableHolder.TOKENIZER_PATH)"
    +   ]
    +  },
    +  {
    +   "cell_type": "code",
    +   "execution_count": null,
    +   "metadata": {},
    +   "outputs": [],
    +   "source": [
    +    "# Create test files and directory\n",
    +    "test_dir = tempfile.mkdtemp()\n",
    +    "print(f\"Created test directory: {test_dir}\")\n",
    +    "\n",
    +    "# Create a test Python file\n",
    +    "test_file = os.path.join(test_dir, \"test_code.py\")\n",
    +    "with open(test_file, \"w\") as f:\n",
    +    "    f.write(\"\"\"\n",
    +    "def calculate_sum(a: int, b: int) -> int:\n",
    +    "    \"\"\"Calculate the sum of two integers.\"\"\"\n",
    +    "    return a + b\n",
    +    "\n",
    +    "def calculate_product(a: int, b: int) -> int:\n",
    +    "    \"\"\"Calculate the product of two integers.\"\"\"\n",
    +    "    return a * b\n",
    +    "    \"\"\")"
    +   ]
    +  },
    +  {
    +   "cell_type": "code",
    +   "execution_count": null,
    +   "metadata": {},
    +   "outputs": [],
    +   "source": [
    +    "# Initialize RAG components\n",
    +    "config = RagConfig(\n",
    +    "    model=\"gpt-4-1106-preview\",\n",
    +    "    path=test_dir,\n",
    +    "    required_exts=[\".py\"],\n",
    +    "    cache_type=\"simple\"\n",
    +    ")\n",
    +    "\n",
    +    "rag = LongContextRAG(config)\n",
    +    "\n",
    +    "# Test questions\n",
    +    "test_questions = [\n",
    +    "    \"What does the calculate_sum function do?\",\n",
    +    "    \"Show me all the functions that work with integers\",\n",
    +    "    \"What's the return type of calculate_product?\"\n",
    +    "]\n",
    +    "\n",
    +    "# Test answers\n",
    +    "for question in test_questions:\n",
    +    "    print(f\"\\nQuestion: {question}\")\n",
    +    "    answer = rag._answer_question(question)\n",
    +    "    print(f\"Answer: {answer}\")"
    +   ]
    +  },
    +  {
    +   "cell_type": "code",
    +   "execution_count": null,
    +   "metadata": {},
    +   "outputs": [],
    +   "source": [
    +    "# Clean up\n",
    +    "import shutil\n",
    +    "shutil.rmtree(test_dir)\n",
    +    "print(f\"Cleaned up test directory: {test_dir}\")"
    +   ]
    +  }
    + ],
    + "metadata": {
    +  "kernelspec": {
    +   "display_name": "Python 3",
    +   "language": "python",
    +   "name": "python3"
    +  },
    +  "language_info": {
    +   "codemirror_mode": {
    +    "name": "ipython",
    +    "version": 3
    +   },
    +   "file_extension": ".py",
    +   "mimetype": "text/x-python",
    +   "name": "python",
    +   "nbconvert_exporter": "python",
    +   "pygments_lexer": "ipython3",
    +   "version": "3.10.11"
    +  }
    + },
    + "nbformat": 4,
    + "nbformat_minor": 4
    +}
    \ No newline at end of file
    ```

    输出的commit 信息为：

    在 notebooks/tests 目录下新建一个 jupyter notebook, 对 @@_answer_question(location: src/autocoder/rag/long_context_rag.py) 进行测试
    <example>

    <example>
    ## Modified Files
    ### src/autocoder/utils/_markitdown.py
    ```diff
    diff --git a/src/autocoder/utils/_markitdown.py b/src/autocoder/utils/_markitdown.py
    index da69b92b..dcecb74e 100644
    --- a/src/autocoder/utils/_markitdown.py
    +++ b/src/autocoder/utils/_markitdown.py
    @@ -635,18 +635,22 @@ class DocxConverter(HtmlConverter):
        """
        Converts DOCX files to Markdown. Style information (e.g.m headings) and tables are preserved where possible.
        """
    +    
    +    def __init__(self):
    +        self._image_counter = 0
    +        super().__init__()
    
        def _save_image(self, image, output_dir: str) -> str:
            """
    -        保存图片并返回相对路径
    +        保存图片并返回相对路径，使用递增的计数器来命名文件
            """
            # 获取图片内容和格式
            image_content = image.open()
            image_format = image.content_type.split('/')[-1] if image.content_type else 'png'
            
    -        # 生成唯一文件名
    -        image_filename = f"image_{hash(image_content.read())}.{image_format}"
    -        image_content.seek(0)  # 重置文件指针
    +        # 增加计数器并生成文件名
    +        self._image_counter += 1
    +        image_filename = f"image_{self._image_counter}.{image_format}"
            
            # 保存图片
            image_path = os.path.join(output_dir, image_filename)
    ```

    输出的commit 信息为：

    @@DocxConverter(location: src/autocoder/utils/_markitdown.py) 中,修改 _save_image中保存图片的文件名使用递增而不是hash值
    </example>

    <example>
    ## Modified Files
    ### src/autocoder/common/code_auto_generate.py
    ### src/autocoder/common/code_auto_generate_diff.py
    ### src/autocoder/common/code_auto_generate_strict_diff.py
    ```diff
    diff --git a/src/autocoder/common/code_auto_generate.py b/src/autocoder/common/code_auto_generate.py
    index b8f3b364..1b3da198 100644
    --- a/src/autocoder/common/code_auto_generate.py
    +++ b/src/autocoder/common/code_auto_generate.py
    @@ -2,6 +2,7 @@ from typing import List, Dict, Tuple
    from autocoder.common.types import Mode
    from autocoder.common import AutoCoderArgs
    import byzerllm
    +from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
    
    
    class CodeAutoGenerate:
    @@ -146,6 +147,15 @@ class CodeAutoGenerate:
        ) -> Tuple[str, Dict[str, str]]:
            llm_config = {"human_as_model": self.args.human_as_model}
    
    +        if self.args.request_id and not self.args.skip_events:
    +            queue_communicate.send_event_no_wait(
    +                request_id=self.args.request_id,
    +                event=CommunicateEvent(
    +                    event_type=CommunicateEventType.CODE_GENERATE_START.value,
    +                    data=query,
    +                ),
    +            )
    +
            if self.args.template == "common":
                init_prompt = self.single_round_instruction.prompt(
                    instruction=query, content=source_content, context=self.args.context
    @@ -162,6 +172,16 @@ class CodeAutoGenerate:
    
            t = self.llm.chat_oai(conversations=conversations, llm_config=llm_config)
            conversations.append({"role": "assistant", "content": t[0].output})
    +
    +        if self.args.request_id and not self.args.skip_events:
    +            queue_communicate.send_event_no_wait(
    +                request_id=self.args.request_id,
    +                event=CommunicateEvent(
    +                    event_type=CommunicateEventType.CODE_GENERATE_END.value,
    +                    data="",
    +                ),
    +            )
    +
            return [t[0].output], conversations
    
        def multi_round_run(
    diff --git a/src/autocoder/common/code_auto_generate_diff.py b/src/autocoder/common/code_auto_generate_diff.py
    index 79a9e8d4..37f191a1 100644
    --- a/src/autocoder/common/code_auto_generate_diff.py
    +++ b/src/autocoder/common/code_auto_generate_diff.py
    @@ -2,6 +2,7 @@ from typing import List, Dict, Tuple
    from autocoder.common.types import Mode
    from autocoder.common import AutoCoderArgs
    import byzerllm
    +from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
    
    
    class CodeAutoGenerateDiff:
    @@ -289,6 +290,15 @@ class CodeAutoGenerateDiff:
        ) -> Tuple[str, Dict[str, str]]:
            llm_config = {"human_as_model": self.args.human_as_model}
    
    +        if self.args.request_id and not self.args.skip_events:
    +            queue_communicate.send_event_no_wait(
    +                request_id=self.args.request_id,
    +                event=CommunicateEvent(
    +                    event_type=CommunicateEventType.CODE_GENERATE_START.value,
    +                    data=query,
    +                ),
    +            )
    +
            init_prompt = self.single_round_instruction.prompt(
                instruction=query, content=source_content, context=self.args.context
            )
    @@ -300,6 +310,16 @@ class CodeAutoGenerateDiff:
    
            t = self.llm.chat_oai(conversations=conversations, llm_config=llm_config)
            conversations.append({"role": "assistant", "content": t[0].output})
    +
    +        if self.args.request_id and not self.args.skip_events:
    +            queue_communicate.send_event_no_wait(
    +                request_id=self.args.request_id,
    +                event=CommunicateEvent(
    +                    event_type=CommunicateEventType.CODE_GENERATE_END.value,
    +                    data="",
    +                ),
    +            )
    +
            return [t[0].output], conversations
    
        def multi_round_run(
    diff --git a/src/autocoder/common/code_auto_generate_strict_diff.py b/src/autocoder/common/code_auto_generate_strict_diff.py
    index 8874ae7a..91409c44 100644
    --- a/src/autocoder/common/code_auto_generate_strict_diff.py
    +++ b/src/autocoder/common/code_auto_generate_strict_diff.py
    @@ -2,6 +2,7 @@ from typing import List, Dict, Tuple
    from autocoder.common.types import Mode
    from autocoder.common import AutoCoderArgs
    import byzerllm
    +from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
    
    
    class CodeAutoGenerateStrictDiff:
    @@ -260,6 +261,15 @@ class CodeAutoGenerateStrictDiff:
        ) -> Tuple[str, Dict[str, str]]:
            llm_config = {"human_as_model": self.args.human_as_model}
    
    +        if self.args.request_id and not self.args.skip_events:
    +            queue_communicate.send_event_no_wait(
    +                request_id=self.args.request_id,
    +                event=CommunicateEvent(
    +                    event_type=CommunicateEventType.CODE_GENERATE_START.value,
    +                    data=query,
    +                ),
    +            )
    +
            init_prompt = self.single_round_instruction.prompt(
                instruction=query, content=source_content, context=self.args.context
            )
    @@ -271,6 +281,16 @@ class CodeAutoGenerateStrictDiff:
    
            t = self.llm.chat_oai(conversations=conversations, llm_config=llm_config)
            conversations.append({"role": "assistant", "content": t[0].output})
    +
    +        if self.args.request_id and not self.args.skip_events:
    +            queue_communicate.send_event_no_wait(
    +                request_id=self.args.request_id,
    +                event=CommunicateEvent(
    +                    event_type=CommunicateEventType.CODE_GENERATE_END.value,
    +                    data="",
    +                ),
    +            )
    +
            return [t[0].output], conversations
    
        def multi_round_run(
    ```

    输出的commit 信息为：

    参考 @src/autocoder/common/code_auto_merge_editblock.py 中CODE_GENERATE_START,CODE_GENERATE_END 事件, 在其他文件里添加也添加这些事件. 注意,只需要修改 single_round_run 方法.
    </example>
    </examples>
    
    下面是变更报告：
    {{ changes_report }}    

    请输出commit message, 不要输出任何其他内容.
    '''

def print_commit_info(commit_result: CommitResult):
    console = Console()
    table = Table(
        title="Commit Information (Use /revert to revert this commit)", show_header=True, header_style="bold magenta"
    )
    table.add_column("Attribute", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    table.add_row("Commit Hash", commit_result.commit_hash)
    table.add_row("Commit Message", commit_result.commit_message)
    table.add_row("Changed Files", "\n".join(commit_result.changed_files))

    console.print(
        Panel(table, expand=False, border_style="green", title="Git Commit Summary")
    )

    if commit_result.diffs:
        for file, diff in commit_result.diffs.items():
            console.print(f"\n[bold blue]File: {file}[/bold blue]")
            syntax = Syntax(diff, "diff", theme="monokai", line_numbers=True)
            console.print(
                Panel(syntax, expand=False, border_style="yellow", title="File Diff")
            )
