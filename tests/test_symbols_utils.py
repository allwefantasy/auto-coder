import unittest
from autocoder.index.symbols_utils import (
    extract_symbols,
    symbols_info_to_str,
    SymbolsInfo,
    SymbolType,
)


class TestSymbolsUtils(unittest.TestCase):
    def test_extract_symbols(self):
        text1 = """
用途：主要用于提供自动实现函数模板的功能。
函数：auto_implement_function_template
变量：a
类：
导入语句：import os^^import time^^from loguru import logger^^import byzerllm
"""
        info1 = extract_symbols(text1)
        self.assertEqual(info1.usage, "主要用于提供自动实现函数模板的功能。")
        self.assertEqual(info1.functions, ["auto_implement_function_template"])
        self.assertEqual(info1.variables, ["a"])
        self.assertEqual(info1.classes, [])
        self.assertEqual(
            info1.import_statements,
            [
                "import os",
                "import time",
                "from loguru import logger",
                "import byzerllm",
            ],
        )

        text2 = """
用途：主要用于自动编码器的索引管理和文件处理。
函数：_get_related_files, get_all_file_symbols, split_text_into_chunks, build_index_for_single_source, build_index, read_index, _get_meta_str, get_related_files, _query_index_with_thread, get_target_files_by_query, _get_target_files_by_query
变量：a
类：IndexItem, TargetFile, FileList, IndexManager  
导入语句：import os^^import json^^import time^^from typing import List, Dict, Any^^from datetime import datetime^^from autocoder.common import SourceCode, AutoCoderArgs
"""
        info2 = extract_symbols(text2)        
        self.assertEqual(info2.usage, "主要用于自动编码器的索引管理和文件处理。")
        self.assertEqual(
            info2.functions,
            [
                "_get_related_files",
                "get_all_file_symbols",
                "split_text_into_chunks",
                "build_index_for_single_source",
                "build_index",
                "read_index",
                "_get_meta_str",
                "get_related_files",
                "_query_index_with_thread",
                "get_target_files_by_query",
                "_get_target_files_by_query",
            ],
        )
        self.assertEqual(info2.variables, ["a"])
        self.assertEqual(
            info2.classes, ["IndexItem", "TargetFile", "FileList", "IndexManager"]
        )
        self.assertEqual(
            info2.import_statements,
            [
                "import os",
                "import json",
                "import time",
                "from typing import List, Dict, Any",
                "from datetime import datetime",
                "from autocoder.common import SourceCode, AutoCoderArgs",
            ],
        )

    def test_symbols_info_to_str(self):
        info = SymbolsInfo(
            usage="Test usage",
            functions=["func1", "func2"],
            variables=["var1", "var2"],
            classes=["Class1", "Class2"],
            import_statements=["import os", "from typing import List"],
        )

        result1 = symbols_info_to_str(info, [SymbolType.USAGE, SymbolType.FUNCTIONS])        
        self.assertEqual(result1, "usage：Test usage\nfunctions：func1,func2")

        result2 = symbols_info_to_str(
            info, [SymbolType.CLASSES, SymbolType.IMPORT_STATEMENTS]
        )
        self.assertEqual(
            result2,
            "classes：Class1,Class2\nimport_statements：import os^^from typing import List",
        )


if __name__ == "__main__":
    unittest.main()
