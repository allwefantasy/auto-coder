import pytest
import tempfile
import shutil
import os
from unittest.mock import MagicMock, patch
from autocoder.common.pruner.context_pruner import PruneContext
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.sdk import get_llm,init_project_if_required


class TestPruneContextExtractStrategy:
    """Test suite for PruneContext extract strategy"""

    @pytest.fixture
    def temp_test_dir(self):
        """提供一个临时的、测试后自动清理的目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    

    @pytest.fixture
    def mock_args(self):
        """Create mock AutoCoderArgs for testing"""
        return AutoCoderArgs(
            source_dir=".",
            context_prune=True,
            context_prune_strategy="extract",
            conversation_prune_safe_zone_tokens=400,  # 设置较小的token限制以触发抽取逻辑
            context_prune_sliding_window_size=10,
            context_prune_sliding_window_overlap=2,
            query="如何实现加法和减法运算？"
        )

    @pytest.fixture
    def real_llm(self):
        """创建真实的LLM对象"""        
        llm = get_llm("v3_chat", product_mode="lite")
        return llm
        

    @pytest.fixture
    def pruner(self, mock_args, real_llm):
        """Create PruneContext instance for testing"""
        return PruneContext(max_tokens=1000, args=mock_args, llm=real_llm)

    @pytest.fixture
    def sample_file_sources(self, temp_test_dir):
        """Sample file sources for testing
        Creates a simulated project structure in the temporary directory
        """
        # 创建项目结构
        src_dir = os.path.join(temp_test_dir, "src")
        utils_dir = os.path.join(src_dir, "utils")
        os.makedirs(utils_dir, exist_ok=True)
        
        # 创建 __init__.py 文件使其成为有效的 Python 包
        with open(os.path.join(src_dir, "__init__.py"), "w") as f:
            f.write("# src package")
        with open(os.path.join(utils_dir, "__init__.py"), "w") as f:
            f.write("# utils package")
        
        # 创建数学工具模块
        math_utils_content = '''def add(a, b):
    """加法函数"""
    return a + b

def subtract(a, b):
    """减法函数"""
    return a - b

def multiply(a, b):
    """乘法函数"""
    return a * b

def divide(a, b):
    """除法函数"""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
'''
        math_utils_path = os.path.join(utils_dir, "math_utils.py")
        with open(math_utils_path, "w") as f:
            f.write(math_utils_content)
        
        # 创建字符串工具模块
        string_utils_content = '''def format_string(s):
    """格式化字符串"""
    return s.strip().lower()

def reverse_string(s):
    """反转字符串"""
    return s[::-1]

def count_characters(s):
    """计算字符数"""
    return len(s)
'''
        string_utils_path = os.path.join(utils_dir, "string_utils.py")
        with open(string_utils_path, "w") as f:
            f.write(string_utils_content)
        
        # 创建主程序文件
        main_content = '''from utils.math_utils import add, subtract
from utils.string_utils import format_string

def main():
    print("计算结果:", add(5, 3))
    print("格式化结果:", format_string("  Hello World  "))

if __name__ == "__main__":
    main()
'''
        main_path = os.path.join(src_dir, "main.py")
        with open(main_path, "w") as f:
            f.write(main_content)
        
        # 创建 README 文件
        readme_content = '''# 测试项目

这是一个用于测试的模拟项目结构。

## 功能

- 数学运算
- 字符串处理
'''
        readme_path = os.path.join(temp_test_dir, "README.md")
        with open(readme_path, "w") as f:
            f.write(readme_content)

        ## 初始化该项目
        os.chdir(temp_test_dir)
        init_project_if_required(target_dir=temp_test_dir)    
        
        # 返回与原来相同的 SourceCode 对象列表，但使用相对路径作为 module_name
        return [
            SourceCode(
                module_name="src/utils/math_utils.py",
                source_code=math_utils_content,
                tokens=500
            ),
            SourceCode(
                module_name="src/utils/string_utils.py",
                source_code=string_utils_content,
                tokens=300
            ),
            SourceCode(
                module_name="src/main.py",
                source_code=main_content,
                tokens=200
            )
        ]

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversations for testing"""
        return [
            {"role": "user", "content": "如何实现加法和减法运算？"},
            {"role": "assistant", "content": "我来帮你实现加法和减法运算。"}
        ]

    def test_extract_strategy_basic(self, pruner, sample_file_sources, sample_conversations):
        """测试extract策略的基本功能"""
        # Mock LLM响应，返回相关代码片段
        mock_response = """```json
[
    {"start_line": 1, "end_line": 7}
]
```"""        
            
        result = pruner.handle_overflow(
            file_sources=sample_file_sources,
            conversations=sample_conversations,
            strategy="extract"
        )
        
        # 验证结果
        assert isinstance(result, list), "应该返回文件列表"
        assert len(result) > 0, "应该至少返回一个文件"
        print(result)
        
        # 验证返回的是SourceCode对象
        for item in result:
            assert isinstance(item, SourceCode), "返回的应该是SourceCode对象"
            assert hasattr(item, 'module_name'), "SourceCode应该有module_name属性"
            assert hasattr(item, 'source_code'), "SourceCode应该有source_code属性"
   

    def test_sliding_window_split(self, pruner):
        """测试滑动窗口分割功能"""
        # 创建一个较长的内容用于测试
        content = "\n".join([f"line {i}: some content here" for i in range(1, 21)])
        
        # 测试滑动窗口分割
        chunks = pruner._split_content_with_sliding_window(
            content=content,
            window_size=5,
            overlap=2
        )
        
        # 验证结果
        assert isinstance(chunks, list), "应该返回chunk列表"
        assert len(chunks) > 0, "应该至少有一个chunk"
        
        # 验证chunk结构
        for chunk in chunks:
            assert isinstance(chunk, tuple), "每个chunk应该是元组"
            assert len(chunk) == 3, "每个chunk应该包含3个元素：(start_line, end_line, content)"
            start_line, end_line, chunk_content = chunk
            assert isinstance(start_line, int), "起始行号应该是整数"
            assert isinstance(end_line, int), "结束行号应该是整数"
            assert isinstance(chunk_content, str), "chunk内容应该是字符串"
            assert start_line <= end_line, "起始行号应该小于等于结束行号"

    def test_merge_overlapping_snippets(self, pruner):
        """测试重叠片段合并功能"""
        # 测试重叠片段
        snippets = [
            {"start_line": 1, "end_line": 5},
            {"start_line": 4, "end_line": 8},
            {"start_line": 10, "end_line": 15}
        ]
        
        merged = pruner._merge_overlapping_snippets(snippets)
        
        # 验证结果
        assert isinstance(merged, list), "应该返回片段列表"
        assert len(merged) == 2, "应该合并为2个片段"
        
        # 验证合并结果
        assert merged[0]["start_line"] == 1, "第一个片段起始行应该是1"
        assert merged[0]["end_line"] == 8, "第一个片段结束行应该是8"
        assert merged[1]["start_line"] == 10, "第二个片段起始行应该是10"
        assert merged[1]["end_line"] == 15, "第二个片段结束行应该是15"

    def test_build_snippet_content(self, pruner):
        """测试构建片段内容功能"""
        full_content = """def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b"""
        
        snippets = [
            {"start_line": 1, "end_line": 2},
            {"start_line": 4, "end_line": 5}
        ]
        
        result = pruner._build_snippet_content("test.py", full_content, snippets)
        
        # 验证结果
        assert isinstance(result, str), "应该返回字符串"
        assert "Snippets:" in result, "应该包含Snippets标题"
        assert "def add(a, b):" in result, "应该包含add函数"
        assert "def subtract(a, b):" in result, "应该包含subtract函数"

    def test_count_tokens_method(self, pruner, sample_file_sources):
        """测试token计数方法"""
        with patch('autocoder.rag.token_counter.count_tokens') as mock_count:
            mock_count.return_value = 100
            
            total_tokens, sources = pruner._count_tokens(sample_file_sources)
            
            # 验证结果
            assert isinstance(total_tokens, int), "总token数应该是整数"
            assert isinstance(sources, list), "应该返回源码列表"
            assert len(sources) == len(sample_file_sources), "源码数量应该一致"

    def test_invalid_strategy(self, pruner, sample_file_sources, sample_conversations):
        """测试无效策略处理"""
        with pytest.raises(ValueError) as exc_info:
            pruner.handle_overflow(
                file_sources=sample_file_sources,
                conversations=sample_conversations,
                strategy="invalid_strategy"
            )
        
        assert "无效策略" in str(exc_info.value), "应该抛出无效策略错误"

    def test_empty_file_sources(self, pruner, sample_conversations):
        """测试空文件源列表"""
        result = pruner.handle_overflow(
            file_sources=[],
            conversations=sample_conversations,
            strategy="extract"
        )
        
        assert isinstance(result, list), "应该返回列表"
        assert len(result) == 0, "空输入应该返回空结果"

    @patch('autocoder.rag.token_counter.count_tokens')
    def test_within_token_limit(self, mock_count, pruner, sample_file_sources, sample_conversations):
        """测试在token限制内的情况"""
        # 设置token计数低于限制
        mock_count.return_value = 100
        
        result = pruner.handle_overflow(
            file_sources=sample_file_sources,
            conversations=sample_conversations,
            strategy="extract"
        )
        
        # 验证结果：应该返回原始文件，因为没有超出限制
        assert len(result) == len(sample_file_sources), "在限制内应该返回所有文件"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
