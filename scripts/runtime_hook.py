
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
    'flask', 'jinja2', 'tiktoken', 'numpy', 'transformers'
]

for package in key_packages:
    ensure_package_imported(package)
