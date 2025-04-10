
import sys
import platform
import types
import io
import os
from unittest import mock

import pytest

# 导入待测试函数
from src.autocoder.common.run_cmd import (
    run_cmd,
    run_cmd_subprocess,
    run_cmd_pexpect,
    get_windows_parent_process_name,
)


def test_run_cmd():
    """
    测试run_cmd函数，确保其正确执行命令并返回预期结果。
    """
    cmd = "echo hello"

    result = run_cmd(cmd)

    if isinstance(result, tuple):
        # pexpect模式
        exit_code, output = result
        assert exit_code == 0, f"命令退出码非零: {exit_code}"
        assert "hello" in output, f"输出不包含hello: {output}"
    elif isinstance(result, types.GeneratorType):
        # subprocess生成器模式
        output_str = ""
        try:
            for chunk in result:
                output_str += chunk
        except Exception as e:
            pytest.fail(f"运行命令时发生异常: {e}")
        assert "hello" in output_str, f"输出不包含hello: {output_str}"
    else:
        pytest.fail(f"run_cmd返回了未知类型: {type(result)}")


def test_run_cmd_subprocess_normal():
    """
    测试run_cmd_subprocess正常执行
    """
    cmd = "echo hello_subprocess"
    gen = run_cmd_subprocess(cmd)
    output = ""
    try:
        for chunk in gen:
            output += chunk
    except Exception as e:
        pytest.fail(f"run_cmd_subprocess异常: {e}")
    assert "hello_subprocess" in output


def test_run_cmd_subprocess_error():
    """
    测试run_cmd_subprocess异常命令
    """
    cmd = "non_existing_command_xyz"
    gen = run_cmd_subprocess(cmd)
    output = ""
    for chunk in gen:
        output += chunk
    # 应该包含错误提示
    assert "[run_cmd_subprocess error]" in output or "not found" in output or "无法" in output or "未找到" in output


def test_run_cmd_pexpect_normal():
    """
    测试run_cmd_pexpect正常执行
    """
    if platform.system() == "Windows":
        pytest.skip("Windows上跳过pexpect测试")

    cmd = "echo hello_pexpect"
    exit_code, output = run_cmd_pexpect(cmd)
    assert exit_code == 0, f"pexpect退出码非零: {exit_code}"
    assert "hello_pexpect" in output, f"pexpect输出不包含预期内容: {output}"


def test_run_cmd_pexpect_error():
    """
    测试run_cmd_pexpect异常命令
    """
    if platform.system() == "Windows":
        pytest.skip("Windows上跳过pexpect测试")

    cmd = "non_existing_command_xyz"
    exit_code, output = run_cmd_pexpect(cmd)
    assert exit_code != 0, "异常命令应返回非零退出码"
    assert "not found" in output or "command not found" in output or "无法" in output or "未找到" in output


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
