#!/usr/bin/env python3
"""
运行Chat Auto Coder并加载插件
"""

import os
import sys
import subprocess
import argparse


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="运行Chat Auto Coder并加载插件")
    parser.add_argument(
        "--plugin_config",
        type=str,
        default="sample_plugin_config.json",
        help="插件配置文件路径",
    )
    parser.add_argument("--quick", action="store_true", help="快速启动，跳过系统初始化")
    parser.add_argument("--debug", action="store_true", help="启用调试模式")
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 构建命令
    # 使用已安装的autocoder模块而不是直接运行脚本
    cmd = [sys.executable, "-m", "autocoder.chat_auto_coder"]

    # 添加参数
    if args.plugin_config:
        if os.path.exists(args.plugin_config):
            cmd.extend(["--plugin_config", args.plugin_config])
        else:
            print(f"警告: 插件配置文件 '{args.plugin_config}' 不存在，使用默认配置")

    if args.quick:
        cmd.append("--quick")

    if args.debug:
        cmd.append("--debug")

    # 运行命令
    print(f"运行命令: {' '.join(cmd)}")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"运行时错误: {e}")


if __name__ == "__main__":
    main()
