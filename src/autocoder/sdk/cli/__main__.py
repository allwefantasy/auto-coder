#!/usr/bin/env python3
"""
CLI 模块主入口点
"""

import sys
import argparse
from pathlib import Path

def main():
    """主入口点，路由到不同的 CLI 功能"""
    
    # 检查是否是自动补全相关的命令
    if len(sys.argv) > 1 and sys.argv[1] in ["install", "uninstall", "test"]:
        # 路由到自动补全安装工具
        from .install_completion import main as install_main
        install_main()
        return
    
    # 检查是否有 -p 参数（这意味着是查询命令）
    if "-p" in sys.argv or "--prompt" in sys.argv or "--print" in sys.argv:
        # 路由到实际的 Auto-Coder CLI
        from .auto_coder_cli import main as cli_main
        sys.exit(cli_main())
        return
    
    # 检查其他 CLI 参数
    if any(arg in sys.argv for arg in ["--help", "-h", "--version"]):
        from .auto_coder_cli import main as cli_main
        sys.exit(cli_main())
        return
    
    # 默认显示自动补全工具的帮助
    from .install_completion import main as install_main
    install_main()

if __name__ == "__main__":
    main()

