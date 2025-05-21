import os
import pytest
import json
from unittest.mock import patch, MagicMock
from autocoder.linters.vue_linter import VueLinter

class TestVueLinter:
    """测试VueLinter类"""
    
    def setup_method(self):
        """每个测试方法前的设置"""
        self.linter = VueLinter(verbose=True)
    
    def test_lint_file_nonexistent_file(self):
        """测试不存在的文件"""
        result = self.linter.lint_file("nonexistent_file.vue")
        
        assert result['success'] == False
        assert "不存在" in result.get('error', '') or "does not exist" in result.get('error', '')
    
    def test_lint_file_unsupported_file(self):
        """测试不支持的文件类型"""
        # 创建一个临时文件
        with open("temp.txt", "w") as f:
            f.write("这不是Vue文件")
        
        try:
            result = self.linter.lint_file("temp.txt")
            
            assert result['success'] == False
            assert "不支持" in result.get('error', '') or "Unsupported" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.txt"):
                os.remove("temp.txt")
    
    @patch.object(VueLinter, '_check_dependencies')
    def test_lint_file_missing_dependencies(self, mock_check):
        """测试缺少依赖项的情况"""
        # 模拟依赖检查失败
        mock_check.return_value = False
        
        # 创建一个临时Vue文件
        with open("temp.vue", "w") as f:
            f.write("<template><div>Hello</div></template>")
        
        try:
            result = self.linter.lint_file("temp.vue")
            
            assert result['success'] == False
            assert "依赖" in result.get('error', '') or "dependencies" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.vue"):
                os.remove("temp.vue")
    
    @patch.object(VueLinter, '_detect_file_type')
    def test_lint_file_not_vue_file(self, mock_detect):
        """测试非Vue文件"""
        # 模拟文件类型检测失败
        mock_detect.return_value = False
        
        # 创建一个临时JS文件
        with open("temp.js", "w") as f:
            f.write("function hello() { console.log('Hello'); }")
        
        try:
            result = self.linter.lint_file("temp.js")
            
            assert result['success'] == False
            assert "Not a Vue file" in result.get('error', '')
        finally:
            # 清理
            if os.path.exists("temp.js"):
                os.remove("temp.js")
    
    @patch.object(VueLinter, '_check_dependencies')
    @patch.object(VueLinter, '_detect_file_type')
    @patch.object(VueLinter, '_install_eslint_if_needed')
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
                'filePath': os.path.abspath('test.vue'),
                'errorCount': 1,
                'warningCount': 2,
                'messages': [
                    {
                        'line': 10,
                        'column': 5,
                        'severity': 2,
                        'message': '组件名称必须是多词的',
                        'ruleId': 'vue/multi-word-component-names'
                    },
                    {
                        'line': 15,
                        'column': 1,
                        'severity': 1,
                        'message': 'props应该被详细定义',
                        'ruleId': 'vue/require-prop-types'
                    },
                    {
                        'line': 20,
                        'column': 10,
                        'severity': 1,
                        'message': '缺少key属性',
                        'ruleId': 'vue/require-v-for-key'
                    }
                ]
            }
        ])
        mock_run.return_value = mock_process
        
        # 创建一个临时Vue文件
        with open("test.vue", "w") as f:
            f.write("<template><div>Hello</div></template>")
        
        try:
            result = self.linter.lint_file("test.vue")
            
            assert result['success'] == True
            assert result['framework'] == 'vue'
            assert result['files_analyzed'] == 1
            assert result['error_count'] == 1
            assert result['warning_count'] == 2
            assert len(result['issues']) == 3
        finally:
            # 清理
            if os.path.exists("test.vue"):
                os.remove("test.vue")
    
    # python -m pytest src/autocoder/linters/test_vue_linter.py::TestVueLinter::test_lint_real_file -v -s
    @pytest.mark.integration
    def test_lint_real_file(self):
        """测试对实际文件的lint功能"""
        # 检查是否有Vue示例文件可用
        test_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(test_dir, "test_samples", "vue_component.vue")
        
        if not os.path.exists(file_path):
            # 如果没有测试示例文件，创建一个
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write("""
<template>
  <div class="test-component">
    <h1>Hello, {{ name }}!</h1>
    <p>This is a test Vue component.</p>
  </div>
</template>

<script>
export default {
  name: 'TestComponent',
  props: {
    name: {
      type: String,
      required: true,
      default: 'World'
    }
  }
}
</script>

<style scoped>
.test-component {
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 5px;
}
</style>
                """)
        
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