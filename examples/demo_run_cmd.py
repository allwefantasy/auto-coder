
import sys
import time
from autocoder.common.run_cmd import run_cmd_subprocess_generator, run_cmd_pexpect

def demo_subprocess_generator():
    print("=== 使用 run_cmd_subprocess_generator 执行命令，逐步输出内容 ===")
    cmd = "echo 'hello from subprocess generator'"
    try:
        for chunk in run_cmd_subprocess_generator(cmd):
            # 模拟处理延迟
            time.sleep(0.05)
            # 实时打印命令输出
            sys.stdout.write(chunk)
            sys.stdout.flush()
    except Exception as e:
        print(f"发生异常: {e}")
    print("\n=== subprocess generator 结束 ===\n")

def demo_pexpect():
    print("=== 使用 run_cmd_pexpect 执行命令，捕获完整交互输出 ===")
    cmd = "echo 'hello from pexpect'"
    exit_code, output = run_cmd_pexpect(cmd)
    print(f"退出码: {exit_code}")
    print(f"完整输出:\n{output}")
    print("=== pexpect 结束 ===\n")

def main():
    print("演示 run_cmd_subprocess_generator：")
    demo_subprocess_generator()

    print("演示 run_cmd_pexpect：")
    demo_pexpect()

if __name__ == "__main__":
    main()
