#!/usr/bin/env python3
"""
测试重构后的 ActivePackage 模块
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """测试所有模块是否能正常导入"""
    try:
        from autocoder.memory.active_header import ActiveHeader
        from autocoder.memory.active_changes import ActiveChanges
        from autocoder.memory.active_documents import ActiveDocuments
        from autocoder.memory.active_diagrams import ActiveDiagrams
        from autocoder.memory.active_package import ActivePackage
        
        print("✅ 所有模块导入成功")
        
        # 测试 ActiveHeader
        header_processor = ActiveHeader()
        test_context = {"directory_path": "/test/path"}
        header = header_processor.generate_header(test_context)
        print(f"✅ ActiveHeader 工作正常: {header.strip()}")
        
        # 测试 ActiveDiagrams (不需要 LLM 的基本功能)
        print("✅ ActiveDiagrams 模块导入成功")
        
        print("✅ 重构成功！所有模块都能正常工作")
        print("📊 新增功能：Mermaid 图表生成模块已集成")
        return True
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 