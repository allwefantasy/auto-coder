
import os
from typing import Optional, List
import pathspec

DEFAULT_IGNORED_DIRS = ['.git', '.auto-coder', 'node_modules', '.mvn', '.idea', '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle']


def load_ignore_spec(source_dir: str) -> Optional[pathspec.PathSpec]:
    """
    Loads .autocoderignore file from the source_dir if it exists.
    Returns a PathSpec object or None if no ignore file.
    """
    ignore_file_path = os.path.join(source_dir, ".autocoderignore")
    if not os.path.isfile(ignore_file_path):
        return None
    try:
        with open(ignore_file_path, "r") as f:
            ignore_patterns = f.read().splitlines()
        spec = pathspec.PathSpec.from_lines("gitwildmatch", ignore_patterns)
        return spec
    except Exception:
        return None


def should_ignore(path: str, ignore_spec: Optional[pathspec.PathSpec], ignored_dirs: List[str], source_dir: str) -> bool:
    """
    Determine if a given path should be ignored based on ignore_spec and ignored_dirs.
    - path: absolute path
    - ignore_spec: PathSpec object or None
    - ignored_dirs: list of directory names to ignore
    - source_dir: root source directory absolute path
    """
    rel_path = os.path.relpath(path, source_dir)
    parts = rel_path.split(os.sep)

    # Always ignore if any part matches ignored_dirs
    for part in parts:
        if part in ignored_dirs:
            return True

    # If ignore_spec exists, use it to check
    if ignore_spec:
        # pathspec expects posix style paths
        rel_path_posix = rel_path.replace(os.sep, "/")
        # Check both file and dir ignoring
        if ignore_spec.match_file(rel_path_posix):
            return True

    return False
