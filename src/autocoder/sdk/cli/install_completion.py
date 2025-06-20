
#!/usr/bin/env python3
"""
Auto-Coder CLI 自动补全安装脚本

该脚本帮助用户在不同的 shell 环境中安装 auto-coder.run 命令的自动补全功能。
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional


class CompletionInstaller:
    """自动补全安装器"""
    
    def __init__(self):
        self.shell = self._detect_shell()
        self.home_dir = Path.home()
        
    def _detect_shell(self) -> str:
        """检测当前使用的 shell"""
        shell = os.environ.get('SHELL', '')
        if 'bash' in shell:
            return 'bash'
        elif 'zsh' in shell:
            return 'zsh'
        elif 'fish' in shell:
            return 'fish'
        else:
            return 'unknown'
    
    def _get_completion_script(self, shell: str) -> str:
        """获取对应 shell 的补全脚本"""
        if shell == 'bash':
            return 'eval "$(register-python-argcomplete auto-coder.run)"'
        elif shell == 'zsh':
            return '''# 启用 bash 兼容模式用于补全
autoload -U +X bashcompinit && bashcompinit
eval "$(register-python-argcomplete auto-coder.run)"'''
        elif shell == 'fish':
            return 'register-python-argcomplete --shell fish auto-coder.run | source'
        else:
            return ''
    
    def _get_config_file(self, shell: str) -> Optional[Path]:
        """获取对应 shell 的配置文件路径"""
        if shell == 'bash':
            # 按优先级检查 bash 配置文件
            candidates = ['.bashrc', '.bash_profile', '.profile']
            for candidate in candidates:
                config_file = self.home_dir / candidate
                if config_file.exists():
                    return config_file
            # 如果都不存在，默认使用 .bashrc
            return self.home_dir / '.bashrc'
        elif shell == 'zsh':
            return self.home_dir / '.zshrc'
        elif shell == 'fish':
            config_dir = self.home_dir / '.config' / 'fish'
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir / 'config.fish'
        else:
            return None
    
    def check_argcomplete_installed(self) -> bool:
        """检查 argcomplete 是否已安装"""
        try:
            import argcomplete
            return True
        except ImportError:
            return False
    
    def check_register_command_available(self) -> bool:
        """检查 register-python-argcomplete 命令是否可用"""
        try:
            result = subprocess.run(['register-python-argcomplete', '--help'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_completion(self, force: bool = False) -> bool:
        """安装自动补全功能"""
        print(f"检测到的 shell: {self.shell}")
        
        # 检查依赖
        if not self.check_argcomplete_installed():
            print("错误: argcomplete 包未安装")
            print("请运行: pip install argcomplete")
            return False
        
        if not self.check_register_command_available():
            print("错误: register-python-argcomplete 命令不可用")
            print("请确保 argcomplete 正确安装并在 PATH 中")
            return False
        
        if self.shell == 'unknown':
            print("错误: 无法检测到支持的 shell")
            print("支持的 shell: bash, zsh, fish")
            return False
        
        config_file = self._get_config_file(self.shell)
        if not config_file:
            print(f"错误: 无法确定 {self.shell} 的配置文件")
            return False
        
        completion_script = self._get_completion_script(self.shell)
        if not completion_script:
            print(f"错误: 不支持的 shell: {self.shell}")
            return False
        
        # 检查是否已经安装
        if config_file.exists():
            content = config_file.read_text()
            if 'auto-coder.run' in content and not force:
                print(f"自动补全似乎已经安装在 {config_file}")
                print("使用 --force 参数强制重新安装")
                return True
        
        # 添加补全脚本到配置文件
        try:
            with open(config_file, 'a') as f:
                f.write(f'\n# Auto-Coder CLI 自动补全\n')
                f.write(f'{completion_script}\n')
            
            print(f"✓ 自动补全已安装到 {config_file}")
            print(f"请重新加载 shell 配置或运行: source {config_file}")
            return True
            
        except Exception as e:
            print(f"错误: 无法写入配置文件 {config_file}: {e}")
            return False
    
    def uninstall_completion(self) -> bool:
        """卸载自动补全功能"""
        config_file = self._get_config_file(self.shell)
        if not config_file or not config_file.exists():
            print("未找到配置文件或自动补全未安装")
            return True
        
        try:
            lines = config_file.read_text().splitlines()
            new_lines = []
            skip_next = False
            
            for line in lines:
                if '# Auto-Coder CLI 自动补全' in line:
                    skip_next = True
                    continue
                elif skip_next and 'auto-coder.run' in line:
                    skip_next = False
                    continue
                else:
                    skip_next = False
                    new_lines.append(line)
            
            config_file.write_text('\n'.join(new_lines))
            print(f"✓ 自动补全已从 {config_file} 中移除")
            return True
            
        except Exception as e:
            print(f"错误: 无法修改配置文件 {config_file}: {e}")
            return False
    
    def test_completion(self) -> bool:
        """测试自动补全是否工作"""
        print("测试自动补全功能...")
        try:
            # 尝试获取补全建议
            result = subprocess.run([
                'python', '-c', 
                'import argcomplete; from autocoder.sdk.cli.main import AutoCoderCLI; '
                'parser = AutoCoderCLI.parse_args.__func__(AutoCoderCLI, []); '
                'print("自动补全功能正常")'
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print("✓ 自动补全功能测试通过")
                return True
            else:
                print(f"✗ 自动补全功能测试失败: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"✗ 自动补全功能测试失败: {e}")
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Auto-Coder CLI 自动补全安装工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 安装自动补全
  python -m autocoder.sdk.cli.install_completion install
  
  # 强制重新安装
  python -m autocoder.sdk.cli.install_completion install --force
  
  # 卸载自动补全
  python -m autocoder.sdk.cli.install_completion uninstall
  
  # 测试自动补全
  python -m autocoder.sdk.cli.install_completion test
"""
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 安装命令
    install_parser = subparsers.add_parser('install', help='安装自动补全')
    install_parser.add_argument('--force', action='store_true', help='强制重新安装')
    
    # 卸载命令
    subparsers.add_parser('uninstall', help='卸载自动补全')
    
    # 测试命令
    subparsers.add_parser('test', help='测试自动补全功能')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    installer = CompletionInstaller()
    
    if args.command == 'install':
        success = installer.install_completion(force=args.force)
        return 0 if success else 1
    elif args.command == 'uninstall':
        success = installer.uninstall_completion()
        return 0 if success else 1
    elif args.command == 'test':
        success = installer.test_completion()
        return 0 if success else 1
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())

