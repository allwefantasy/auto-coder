
import sys
import platform
from unittest import mock
import io

import pytest

from autocoder.common.run_cmd import (
    run_cmd,
    run_cmd_subprocess,
    run_cmd_subprocess_generator,
    run_cmd_pexpect,
    get_windows_parent_process_name,
)

def test_run_cmd_basic():
    """
    测试run_cmd函数，确保其正确执行命令并返回预期结果。
    """
    cmd = "echo hello"
    exit_code, output = run_cmd(cmd)
    assert exit_code == 0, f"命令退出码非零: {exit_code}"
    assert "hello" in output, f"输出不包含hello: {output}"

def test_run_cmd_subprocess_normal():
    """
    测试run_cmd_subprocess正常执行命令，逐步输出。
    """
    cmd = "echo hello_subprocess"
    gen = run_cmd_subprocess_generator(cmd)
    output = ""
    try:
        for chunk in gen:
            output += chunk
    except Exception as e:
        pytest.fail(f"run_cmd_subprocess异常: {e}")
    assert "hello_subprocess" in output

def test_run_cmd_subprocess_error():
    """
    测试run_cmd_subprocess执行错误命令时能否正确返回异常信息。
    """
    cmd = "non_existing_command_xyz"
    gen = run_cmd_subprocess_generator(cmd)
    output = ""
    for chunk in gen:
        output += chunk
    # 应该包含错误提示
    assert "[run_cmd_subprocess error]" in output or "not found" in output or "无法" in output or "未找到" in output

def test_run_cmd_pexpect_mock():
    """
    测试run_cmd_pexpect函数，mock pexpect交互行为。
    """
    with mock.patch("pexpect.spawn") as mock_spawn:
        mock_child = mock.MagicMock()
        mock_child.exitstatus = 0
        mock_child.interact.side_effect = lambda output_filter=None: output_filter(b"mock output\n")
        mock_child.close.return_value = None
        mock_child.exitstatus = 0
        mock_child.getvalue = lambda: b"mock output\n"
        mock_spawn.return_value = mock_child

        # 由于run_cmd_pexpect内部会decode BytesIO内容
        exit_code, output = run_cmd_pexpect("echo hello", verbose=False)
        assert exit_code == 0
        assert "mock output" in output

def test_get_windows_parent_process_name_mocked():
    """
    测试get_windows_parent_process_name，模拟不同父进程
    """
    if platform.system() != "Windows":
        # 非Windows系统跳过
        return

    # 构造mock进程树
    class FakeProcess:
        def __init__(self, name, parent=None):
            self._name = name
            self._parent = parent

        def name(self):
            return self._name

        def parent(self):
            return self._parent

    powershell_proc = FakeProcess("powershell.exe")
    cmd_proc = FakeProcess("cmd.exe")
    other_proc = FakeProcess("python.exe")

    # 模拟powershell父进程
    with mock.patch("psutil.Process") as MockProcess:
        MockProcess.return_value = FakeProcess("python.exe", powershell_proc)
        assert get_windows_parent_process_name() == "powershell.exe"

    # 模拟cmd父进程
    with mock.patch("psutil.Process") as MockProcess:
        MockProcess.return_value = FakeProcess("python.exe", cmd_proc)
        assert get_windows_parent_process_name() == "cmd.exe"

    # 模拟无匹配父进程
    with mock.patch("psutil.Process") as MockProcess:
        MockProcess.return_value = FakeProcess("python.exe", other_proc)
        assert get_windows_parent_process_name() is None

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
