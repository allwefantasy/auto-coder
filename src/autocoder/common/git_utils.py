import os
from git import Repo, GitCommandError
from loguru import logger
from typing import List

def init(repo_path: str) -> bool:
    if not os.path.exists(repo_path):
        os.makedirs(repo_path)

    if os.path.exists(os.path.join(repo_path, '.git')):
        logger.warning(f"The directory {repo_path} is already a Git repository. Skipping initialization.")
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

def commit_changes(repo_path: str, message: str) -> bool:
    repo = get_repo(repo_path)
    if repo is None:
        logger.error("Repository is not initialized.")
        return False
    try:
        repo.git.add(all=True)
        commit = repo.index.commit(message)
        logger.info(f"Committed changes with message: {message}")
        logger.info(f"Commit hash: {commit.hexsha}")
        # Check if there is a parent commit to compare against
        if commit.parents:
            changed_files = repo.git.diff(commit.parents[0].hexsha, commit.hexsha, name_only=True).split('\n')
            logger.info(f"Changed files: {changed_files}")
            for file in changed_files:
                if file.strip():
                    diff = repo.git.diff(commit.parents[0].hexsha, commit.hexsha, file)
                    logger.info(f"Diff for {file}:\n{diff}")
        else:
            logger.info("This is the initial commit, no parent to compare against.")
        return True
    except GitCommandError as e:
        logger.error(f"Error during commit operation: {e}")
        return False

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