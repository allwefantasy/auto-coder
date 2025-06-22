

#!/usr/bin/env python3
"""
Auto-Coder CLI 自动补全包装器

提供一个独立的补全脚本，不依赖于特定的 shell 环境
"""

import sys
import os

def main():
    """主函数，处理自动补全请求"""
    try:
        # 设置环境变量以启用 argcomplete
        os.environ.setdefault('_ARGCOMPLETE_COMPLETE', 'complete')
        
        # 导入并运行 CLI
        from autocoder.sdk.cli.main import AutoCoderCLI
        
        # 模拟 auto-coder.run 命令
        sys.argv[0] = 'auto-coder.run'
        
        # 解析参数（这会触发自动补全）
        AutoCoderCLI.parse_args()
        
    except SystemExit:
        # argcomplete 会调用 sys.exit，这是正常的
        pass
    except Exception as e:
        # 在补全过程中出现错误，静默处理
        pass

if __name__ == '__main__':
    main()


