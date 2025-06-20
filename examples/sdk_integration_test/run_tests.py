#!/usr/bin/env python3
"""
主测试运行脚本

运行所有 Auto-Coder SDK 集成测试
"""

import sys
import subprocess
import os
from pathlib import Path

def run_test(test_name, test_script):
    """运行单个测试脚本"""
    print(f"\n{'='*60}")
    print(f"运行测试: {test_name}")
    print(f"{'='*60}")
    
    try:
        # 设置环境
        env = os.environ.copy()
        project_root = Path(__file__).parent.parent.parent
        env["PYTHONPATH"] = str(project_root / "src")
        
        # 运行测试
        result = subprocess.run(
            [sys.executable, test_script],
            cwd=Path(__file__).parent,
            env=env,
            capture_output=False,
            text=True
        )
        
        success = result.returncode == 0
        print(f"\n{test_name} 测试结果: {'✅ 通过' if success else '❌ 失败'}")
        return success
        
    except Exception as e:
        print(f"❌ {test_name} 测试异常: {e}")
        return False

def main():
    """主函数"""
    print("开始运行 Auto-Coder SDK 集成测试")
    
    tests = [
        ("Python API 测试", "test_python_api.py"),
        ("CLI 测试", "test_cli.py"),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_script in tests:
        if run_test(test_name, test_script):
            passed += 1
    
    print(f"\n{'='*60}")
    print(f"测试完成: {passed}/{total} 通过")
    print(f"{'='*60}")
    
    # 如果所有测试都通过，返回 0；否则返回 1
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 