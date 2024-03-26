import os
from git import Repo, GitCommandError
from loguru import logger

def get_repo(repo_path: str) -> Repo:
    try:
        repo = Repo(repo_path)
        return repo
    except GitCommandError as e:
        logger.warning(f"Failed to get Git repository at {repo_path}. Error: {str(e)}")
        return None

def commit_changes(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        return False

    try:
        repo.git.add(all=True)
        repo.index.commit(message)
        logger.info(f"Committed changes with message: {message}")
        return True
    except GitCommandError as e:
        logger.warning(f"Failed to commit changes. Error: {str(e)}")
        return False

def get_current_branch(repo_path: str) -> str:
    repo = get_repo(repo_path)
    if repo is None:
        return ""

    try:
        branch = repo.active_branch.name
        return branch
    except GitCommandError as e:
        logger.warning(f"Failed to get current branch. Error: {str(e)}")
        return ""

def revert_changes(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        return False

    try:
        commit = repo.git.log('--all', f'--grep={message}', '--format=%H', '-n', '1') 
        if commit:
            repo.git.revert(commit, no_edit=True)
            logger.info(f"Reverted changes with commit message: {message}")
            return True
        else:
            logger.warning(f"No commit found with message: {message}")
            return False
    except GitCommandError as e:
        logger.warning(f"Failed to revert changes. Error: {str(e)}")
        return False