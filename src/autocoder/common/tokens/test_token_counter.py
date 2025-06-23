
"""
Token统计模块测试

测试TokenStatsCalculator的各种功能
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from autocoder.common.tokens.token_counter import (
    TokenStatsCalculator, 
    FileTokenStats, 
    DirectoryTokenStats
)


class TestTokenStatsCalculator:
    """Token统计计算器测试类"""

    def setup_method(self):
        """测试初始化"""
        self.calculator = TokenStatsCalculator()
        
        # 模拟tokenizer
        self.mock_tokenizer = Mock()
        self.mock_encoded = Mock()
        self.mock_encoded.ids = list(range(100))  # 模拟100个token
        self.mock_tokenizer.encode.return_value = self.mock_encoded

    def test_is_text_file_by_extension(self):
        """测试根据扩展名判断文本文件"""
        # 文本文件
        is_text, reason = self.calculator._is_text_file("test.py")
        assert is_text is True
        assert "文本文件扩展名" in reason
        
        # 二进制文件
        is_text, reason = self.calculator._is_text_file("image.jpg")
        assert is_text is False
        assert "二进制文件扩展名" in reason

    def test_is_text_file_by_special_name(self):
        """测试根据特殊文件名判断文本文件"""
        is_text, reason = self.calculator._is_text_file("Dockerfile")
        assert is_text is True
        assert "特殊文件名" in reason
        
        is_text, reason = self.calculator._is_text_file("README")
        assert is_text is True
        assert "特殊文件名" in reason

    @patch('autocoder.rag.variable_holder.VariableHolder')
    def test_count_file_tokens_success(self, mock_variable_holder):
        """测试成功统计文件token"""
        mock_variable_holder.TOKENIZER_MODEL = self.mock_tokenizer
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello world')")
            temp_file = f.name
        
        try:
            with patch('autocoder.common.files.read_file', return_value="print('hello world')"):
                stats = self.calculator.count_file_tokens(temp_file)
                
                assert stats.is_success
                assert stats.token_count == 100
                assert stats.error is None
                assert not stats.skipped
        finally:
            os.unlink(temp_file)

    @patch('autocoder.rag.variable_holder.VariableHolder')
    def test_count_file_tokens_nonexistent_file(self, mock_variable_holder):
        """测试统计不存在的文件"""
        mock_variable_holder.TOKENIZER_MODEL = self.mock_tokenizer
        
        stats = self.calculator.count_file_tokens("/nonexistent/file.py")
        
        assert not stats.is_success
        assert stats.token_count == 0
        assert "文件不存在" in stats.error

    @patch('autocoder.rag.variable_holder.VariableHolder')
    def test_count_file_tokens_binary_file(self, mock_variable_holder):
        """测试跳过二进制文件"""
        mock_variable_holder.TOKENIZER_MODEL = self.mock_tokenizer
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            temp_file = f.name
        
        try:
            stats = self.calculator.count_file_tokens(temp_file)
            
            assert not stats.is_success
            assert stats.skipped
            assert "非文本文件" in stats.skip_reason
        finally:
            os.unlink(temp_file)

    @patch('autocoder.rag.variable_holder.VariableHolder')
    def test_count_directory_tokens(self, mock_variable_holder):
        """测试统计目录token"""
        mock_variable_holder.TOKENIZER_MODEL = self.mock_tokenizer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            py_file = os.path.join(temp_dir, "test.py")
            txt_file = os.path.join(temp_dir, "test.txt")
            jpg_file = os.path.join(temp_dir, "image.jpg")
            
            with open(py_file, 'w') as f:
                f.write("print('hello')")
            with open(txt_file, 'w') as f:
                f.write("hello world")
            with open(jpg_file, 'wb') as f:
                f.write(b'\xff\xd8\xff\xe0')  # JPEG文件头
            
            with patch('autocoder.common.files.read_file', return_value="test content"):
                stats = self.calculator.count_directory_tokens(temp_dir)
                
                assert stats.total_files == 3
                assert stats.successful_files == 2  # py和txt文件
                assert stats.skipped_files == 1    # jpg文件
                assert stats.error_files == 0
                assert stats.total_tokens == 200   # 2个文件 * 100 tokens

    @patch('autocoder.rag.variable_holder.VariableHolder')
    def test_count_directory_tokens_with_pattern(self, mock_variable_holder):
        """测试使用正则模式统计目录"""
        mock_variable_holder.TOKENIZER_MODEL = self.mock_tokenizer
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            py_file = os.path.join(temp_dir, "test.py")
            txt_file = os.path.join(temp_dir, "test.txt")
            
            with open(py_file, 'w') as f:
                f.write("print('hello')")
            with open(txt_file, 'w') as f:
                f.write("hello world")
            
            with patch('autocoder.common.files.read_file', return_value="test content"):
                # 只匹配.py文件
                stats = self.calculator.count_directory_tokens(
                    temp_dir, 
                    file_pattern=r".*\.py$"
                )
                
                assert stats.total_files == 1
                assert stats.successful_files == 1
                assert stats.total_tokens == 100

    def test_get_summary_report(self):
        """测试生成摘要报告"""
        file_stats = [
            FileTokenStats("file1.py", 100),
            FileTokenStats("file2.py", 50),
            FileTokenStats("image.jpg", 0, skipped=True, skip_reason="二进制文件"),
            FileTokenStats("bad.py", 0, error="读取错误")
        ]
        
        directory_stats = DirectoryTokenStats(
            directory_path="/test/dir",
            total_tokens=150,
            file_stats=file_stats,
            total_files=4,
            successful_files=2,
            skipped_files=1,
            error_files=1
        )
        
        report = self.calculator.get_summary_report(directory_stats)
        
        assert "Token统计报告" in report
        assert "总tokens: 150" in report
        assert "总文件数: 4" in report
        assert "成功统计: 2" in report
        assert "跳过文件: 1" in report
        assert "错误文件: 1" in report

    def test_file_token_stats_properties(self):
        """测试FileTokenStats属性"""
        # 成功的统计
        success_stats = FileTokenStats("test.py", 100)
        assert success_stats.is_success
        assert "100 tokens" in str(success_stats)
        
        # 跳过的文件
        skipped_stats = FileTokenStats("test.jpg", 0, skipped=True, skip_reason="二进制文件")
        assert not skipped_stats.is_success
        assert "跳过" in str(skipped_stats)
        
        # 错误的文件
        error_stats = FileTokenStats("test.py", 0, error="读取失败")
        assert not error_stats.is_success
        assert "错误" in str(error_stats)

    def test_directory_token_stats_properties(self):
        """测试DirectoryTokenStats属性"""
        file_stats = [
            FileTokenStats("file1.py", 100),
            FileTokenStats("file2.py", 50),
            FileTokenStats("image.jpg", 0, skipped=True, skip_reason="二进制文件"),
            FileTokenStats("bad.py", 0, error="读取错误")
        ]
        
        stats = DirectoryTokenStats(
            directory_path="/test",
            total_tokens=150,
            file_stats=file_stats,
            total_files=4,
            successful_files=2,
            skipped_files=1,
            error_files=1
        )
        
        assert stats.success_rate == 0.5
        assert len(stats.get_files_by_status('success')) == 2
        assert len(stats.get_files_by_status('skipped')) == 1
        assert len(stats.get_files_by_status('error')) == 1
        assert len(stats.get_files_by_status('unknown')) == 0

    @patch('autocoder.rag.variable_holder.VariableHolder')
    def test_tokenizer_not_initialized(self, mock_variable_holder):
        """测试tokenizer未初始化的情况"""
        mock_variable_holder.TOKENIZER_MODEL = None
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello')")
            temp_file = f.name
        
        try:
            with patch('autocoder.common.files.read_file', return_value="test"):
                stats = self.calculator.count_file_tokens(temp_file)
                
                assert not stats.is_success
                assert "token统计失败" in stats.error
        finally:
            os.unlink(temp_file)


if __name__ == "__main__":
    # 简单的手动测试
    print("运行Token统计模块测试...")
    
    # 创建测试实例
    calculator = TokenStatsCalculator()
    
    # 测试文件类型判断
    print("\n=== 文件类型判断测试 ===")
    test_files = [
        "test.py", "image.jpg", "data.txt", "Dockerfile", 
        "README", "unknown_file", "script.sh"
    ]
    
    for file_path in test_files:
        is_text, reason = calculator._is_text_file(file_path)
        print(f"{file_path}: {'文本' if is_text else '非文本'} - {reason}")
    
    print("\nToken统计模块测试完成!")

