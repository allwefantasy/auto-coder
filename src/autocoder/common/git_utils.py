import os
from git import Repo, GitCommandError
from loguru import logger
from typing import List, Optional
from pydantic import BaseModel
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
