
import os
import shutil
from pathlib import Path

import pytest

from src.autocoder.common.ignorefiles import ignore_file_utils

@pytest.fixture(autouse=True)
def cleanup_ignore_manager(monkeypatch):
    """
    在每个测试前后清理 IgnoreFileManager 的单例状态，保证测试隔离
    """
    # 备份原始实例
    original_instance = ignore_file_utils._ignore_manager
    # 强制重新加载忽略规则
    def reset_ignore_manager():
        ignore_file_utils.IgnoreFileManager._instance = None
        return ignore_file_utils.IgnoreFileManager()

    monkeypatch.setattr(ignore_file_utils, "_ignore_manager", reset_ignore_manager())
    yield
    # 恢复原始实例
    ignore_file_utils._ignore_manager = original_instance


def test_default_excludes(tmp_path, monkeypatch):
    # 切换当前工作目录
    monkeypatch.chdir(tmp_path)

    # 不创建任何 .autocoderignore 文件，使用默认排除规则
    # 创建默认排除目录
    for dirname in ignore_file_utils.DEFAULT_EXCLUDES:
        (tmp_path / dirname).mkdir(parents=True, exist_ok=True)
        # 应该被忽略
        assert ignore_file_utils.should_ignore(str(tmp_path / dirname)) is True

    # 创建不会被忽略的文件
    normal_file = tmp_path / "myfile.txt"
    normal_file.write_text("hello")
    assert ignore_file_utils.should_ignore(str(normal_file)) is False


def test_custom_ignore_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # 创建自定义忽略文件
    ignore_file = tmp_path / ".autocoderignore"
    ignore_file.write_text("data/**\nsecret.txt")

    # 重新初始化忽略管理器以加载新规则
    ignore_file_utils.IgnoreFileManager._instance = None
    ignore_file_utils._ignore_manager = ignore_file_utils.IgnoreFileManager()

    # 符合忽略规则的路径
    ignored_dir = tmp_path / "data" / "subdir"
    ignored_dir.mkdir(parents=True)
    ignored_file = tmp_path / "secret.txt"
    ignored_file.write_text("secret")

    assert ignore_file_utils.should_ignore(str(ignored_dir)) is True
    assert ignore_file_utils.should_ignore(str(ignored_file)) is True

    # 不应被忽略的文件
    normal_file = tmp_path / "keepme.txt"
    normal_file.write_text("keep me")
    assert ignore_file_utils.should_ignore(str(normal_file)) is False


def test_nested_ignore_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # 没有根目录的.ignore，创建.auto-coder/.autocoderignore
    nested_dir = tmp_path / ".auto-coder"
    nested_dir.mkdir()

    ignore_file = nested_dir / ".autocoderignore"
    ignore_file.write_text("logs/**")

    # 重新初始化忽略管理器以加载新规则
    ignore_file_utils.IgnoreFileManager._instance = None
    ignore_file_utils._ignore_manager = ignore_file_utils.IgnoreFileManager()

    ignored_dir = tmp_path / "logs" / "2024"
    ignored_dir.mkdir(parents=True)
    assert ignore_file_utils.should_ignore(str(ignored_dir)) is True

    normal_file = tmp_path / "main.py"
    normal_file.write_text("# main")
    assert ignore_file_utils.should_ignore(str(normal_file)) is False
