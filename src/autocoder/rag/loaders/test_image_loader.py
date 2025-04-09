import os
import unittest
from autocoder.rag.loaders.image_loader import ImageLoader, ReplaceInFileTool
from autocoder.utils.llms import get_single_llm

class TestImageLoader(unittest.TestCase):

    def setUp(self):
        # 准备一个简单的OCR文本示例
        self.simple_ocr_text = """
产品名称 
价格 
库存
苹果手机 
8999 352
华为平板 
4599 
128
小米电视 
3299 
89
        """.strip()

        # 初始化一个轻量的llm（可以根据环境调整）
        try:
            self.llm = get_single_llm("quasar-alpha", product_mode="lite")
        except Exception:
            self.llm = None  # 如果llm不可用，则部分测试跳过

    def test_parse_diff(self):
        diff_text = """
hello
world
hi
earth
baz
qux