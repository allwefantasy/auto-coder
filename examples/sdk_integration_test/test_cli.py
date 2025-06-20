#!/usr/bin/env python3
"""
CLI 测试脚本

测试 Auto-Coder SDK 的命令行接口功能
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n=== {description} ===")
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent
        )
        
        print(f"返回码: {result.returncode}")
        if result.stdout:
            print(f"输出:\n{result.stdout}")
        if result.stderr:
            print(f"错误:\n{result.stderr}")
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ 命令执行超时")
        return False
    except Exception as e:
        print(f"❌ 命令执行失败: {e}")
        return False

def test_cli_help():
    """测试帮助命令"""
    return run_command([
        sys.executable, "-m", "autocoder.sdk.cli", "--help"
    ], "测试帮助命令")

def test_cli_version():
    """测试版本命令"""
    return run_command([
        sys.executable, "-m", "autocoder.sdk.cli", "--version"
    ], "测试版本命令")

def test_cli_basic_query():
    """测试基本查询"""
    return run_command([
        sys.executable, "-m", "autocoder.sdk.cli",
        "-p", "Write a simple hello function"
    ], "测试基本查询")

def test_cli_json_output():
    """测试JSON输出"""
    return run_command([
        sys.executable, "-m", "autocoder.sdk.cli",
        "-p", "Explain what this script does",
        "--output-format", "json"
    ], "测试JSON输出")

def test_cli_stream_json_output():
    """测试流式JSON输出"""
    return run_command([
        sys.executable, "-m", "autocoder.sdk.cli",
        "-p", "Generate a simple function",
        "--output-format", "stream-json"
    ], "测试流式JSON输出")

def main():
    """主测试函数"""
    print("开始 Auto-Coder SDK CLI 测试")
    
    # 设置环境变量
    project_root = Path(__file__).parent.parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    
    tests = [
        ("帮助命令", test_cli_help),
        ("版本命令", test_cli_version),
        ("基本查询", test_cli_basic_query),
        ("JSON输出", test_cli_json_output),
        ("流式JSON输出", test_cli_stream_json_output),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n测试完成: {passed}/{total} 通过")
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 