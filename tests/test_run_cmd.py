
import sys
import platform
import types

import pytest

# 导入run_cmd函数
from src.autocoder.common.run_cmd import run_cmd


def test_run_cmd():
    """
    测试run_cmd函数，确保其正确执行命令并返回预期结果。
    """
    # 选择一个简单的跨平台命令
    cmd = "echo hello"

    result = run_cmd(cmd)

    # 兼容pexpect返回tuple 和 subprocess返回生成器的两种情况
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
        # subprocess没有明确exit code, 只检查输出
        assert "hello" in output_str, f"输出不包含hello: {output_str}"
    else:
        pytest.fail(f"run_cmd返回了未知类型: {type(result)}")


if __name__ == "__main__":
    # 方便直接运行此文件调试
    sys.exit(pytest.main([__file__]))
