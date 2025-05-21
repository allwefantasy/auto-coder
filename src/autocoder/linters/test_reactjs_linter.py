import os
import pytest
import json
from unittest.mock import patch, MagicMock
from autocoder.linters.reactjs_linter import ReactJSLinter

# python -m pytest src/autocoder/linters/test_reactjs_linter.py::TestReactJSLinter::test_lint_real_file -v -s
class TestReactJSLinter:
    """测试ReactJSLinter类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.linter = ReactJSLinter(verbose=True)
    
    def test_lint_file_nonexistent_file(self):
        """测试不存在的文件"""
        result = self.linter.lint_file("nonexistent_file.jsx")
        
        assert result['success'] == False
        assert "不存在" in result.get('error', '') or "does not exist" in result.get('error', '')
    
    def test_lint_file_unsupported_file(self):
        """测试不支持的文件类型"""
        # 创建一个临时文件
        with open("temp.txt", "w") as f:
            f.write("这不是React文件")
        
        try:
            result = self.linter.lint_file("temp.txt")
            
            assert result['success'] == False
            assert "不支持" in result.get('error', '') or "Unsupported" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.txt"):
                os.remove("temp.txt")
    
    @patch.object(ReactJSLinter, '_check_dependencies')
    def test_lint_file_missing_dependencies(self, mock_check):
        """测试缺少依赖项的情况"""
        # 模拟依赖检查失败
        mock_check.return_value = False
        
        # 创建一个临时React文件
        with open("temp.jsx", "w") as f:
            f.write("import React from 'react';\nfunction App() { return <div>Hello</div>; }")
        
        try:
            result = self.linter.lint_file("temp.jsx")
            
            assert result['success'] == False
            assert "依赖" in result.get('error', '') or "dependencies" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.jsx"):
                os.remove("temp.jsx")
    
    @patch.object(ReactJSLinter, '_detect_file_type')
    def test_lint_file_not_react_file(self, mock_detect):
        """测试非React文件"""
        # 模拟文件类型检测失败
        mock_detect.return_value = False
        
        # 创建一个临时JS文件
        with open("temp.js", "w") as f:
            f.write("function hello() { console.log('Hello'); }")
        
        try:
            result = self.linter.lint_file("temp.js")
            
            assert result['success'] == False
            assert "Not a React file" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.js"):
                os.remove("temp.js")
    
    @patch.object(ReactJSLinter, '_check_dependencies')
    @patch.object(ReactJSLinter, '_detect_file_type')
    @patch.object(ReactJSLinter, '_install_eslint_if_needed')
    @patch('subprocess.run')
    def test_lint_file_successful(self, mock_run, mock_install, mock_detect, mock_check):
        """测试成功的lint过程"""
        # 模拟依赖检查成功
        mock_check.return_value = True
        # 模拟文件类型检测成功
        mock_detect.return_value = True
        # 模拟安装ESLint成功
        mock_install.return_value = True
        
        # 模拟subprocess.run的结果
        mock_process = MagicMock()
        mock_process.stdout = json.dumps([
            {
                'filePath': os.path.abspath('test.jsx'),
                'errorCount': 1,
                'warningCount': 2,
                'messages': [
                    {
                        'line': 10,
                        'column': 5,
                        'severity': 2,
                        'message': '未使用的变量',
                        'ruleId': 'no-unused-vars'
                    },
                    {
                        'line': 15,
                        'column': 1,
                        'severity': 1,
                        'message': '缺少分号',
                        'ruleId': 'semi'
                    },
                    {
                        'line': 20,
                        'column': 10,
                        'severity': 1,
                        'message': '建议使用解构赋值',
                        'ruleId': 'prefer-destructuring'
                    }
                ]
            }
        ])
        mock_run.return_value = mock_process
        
        # 创建一个临时React文件
        with open("test.jsx", "w") as f:
            f.write("import React from 'react';\nfunction App() { return <div>Hello</div>; }")
        
        try:
            result = self.linter.lint_file("test.jsx")
            
            assert result['success'] == True
            assert result['framework'] == 'reactjs'
            assert result['files_analyzed'] == 1
            assert result['error_count'] == 1
            assert result['warning_count'] == 2
            assert len(result['issues']) == 3
        finally:
            # 清理
            if os.path.exists("test.jsx"):
                os.remove("test.jsx")
    
    # python -m pytest src/autocoder/linters/test_reactjs_linter.py::TestReactJSLinter::test_lint_real_file -v -s
    @pytest.mark.integration
    def test_lint_real_file(self):
        """测试对实际文件的lint功能"""
        # 检查是否有React示例文件可用        
        file_path = "/Users/allwefantasy/projects/auto-coder.web/frontend/src/components/Sidebar/ChatPanel.tsx"                
        
        # 执行lint操作
        result = self.linter.lint_file(file_path)
        
        # 基本断言
        assert 'success' in result
        assert 'framework' in result
        assert 'files_analyzed' in result
        
        # 打印完整的lint结果
        print("\n==== Lint结果概述 ====")
        print(f"文件: {file_path}")
        print(f"成功: {result.get('success', False)}")
        if 'error' in result:
            print(f"错误: {result['error']}")
        else:
            print(f"错误数: {result.get('error_count', 0)}")
            print(f"警告数: {result.get('warning_count', 0)}")
            print(f"问题总数: {len(result.get('issues', []))}")
        
        print("\n==== 详细问题列表 ====")
        if not result.get('issues', []):
            print("没有发现问题或执行失败！")
        else:
            for i, issue in enumerate(result['issues'], 1):
                print(f"\n问题 #{i}:")
                print(f"  文件: {issue['file']}")
                print(f"  位置: 第{issue['line']}行, 第{issue['column']}列")
                print(f"  严重性: {issue['severity']}")
                print(f"  信息: {issue['message']}")
                print(f"  规则: {issue['rule']}")
                
        # 可选：打印完整的JSON格式结果
        print("\n==== 完整JSON结果 ====")
        print(json.dumps(result, indent=2, ensure_ascii=False)) 