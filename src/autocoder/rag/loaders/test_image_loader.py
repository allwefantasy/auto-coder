import os
import re
import tempfile

import pytest

from autocoder.rag.loaders.image_loader import ImageLoader, ReplaceInFileTool
from autocoder.utils.llms import get_single_llm

# 模拟一个简单的llm对象（避免测试中真实调用LLM）
class DummyLLM:
    def get_sub_client(self, name):
        return None

    def run(self, *args, **kwargs):
        return "dummy response"

@pytest.fixture(scope="module")
def dummy_llm():
    # 这里可以替换为真实llm，或Mock
    return DummyLLM()

def test_parse_diff_basic():
    diff = """
<<<<<<< SEARCH
foo
bar
=======
hello
world
>>>>>>> REPLACE
"""
    blocks = ImageLoader.parse_diff(diff)
    assert len(blocks) == 1
    search, replace = blocks[0]
    assert "foo" in search
    assert "hello" in replace

def test_extract_replace_in_file_tools():
    text = """
<replace_in_file>
<path>file1.py</path>
<diff>
<<<<<<< SEARCH
old content
=======
new content
>>>>>>> REPLACE
</diff>
</replace_in_file>

<replace_in_file>
<path>file2.py</path>
<diff>
<<<<<<< SEARCH
x=1
=======
x=2
>>>>>>> REPLACE
</diff>
</replace_in_file>
"""
    tools = ImageLoader.extract_replace_in_file_tools(text)
    assert len(tools) == 2
    assert tools[0].path == "file1.py"
    assert "old content" in tools[0].diff
    assert tools[1].path == "file2.py"
    assert "x=1" in tools[1].diff

def test_format_table_in_content_apply_diff(dummy_llm):
    # 模拟一个OCR文本和对应diff
    original = """这里是介绍
产品 价格 数量
苹果 5 10
香蕉 3 20
结束"""

    # 构造符合replace_in_file格式的llm返回
    llm_response = """
<replace_in_file>
<path>content</path>
<diff>
<<<<<<< SEARCH
产品 价格 数量
苹果 5 10
香蕉 3 20
=======
| 产品 | 价格 | 数量 |
| --- | --- | --- |
| 苹果 | 5 | 10 |
| 香蕉 | 3 | 20 |
>>>>>>> REPLACE
</diff>
</replace_in_file>
"""

    # 模拟调用llm时返回llm_response
    class FakeLLM:
        def get_sub_client(self, name):
            return None

        def run(self, *args, **kwargs):
            return llm_response

    fake_llm = FakeLLM()

    # patch _format_table 方法，让它直接返回llm_response
    import byzerllm

    class DummyPrompt:
        def __call__(self, *args, **kwargs):
            # 使其可装饰函数
            def decorator(func):
                class FakePromptWrapper:
                    def with_llm(self_inner, llm_obj):
                        class Runner:
                            def run(self_inner_inner, content):
                                return llm_response
                        return Runner()
                return FakePromptWrapper()
            return decorator

    orig_prompt = byzerllm.prompt
    byzerllm.prompt = DummyPrompt()

    try:
        formatted = ImageLoader.format_table_in_content(original, llm=fake_llm)
        assert "| 产品 | 价格 | 数量 |" in formatted
        assert "这里是介绍" in formatted
        assert "结束" in formatted
    finally:
        byzerllm.prompt = orig_prompt

def test_paddleocr_extract_text_type_error_fix(monkeypatch):
    """
    测试paddleocr_extract_text对异常结构的兼容性，模拟paddleocr.ocr返回非字符串结构
    """
    # 模拟PaddleOCR类
    class FakeOCR:
        def __init__(self, **kwargs):
            pass

        def ocr(self, file_path, **kwargs):
            # 模拟返回嵌套list，第二个元素是list而非str，之前会报错
            return [
                [
                    # page 1
                    [[ [0,0],[1,1] ], (["text_in_list"], 0.9)],
                    [[ [0,0],[1,1] ], ("normal text", 0.95)],
                ]
            ]
    # patch PaddleOCR
    import autocoder.rag.loaders.image_loader as ilmod
    monkeypatch.setattr(ilmod, "PaddleOCR", FakeOCR)

    # 创建临时文件模拟图片
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmpf:
        tmp_path = tmpf.name

    try:
        text = ImageLoader.paddleocr_extract_text(tmp_path)
        # 应该不会抛异常，且返回内容包含normal text和text_in_list
        assert "normal text" in text
        assert "text_in_list" in text
    finally:
        os.remove(tmp_path)

def test_paddlex_table_extract_markdown_no_paddlex(monkeypatch):
    # paddlex_module为None时应返回""
    import autocoder.rag.loaders.image_loader as ilmod
    monkeypatch.setattr(ilmod, "paddlex_module", None)
    md = ImageLoader.paddlex_table_extract_markdown("dummy_path.png")
    assert md == ""

def test_html_table_to_markdown_simple():
    html = """
<table>
<tr><th>头1</th><th>头2</th></tr>
<tr><td>数据1</td><td>数据2</td></tr>
<tr><td>数据3</td><td>数据4</td></tr>
</table>
"""
    md = ImageLoader.html_table_to_markdown(html)
    assert "| 头1 | 头2 |" in md
    assert "| 数据1 | 数据2 |" in md
    assert "| 数据3 | 数据4 |" in md

def test_extract_text_from_image_unknown_engine(dummy_llm):
    res = ImageLoader.extract_text_from_image("non_exist.png", dummy_llm, engine="xxx")
    assert res == ""

def test_image_to_markdown_creates_file(tmp_path, dummy_llm, monkeypatch):
    # 准备一个假图片文件
    imgfile = tmp_path / "testimg.png"
    imgfile.write_bytes(b"fake image content")

    # monkeypatch extract_text_from_image返回固定内容
    monkeypatch.setattr(ImageLoader, "extract_text_from_image", staticmethod(lambda *args, **kwargs: "# hello world"))

    md_content = ImageLoader.image_to_markdown(str(imgfile), dummy_llm, engine="vl")
    assert "# hello world" in md_content

    md_file = imgfile.with_suffix(".md")
    assert md_file.exists()
    assert "# hello world" in md_file.read_text()

if __name__ == "__main__":
    # 手动运行全部测试
    pytest.main([__file__])