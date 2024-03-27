import os
from git import Repo, GitCommandError
from loguru import logger

def get_repo(repo_path: str) -> Repo:
    repo = Repo(repo_path)
    return repo

def commit_changes(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        return False
    
    repo.git.add(all=True)
    repo.index.commit(message)
    logger.info(f"Committed changes with message: {message}")
        

def get_current_branch(repo_path: str) -> str:
    repo = get_repo(repo_path)
    if repo is None:
        return ""
    branch = repo.active_branch.name
    return branch

def revert_changes(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        return False

    commit = repo.git.log('--all', f'--grep={message}', '--format=%H', '-n', '1') 
    if commit:
        repo.git.revert(commit, no_edit=True)
        logger.info(f"Reverted changes with commit message: {message}")
        return True
    else:
        logger.warning(f"No commit found with message: {message}")
        return False