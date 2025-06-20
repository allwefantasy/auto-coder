

"""
Auto-Coder CLI 模块主入口

允许通过 python -m autocoder.sdk.cli 运行 CLI 工具
"""

import sys
from .install_completion import main

if __name__ == '__main__':
    sys.exit(main())

