#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AutoCoder 安装程序打包脚本

使用 PyInstaller 支持多平台打包（macOS/Windows/Linux），包括 Python 解释器和所有依赖库，
打包成一个单独的可执行文件。

使用方法:
    python scripts/build_installer.py [--platform PLATFORM] [--name NAME] [--clean]

参数:
    --platform: 目标平台，可选值为 'win', 'mac', 'linux' 或 'all'（默认）
    --name:     输出安装程序的名称（不含扩展名），默认为 'AutoCoderInstaller'
    --clean:    清理构建文件和临时文件
    --debug:    启用调试模式，生成更多日志信息
"""

import os
import sys
import shutil
import platform as sys_platform
import subprocess
import argparse
from pathlib import Path

# 项目根目录
ROOT_DIR = Path(__file__).parent.parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
SPEC_DIR = ROOT_DIR / "specs"

# 主程序入口
MAIN_APP = ROOT_DIR / "src" / "autocoder" / "chat_auto_coder.py"

# 平台映射
PLATFORMS = {
    'win': 'Windows',
    'mac': 'Darwin',
    'linux': 'Linux'
}

# 平台特定的可执行文件扩展名
PLATFORM_EXT = {
    'win': '.exe',
    'mac': '',
    'linux': ''
}

def check_requirements():
    """检查必要的工具是否安装"""
    try:
        import PyInstaller
        print(f"PyInstaller 版本: {PyInstaller.__version__}")
    except ImportError:
        print("错误: 请先安装 PyInstaller: pip install pyinstaller")
        sys.exit(1)

def clean():
    """清理构建文件和临时文件"""
    print("清理构建文件和临时文件...")
    for dir_path in [BUILD_DIR, DIST_DIR, SPEC_DIR]:
        if dir_path.exists():
            try:
                shutil.rmtree(dir_path)
                print(f"已删除: {dir_path}")
            except Exception as e:
                print(f"删除 {dir_path} 时出错: {e}")
    print("清理完成。")

def get_platform_specific_args(platform_name, debug=False):
    """获取特定平台的PyInstaller参数"""
    args = []
    
    # 基本参数
    args.extend([
        '--clean',  # 清理临时文件
        '--onefile',  # 打包成单个可执行文件
        '--noconfirm',  # 不确认覆盖
        '--collect-all', 'autocoder',  # 收集所有autocoder相关模块
        '--collect-submodules', 'autocoder',  # 收集所有子模块
    ])
    
    # 调试模式
    if debug:
        args.extend(['--debug', 'all'])
    else:
        args.append('--log-level=INFO')
    
    # 添加数据文件和资源
    data_files = []
    
    # 检查README.md是否存在
    readme_path = ROOT_DIR / "README.md"
    if readme_path.exists():
        data_files.append((str(readme_path), '.'))
    
    # 检查templates目录是否存在
    templates_dir = ROOT_DIR / "src" / "autocoder" / "templates"
    if templates_dir.exists():
        data_files.append((str(templates_dir), 'autocoder/templates'))
    
    # 检查assets目录是否存在
    assets_dir = ROOT_DIR / "src" / "autocoder" / "assets"
    if assets_dir.exists():
        data_files.append((str(assets_dir), 'autocoder/assets'))
    
    # 添加所有数据文件
    for src, dest in data_files:
        args.extend(['--add-data', f'{src}{os.pathsep}{dest}'])
    
    # 收集项目中所有Python文件
    src_dir = ROOT_DIR / "src"
    if src_dir.exists():
        args.extend(['--add-data', f'{src_dir}{os.pathsep}src'])
    
    # 隐藏导入模块 - 确保所有依赖都被包含
    hidden_imports = [        
    ]
    
    for imp in hidden_imports:
        args.extend(['--hidden-import', imp])
    
    # 平台特定配置
    if platform_name == 'win':
        # Windows 特定配置
        win_args = []
        
        # 检查图标是否存在
        icon_path = ROOT_DIR / 'src' / 'autocoder' / 'assets' / 'icon.ico'
        if icon_path.exists():
            win_args.extend(['--icon', str(icon_path)])
        
        win_args.extend([
            '--console',  # 显示控制台窗口
            '--uac-admin',  # 请求管理员权限
        ])
        
        # 检查版本文件是否存在
        version_file = ROOT_DIR / 'version.txt'
        if version_file.exists():
            win_args.extend(['--version-file', str(version_file)])
            
        args.extend(win_args)
    elif platform_name == 'mac':
        # macOS 特定配置
        icon_path = ROOT_DIR / 'src' / 'autocoder' / 'assets' / 'icon.icns'
        if not icon_path.exists():
            icon_path = ROOT_DIR / 'src' / 'autocoder' / 'assets' / 'icon.png'
        
        # 只有当图标文件存在时才添加图标参数
        mac_args = []
        if icon_path.exists():
            mac_args.extend(['--icon', str(icon_path)])
            
        # 在macOS上，完全禁用代码签名
        mac_args.extend([
            '--osx-bundle-identifier', 'com.autocoder.app',
            '--disable-windowed-traceback',  # 禁用窗口化回溯
        ])
        
        args.extend(mac_args)
    elif platform_name == 'linux':
        # Linux 特定配置
        linux_args = ['--strip']  # 减小二进制文件大小
        
        # 检查图标是否存在
        icon_path = ROOT_DIR / 'src' / 'autocoder' / 'assets' / 'icon.png'
        if icon_path.exists():
            linux_args.extend(['--icon', str(icon_path)])
            
        args.extend(linux_args)
    
    return args

def collect_requirements():
    """收集项目的所有依赖包"""
    print("收集项目依赖...")
    requirements = []
    req_file = ROOT_DIR / "requirements.txt"
    
    if req_file.exists():
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # 移除版本信息，只保留包名
                    package = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                    if package:
                        requirements.append(package)
        print(f"从requirements.txt收集到{len(requirements)}个依赖包")
    else:
        print("警告: 未找到requirements.txt文件")
    
    return requirements

def build_installer(platform_name, target_name, debug=False):
    """为指定平台构建安装程序"""
    print(f"\n开始为 {PLATFORMS[platform_name]} 构建安装程序 {target_name}...")
    
    # 确保输出目录存在
    for directory in [BUILD_DIR, DIST_DIR, SPEC_DIR]:
        directory.mkdir(exist_ok=True)
    
    # 收集依赖包
    requirements = collect_requirements()
    
    # 检查运行时钩子文件
    runtime_hook_path = ROOT_DIR / "scripts" / "runtime_hook.py"
    runtime_hook_arg = None
    if runtime_hook_path.exists():
        runtime_hook_arg = str(runtime_hook_path)
    
    # 构建PyInstaller命令
    cmd = [
        'pyinstaller',
        '--name', target_name,
        '--workpath', str(BUILD_DIR / platform_name),
        '--specpath', str(SPEC_DIR),
        '--distpath', str(DIST_DIR / platform_name),
    ]
    
    # 添加运行时钩子
    if runtime_hook_arg:
        cmd.extend(['--runtime-hook', runtime_hook_arg])
    
    # 添加平台特定参数
    cmd.extend(get_platform_specific_args(platform_name, debug))
    
    # 添加主程序
    cmd.append(str(MAIN_APP))
    
    # 打印命令（调试用）
    print("执行命令:", ' '.join(cmd))
    
    # 执行构建命令
    try:
        subprocess.check_call(cmd, cwd=ROOT_DIR)
        
        # 获取生成的可执行文件路径
        output_file = DIST_DIR / platform_name / f"{target_name}{PLATFORM_EXT[platform_name]}"
        
        if output_file.exists():
            print(f"\n{PLATFORMS[platform_name]} 平台安装程序构建成功！")
            print(f"安装程序路径: {output_file}")
            print(f"文件大小: {output_file.stat().st_size / (1024*1024):.2f} MB")
        else:
            print(f"\n警告: 找不到生成的安装程序文件: {output_file}")
            
    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        sys.exit(1)

def create_runtime_hook():
    """创建运行时钩子脚本，确保所有依赖都被正确加载"""
    hook_path = ROOT_DIR / "scripts" / "runtime_hook.py"
    
    if not hook_path.exists():
        print("创建运行时钩子脚本...")
        hook_content = '''
# -*- coding: utf-8 -*-
# PyInstaller运行时钩子脚本
import os
import sys
import site
import importlib.util

def ensure_package_imported(package_name):
    """确保包被正确导入"""
    try:
        importlib.import_module(package_name)
        return True
    except ImportError:
        return False

# 添加打包后的目录到sys.path
def setup_environment():
    # 获取应用程序根目录
    if getattr(sys, 'frozen', False):
        # 运行在PyInstaller打包的环境中
        app_path = os.path.dirname(sys.executable)
    else:
        # 运行在普通Python环境中
        app_path = os.path.dirname(os.path.abspath(__file__))
    
    # 添加关键路径
    paths_to_add = [
        app_path,
        os.path.join(app_path, 'src'),
        os.path.join(app_path, 'autocoder'),
    ]
    
    for path in paths_to_add:
        if path not in sys.path and os.path.exists(path):
            sys.path.insert(0, path)

# 设置环境变量
os.environ['PYTHONPATH'] = os.pathsep.join(sys.path)

# 初始化环境
setup_environment()

# 预加载关键模块
key_packages = [
    'flask', 'jinja2', 'tiktoken', 'numpy'
]

for package in key_packages:
    ensure_package_imported(package)
'''
        with open(hook_path, 'w') as f:
            f.write(hook_content)
        print(f"运行时钩子脚本已创建: {hook_path}")
    else:
        print(f"运行时钩子脚本已存在: {hook_path}")

def main():
    parser = argparse.ArgumentParser(description='AutoCoder 安装程序打包工具')
    parser.add_argument('--platform', type=str, default='all', 
                      choices=['all', 'win', 'mac', 'linux', 'clean'],
                      help='目标平台: all, win, mac, linux, clean (默认: all)')
    parser.add_argument('--name', type=str, default='AutoCoderInstaller',
                      help='输出安装程序的名称 (默认: AutoCoderInstaller)')
    parser.add_argument('--clean', action='store_true',
                      help='清理构建文件和临时文件')
    parser.add_argument('--debug', action='store_true',
                      help='启用调试模式')
    parser.add_argument('--collect-deps', action='store_true',
                      help='自动收集所有依赖项')
    
    args = parser.parse_args()
    
    # 检查必要工具
    check_requirements()
    
    # 检测当前系统
    current_platform = None
    system = sys_platform.system()
    for key, value in PLATFORMS.items():
        if value == system:
            current_platform = key
            break
    
    if current_platform:
        print(f"当前系统: {PLATFORMS[current_platform]}")
    else:
        print(f"警告: 未识别的系统类型: {system}")
    
    # 清理构建文件
    if args.clean:
        clean()
        if args.platform == 'clean':  # 如果只是清理，不构建
            return
    
    # 确定目标平台
    if args.platform == 'all':
        platforms = ['win', 'mac', 'linux']
    else:
        platforms = [args.platform]
    
    # 创建运行时钩子
    create_runtime_hook()
    
    # 构建安装程序
    for platform_name in platforms:
        build_installer(platform_name, args.name, args.debug)
    
    print("\n所有平台安装程序构建完成！")
    print("注意: 生成的安装程序包含完整的Python解释器和所有依赖库")

if __name__ == "__main__":
    main()
