import os
import pytest
import json
from unittest.mock import patch, MagicMock
from autocoder.linters.python_linter import PythonLinter

class TestPythonLinter:
    """测试PythonLinter类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.linter = PythonLinter(verbose=True)
    
    def test_lint_file_nonexistent_file(self):
        """测试不存在的文件"""
        result = self.linter.lint_file("nonexistent_file.py")
        
        assert result['success'] == False
        assert "不存在" in result.get('error', '') or "does not exist" in result.get('error', '')
    
    def test_lint_file_unsupported_file(self):
        """测试不支持的文件类型"""
        # 创建一个临时文件
        with open("temp.txt", "w") as f:
            f.write("这不是Python文件")
        
        try:
            result = self.linter.lint_file("temp.txt")
            
            assert result['success'] == False
            assert "不支持" in result.get('error', '') or "Unsupported" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.txt"):
                os.remove("temp.txt")
    
    @patch.object(PythonLinter, '_check_dependencies')
    @patch.object(PythonLinter, '_install_dependencies_if_needed')
    def test_lint_file_missing_dependencies(self, mock_install, mock_check):
        """测试缺少依赖项的情况"""
        # 模拟依赖检查失败
        mock_check.return_value = False
        # 模拟安装依赖失败
        mock_install.return_value = False
        
        # 创建一个临时Python文件
        with open("temp.py", "w") as f:
            f.write("print('Hello, World!')")
        
        try:
            result = self.linter.lint_file("temp.py")
            
            assert result['success'] == False
            assert "依赖" in result.get('error', '') or "dependencies" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.py"):
                os.remove("temp.py")
    
    @patch.object(PythonLinter, '_check_dependencies')
    @patch.object(PythonLinter, '_run_pylint')
    def test_lint_file_successful(self, mock_pylint, mock_check):
        """测试成功的lint过程"""
        # 模拟依赖检查成功
        mock_check.return_value = True
        
        # 模拟pylint结果
        mock_pylint.return_value = {
            'error_count': 1,
            'warning_count': 2,
            'issues': [
                {
                    'file': 'test.py',
                    'line': 10,
                    'column': 5,
                    'severity': 'error',
                    'message': '未定义变量',
                    'rule': 'undefined-variable',
                    'tool': 'pylint'
                },
                {
                    'file': 'test.py',
                    'line': 15,
                    'column': 1,
                    'severity': 'warning',
                    'message': '不必要的空行',
                    'rule': 'trailing-whitespace',
                    'tool': 'pylint'
                }
            ]
        }
        
        # 创建一个临时Python文件
        with open("test.py", "w") as f:
            f.write("print('Hello, World!')")
        
        try:
            result = self.linter.lint_file("test.py")
            
            assert result['success'] == True
            assert result['language'] == 'python'
            assert result['files_analyzed'] == 1
            assert result['error_count'] == 1
            assert result['warning_count'] == 2  # 只有pylint的警告
            assert len(result['issues']) == 2  # 总共2个问题
        finally:
            # 清理
            if os.path.exists("test.py"):
                os.remove("test.py")
    
    # python -m pytest src/autocoder/linters/test_python_linter.py::TestPythonLinter::test_lint_real_file -v -s
    @pytest.mark.integration
    def test_lint_real_file(self):
        """测试对实际文件的lint功能"""
        # 实际存在的Python文件路径
        file_path = "/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/agent/agentic_edit_tools/read_file_tool_resolver.py"
        
        # 检查文件是否存在，如果不存在则跳过测试
        if not os.path.exists(file_path):
            pytest.skip(f"测试文件 {file_path} 不存在")
        
        # 执行lint操作
        result = self.linter.lint_file(file_path)
        
        # 基本断言
        assert result['success'] == True
        assert result['language'] == 'python'
        assert result['files_analyzed'] == 1
        
        # 打印完整的lint结果
        print("\n==== Lint结果概述 ====")
        print(f"文件: {file_path}")
        print(f"错误数: {result['error_count']}")
        print(f"警告数: {result['warning_count']}")
        print(f"问题总数: {len(result['issues'])}")
        
        print("\n==== 详细问题列表 ====")
        if not result['issues']:
            print("没有发现问题！")
        else:
            for i, issue in enumerate(result['issues'], 1):
                print(f"\n问题 #{i}:")
                print(f"  文件: {issue['file']}")
                print(f"  位置: 第{issue['line']}行, 第{issue['column']}列")
                print(f"  严重性: {issue['severity']}")
                print(f"  信息: {issue['message']}")
                print(f"  规则: {issue['rule']}")
                print(f"  工具: {issue['tool']}")
                
        # 可选：打印完整的JSON格式结果
        print("\n==== 完整JSON结果 ====")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 验证结果中包含issues字段，且为列表类型
        assert 'issues' in result
        assert isinstance(result['issues'], list)
        
        # 如果有issues，验证其结构
        if result['issues']:
            issue = result['issues'][0]
            assert 'file' in issue
            assert 'line' in issue
            assert 'severity' in issue
            assert 'message' in issue
            assert 'rule' in issue
            assert 'tool' in issue 