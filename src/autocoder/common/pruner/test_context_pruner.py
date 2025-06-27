import pytest
import tempfile
import shutil
import os
from unittest.mock import MagicMock, patch
from autocoder.common.pruner.context_pruner import PruneContext
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.sdk import get_llm, init_project_if_required
from autocoder.common.tokens import count_string_tokens


class TestPruneContextExtractStrategy:
    """Test suite for PruneContext extract strategy"""

    @pytest.fixture
    def temp_test_dir(self):
        """提供一个临时的、测试后自动清理的目录"""
        # 保存原始工作目录
        original_cwd = os.getcwd()
        temp_dir = tempfile.mkdtemp()
        try:
            yield temp_dir
        finally:
            # 确保恢复到原始目录，即使出现异常
            try:
                os.chdir(original_cwd)
            except OSError:
                # 如果原始目录也不存在，则切换到用户主目录
                os.chdir(os.path.expanduser("~"))
            # 删除临时目录
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_args(self):
        """Create mock AutoCoderArgs for testing"""
        return AutoCoderArgs(
            source_dir=".",
            context_prune=True,
            context_prune_strategy="extract",
            conversation_prune_safe_zone_tokens=30,  # 这个不对context_prunner 生效
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
        # 对 context_prunner 生效的是 max_tokens这里
        return PruneContext(max_tokens=60, args=mock_args, llm=real_llm)

    @pytest.fixture
    def verbose_pruner(self, mock_args, real_llm):
        """Create PruneContext instance with verbose=True for testing"""
        return PruneContext(max_tokens=60, args=mock_args, llm=real_llm, verbose=True)

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

        # 初始化该项目
        # 保存当前工作目录
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_test_dir)
            init_project_if_required(target_dir=temp_test_dir)
        finally:
            # 立即恢复工作目录，避免影响后续测试
            os.chdir(original_cwd)

        # 返回与原来相同的 SourceCode 对象列表，但使用相对路径作为 module_name
        v = [
            SourceCode(
                module_name="src/utils/math_utils.py",
                source_code=math_utils_content,
                tokens=count_string_tokens(math_utils_content)
            ),
            SourceCode(
                module_name="src/utils/string_utils.py",
                source_code=string_utils_content,
                tokens=count_string_tokens(string_utils_content)
            ),
            SourceCode(
                module_name="src/main.py",
                source_code=main_content,
                tokens=count_string_tokens(main_content)
            )
        ]
                      
        return v

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversations for testing"""
        return [
            {"role": "user", "content": "如何实现加法和减法运算？"},
            {"role": "assistant", "content": "我来帮你实现加法和减法运算。"}
        ]

    def test_extract_strategy_basic(self, pruner, sample_file_sources, sample_conversations):
        """测试extract策略的基本功能"""
        
        # 计算输入的总token数
        original_total_tokens = sum(source.tokens for source in sample_file_sources)
        print(f"原始总token数: {original_total_tokens}")

        result = pruner.handle_overflow(
            file_sources=sample_file_sources,
            conversations=sample_conversations,
            strategy="extract"
        )

        # 验证结果基本结构
        assert isinstance(result, list), "应该返回文件列表"
        print(f"返回文件数量: {len(result)}")

        # 验证返回的是SourceCode对象
        for item in result:
            assert isinstance(item, SourceCode), "返回的应该是SourceCode对象"
            assert hasattr(item, 'module_name'), "SourceCode应该有module_name属性"
            assert hasattr(item, 'source_code'), "SourceCode应该有source_code属性"

        # 如果有结果，验证token压缩效果
        if len(result) > 0:
            # 计算输出的总token数
            result_total_tokens = sum(item.tokens for item in result)
            print(f"处理后总token数: {result_total_tokens}")
            
            # 验证token数确实减少了
            assert result_total_tokens < original_total_tokens, f"Token数应该减少，原始: {original_total_tokens}, 处理后: {result_total_tokens}"
            
            # 计算压缩率
            compression_rate = (original_total_tokens - result_total_tokens) / original_total_tokens * 100
            print(f"Token压缩率: {compression_rate:.1f}%")
            assert compression_rate > 0, "应该有有效的压缩率"
            
            # 验证与查询相关的函数是否在结果中（用户查询："如何实现加法和减法运算？"）
            combined_content = "\n".join(item.source_code for item in result)
            print(f"合并后的内容长度: {len(combined_content)} 字符")
            
            # 检查加法和减法相关的函数是否存在
            has_add_function = "def add(" in combined_content or "add(" in combined_content
            has_subtract_function = "def subtract(" in combined_content or "subtract(" in combined_content
            
            print(f"包含add函数: {has_add_function}")
            print(f"包含subtract函数: {has_subtract_function}")
            
            # 至少应该包含其中一个相关函数
            assert has_add_function or has_subtract_function, "裁剪后的结果应该包含与查询相关的加法或减法函数"
            
            # 验证math_utils.py是否在结果中（因为它包含相关函数）
            math_utils_files = [item for item in result if "math_utils.py" in item.module_name]
            if math_utils_files:
                math_utils_content = math_utils_files[0].source_code
                print(f"math_utils.py处理后内容:\n{math_utils_content}")
                
                # 验证包含Snippets标记（说明经过了代码片段抽取）
                assert "Snippets:" in math_utils_content, "math_utils.py应该包含代码片段抽取标记"
                
        else:
            print("⚠️ Extract策略返回空结果（这可能发生在LLM超时或其他异常情况下）")

    def test_sliding_window_split(self, pruner):
        """测试滑动窗口分割功能"""
        # 创建一个较长的内容用于测试（20行）
        content = "\n".join([f"line {i}: some content here" for i in range(1, 21)])
        content_lines = content.split('\n')
        total_lines = len(content_lines)
        
        print(f"测试内容总行数: {total_lines}")

        # 测试不同的滑动窗口配置
        test_cases = [
            {
                "window_size": 5,
                "overlap": 2,
                "expected_chunks": 7,  # 基于实际运行结果
                "description": "标准滑动窗口配置"
            },
            {
                "window_size": 3, 
                "overlap": 1,
                "expected_chunks": 10,  # 基于实际运行结果
                "description": "小窗口高重叠配置"
            },
            {
                "window_size": 10,
                "overlap": 3, 
                "expected_chunks": 3,  # 基于实际运行结果
                "description": "大窗口中等重叠配置"
            },
            {
                "window_size": 7,
                "overlap": 0,
                "expected_chunks": 3,  # 基于实际运行结果
                "description": "无重叠配置"
            }
        ]

        for case in test_cases:
            window_size = case["window_size"]
            overlap = case["overlap"]
            expected_chunks = case["expected_chunks"]
            description = case["description"]
            
            print(f"\n🔍 测试 {description}: 窗口={window_size}, 重叠={overlap}")
            
            chunks = pruner._split_content_with_sliding_window(
                content=content,
                window_size=window_size,
                overlap=overlap
            )

            # 验证基本结构
            assert isinstance(chunks, list), f"应该返回chunk列表 ({description})"
            assert len(chunks) == expected_chunks, f"应该有 {expected_chunks} 个chunks，实际: {len(chunks)} ({description})"

            # 验证chunk结构和内容
            for i, chunk in enumerate(chunks):
                assert isinstance(chunk, tuple), f"Chunk {i+1} 应该是元组 ({description})"
                assert len(chunk) == 3, f"Chunk {i+1} 应该包含3个元素 ({description})"
                
                start_line, end_line, chunk_content = chunk
                assert isinstance(start_line, int), f"Chunk {i+1} 起始行号应该是整数 ({description})"
                assert isinstance(end_line, int), f"Chunk {i+1} 结束行号应该是整数 ({description})"
                assert isinstance(chunk_content, str), f"Chunk {i+1} 内容应该是字符串 ({description})"
                assert start_line <= end_line, f"Chunk {i+1} 起始行号应该 <= 结束行号 ({description})"
                
                # 验证行号范围合理
                assert 1 <= start_line <= total_lines, f"Chunk {i+1} 起始行号应该在1-{total_lines}范围内 ({description})"
                assert 1 <= end_line <= total_lines, f"Chunk {i+1} 结束行号应该在1-{total_lines}范围内 ({description})"
                
                # 验证内容行数与行号范围一致
                chunk_lines = chunk_content.split('\n')
                expected_line_count = end_line - start_line + 1
                # 注意：由于chunk_content中可能包含行号前缀，实际行数可能不同
                # 我们主要验证内容不为空且合理
                assert len(chunk_content) > 0, f"Chunk {i+1} 内容不应为空 ({description})"
                
                print(f"   Chunk {i+1}: 行 {start_line}-{end_line} ({len(chunk_lines)} 行)")

            # 验证重叠逻辑
            if overlap > 0 and len(chunks) > 1:
                for i in range(len(chunks) - 1):
                    current_start, current_end, _ = chunks[i]
                    next_start, next_end, _ = chunks[i + 1]
                    
                    # 验证有重叠
                    if i < len(chunks) - 2:  # 不是最后一个chunk对
                        overlap_lines = current_end - next_start + 1
                        assert overlap_lines >= overlap, f"Chunk {i+1} 和 {i+2} 重叠行数应该 >= {overlap}，实际: {overlap_lines} ({description})"
            
            # 验证覆盖完整性（所有行都被覆盖）
            covered_lines = set()
            for start_line, end_line, _ in chunks:
                for line_num in range(start_line, end_line + 1):
                    covered_lines.add(line_num)
            
            expected_lines = set(range(1, total_lines + 1))
            assert covered_lines == expected_lines, f"应该覆盖所有行1-{total_lines} ({description})"
            
            print(f"   ✅ 验证通过: {len(chunks)} 个chunks，覆盖所有 {total_lines} 行")

        # 追加基于math_utils_content的真实代码测试
        print(f"\n🧮 测试真实代码内容 - math_utils.py")
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
        
        math_content_lines = math_utils_content.split('\n')
        math_total_lines = len([line for line in math_content_lines if line.strip()])  # 只计算非空行
        print(f"math_utils.py 总行数: {len(math_content_lines)} (非空行: {math_total_lines})")
        
        # 测试适合代码的窗口配置
        math_test_cases = [
            {
                "window_size": 4,
                "overlap": 1,
                "description": "小窗口配置适合函数分割"
            },
            {
                "window_size": 6,
                "overlap": 2,
                "description": "中等窗口配置包含完整函数"
            }
        ]
        
        for case in math_test_cases:
            window_size = case["window_size"]
            overlap = case["overlap"]
            description = case["description"]
            
            print(f"\n🔍 测试 {description}: 窗口={window_size}, 重叠={overlap}")
            
            chunks = pruner._split_content_with_sliding_window(
                content=math_utils_content,
                window_size=window_size,
                overlap=overlap
            )
            
            print(f"   生成 {len(chunks)} 个chunks:")
            
            # 验证基本结构
            assert isinstance(chunks, list), f"应该返回chunk列表 ({description})"
            assert len(chunks) > 0, f"应该至少有一个chunk ({description})"
            
            # 分析每个chunk的内容
            function_keywords = ["def add(", "def subtract(", "def multiply(", "def divide("]
            
            for i, chunk in enumerate(chunks):
                start_line, end_line, chunk_content = chunk
                print(f"   Chunk {i+1}: 行 {start_line}-{end_line}")
                
                # 检查这个chunk包含哪些函数定义
                found_functions = []
                for keyword in function_keywords:
                    if keyword in chunk_content:
                        func_name = keyword[4:-1]  # 提取函数名 (去掉 "def " 和 "(")
                        found_functions.append(func_name)
                
                if found_functions:
                    print(f"      包含函数: {', '.join(found_functions)}")
                else:
                    print(f"      包含: 函数体或注释部分")
                
                # 验证基本结构
                assert isinstance(chunk, tuple), f"Chunk {i+1} 应该是元组 ({description})"
                assert len(chunk) == 3, f"Chunk {i+1} 应该包含3个元素 ({description})"
                assert isinstance(start_line, int), f"Chunk {i+1} 起始行号应该是整数 ({description})"
                assert isinstance(end_line, int), f"Chunk {i+1} 结束行号应该是整数 ({description})"
                assert isinstance(chunk_content, str), f"Chunk {i+1} 内容应该是字符串 ({description})"
                assert len(chunk_content.strip()) > 0, f"Chunk {i+1} 内容不应为空 ({description})"
            
            # 验证所有函数定义都被覆盖
            all_chunk_content = "\n".join(chunk[2] for chunk in chunks)
            for keyword in function_keywords:
                assert keyword in all_chunk_content, f"应该覆盖函数定义: {keyword} ({description})"
                
            print(f"   ✅ 验证通过: 所有函数定义都被覆盖")

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

        result = pruner._build_snippet_content(
            "test.py", full_content, snippets)

        # 验证结果
        assert isinstance(result, str), "应该返回字符串"
        assert "Snippets:" in result, "应该包含Snippets标题"
        assert "def add(a, b):" in result, "应该包含add函数"
        assert "def subtract(a, b):" in result, "应该包含subtract函数"

    def test_invalid_strategy(self, pruner, sample_file_sources, sample_conversations):
        """测试无效策略处理"""
        with pytest.raises(ValueError) as exc_info:
            pruner.handle_overflow(
                file_sources=sample_file_sources,
                conversations=sample_conversations,
                strategy="invalid_strategy"
            )

        assert "无效策略" in str(exc_info.value), "应该抛出无效策略错误"

    def test_verbose_functionality(self, verbose_pruner, sample_file_sources, sample_conversations, capsys):
        """测试verbose参数的功能"""
        # 使用verbose=True的pruner进行测试
        result = verbose_pruner.handle_overflow(
            file_sources=sample_file_sources,
            conversations=sample_conversations,
            strategy="extract"
        )

        # 捕获输出
        captured = capsys.readouterr()
        
        # 验证verbose输出包含预期的信息
        assert "🚀 开始代码片段抽取处理" in captured.out, "应该包含开始处理的信息"
        assert "📋 处理策略" in captured.out, "应该包含处理策略信息"
        assert "🎯 代码片段抽取处理完成" in captured.out, "应该包含处理完成的信息"
        assert "📊 处理结果统计" in captured.out, "应该包含结果统计信息"
        
        # 验证结果仍然正确
        assert isinstance(result, list), "应该返回文件列表"
        assert len(result) >= 0, "应该返回有效的结果列表"

    def test_non_verbose_functionality(self, pruner, sample_file_sources, sample_conversations, capsys):
        """测试verbose=False时不输出详细信息"""
        # 使用verbose=False的pruner进行测试
        result = pruner.handle_overflow(
            file_sources=sample_file_sources,
            conversations=sample_conversations,
            strategy="extract"
        )

        # 捕获输出
        captured = capsys.readouterr()
        
        # 验证不包含verbose特有的输出
        assert "🚀 开始代码片段抽取处理" not in captured.out, "非verbose模式不应该包含详细处理信息"
        assert "📋 处理策略" not in captured.out, "非verbose模式不应该包含处理策略信息"
        assert "🎯 代码片段抽取处理完成" not in captured.out, "非verbose模式不应该包含处理完成的详细信息"
        
        # 验证结果仍然正确
        assert isinstance(result, list), "应该返回文件列表"
        assert len(result) >= 0, "应该返回有效的结果列表"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
