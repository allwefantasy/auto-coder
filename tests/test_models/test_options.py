






"""
测试AutoCodeOptions模型
"""

import pytest
import os
from pathlib import Path

from src.autocoder.sdk.models.options import AutoCodeOptions
from src.autocoder.sdk.exceptions import ValidationError


class TestAutoCodeOptions:
    """测试AutoCodeOptions类"""
    
    def test_default_initialization(self):
        """测试默认初始化
        Given: 无参数创建AutoCodeOptions
        When: 实例化对象
        Then: 应该使用默认值并通过验证
        """
        options = AutoCodeOptions()
        
        assert options.max_turns == 3
        assert options.system_prompt is None
        assert options.cwd == os.getcwd()  # 应该被标准化为当前工作目录
        assert options.permission_mode == "manual"
        assert options.output_format == "text"
        assert options.stream is False
        assert options.temperature == 0.7
        assert options.timeout == 30
        assert options.verbose is False
        assert options.include_project_structure is True
    
    def test_custom_initialization(self, temp_dir):
        """测试自定义初始化
        Given: 自定义参数
        When: 创建AutoCodeOptions实例
        Then: 应该使用指定的参数值
        """
        options = AutoCodeOptions(
            max_turns=5,
            system_prompt="Custom prompt",
            cwd=temp_dir,
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits",
            output_format="json",
            stream=True,
            model="test-model",
            temperature=0.5,
            timeout=60,
            verbose=True
        )
        
        assert options.max_turns == 5
        assert options.system_prompt == "Custom prompt"
        assert options.cwd == str(Path(temp_dir).resolve())
        assert options.allowed_tools == ["Read", "Write"]
        assert options.permission_mode == "acceptedits"  # 应该被标准化为小写
        assert options.output_format == "json"
        assert options.stream is True
        assert options.model == "test-model"
        assert options.temperature == 0.5
        assert options.timeout == 60
        assert options.verbose is True
    
    def test_max_turns_validation(self):
        """测试max_turns验证
        Given: 无效的max_turns值
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="max_turns.*must be positive"):
            AutoCodeOptions(max_turns=0)
        
        with pytest.raises(ValidationError, match="max_turns.*must be positive"):
            AutoCodeOptions(max_turns=-1)
        
        with pytest.raises(ValidationError, match="max_turns.*cannot exceed 100"):
            AutoCodeOptions(max_turns=101)
    
    def test_output_format_validation(self):
        """测试output_format验证
        Given: 无效的output_format值
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="output_format.*must be one of"):
            AutoCodeOptions(output_format="invalid_format")
    
    def test_permission_mode_validation(self):
        """测试permission_mode验证
        Given: 无效的permission_mode值
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="permission_mode.*must be one of"):
            AutoCodeOptions(permission_mode="invalid_mode")
    
    def test_allowed_tools_validation(self):
        """测试allowed_tools验证
        Given: 无效的工具列表
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="invalid tools"):
            AutoCodeOptions(allowed_tools=["InvalidTool"])
    
    def test_temperature_validation(self):
        """测试temperature验证
        Given: 无效的temperature值
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="temperature.*must be between"):
            AutoCodeOptions(temperature=-0.1)
        
        with pytest.raises(ValidationError, match="temperature.*must be between"):
            AutoCodeOptions(temperature=2.1)
    
    def test_timeout_validation(self):
        """测试timeout验证
        Given: 无效的timeout值
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="timeout.*must be positive"):
            AutoCodeOptions(timeout=0)
        
        with pytest.raises(ValidationError, match="timeout.*must be positive"):
            AutoCodeOptions(timeout=-1)
    
    def test_cwd_validation(self):
        """测试cwd验证
        Given: 无效的cwd路径
        When: 创建AutoCodeOptions实例
        Then: 应该抛出ValidationError
        """
        with pytest.raises(ValidationError, match="directory does not exist"):
            AutoCodeOptions(cwd="/nonexistent/directory")
    
    def test_to_dict(self, temp_dir):
        """测试to_dict方法
        Given: AutoCodeOptions实例
        When: 调用to_dict方法
        Then: 应该返回包含所有字段的字典
        """
        options = AutoCodeOptions(
            max_turns=5,
            system_prompt="Test prompt",
            cwd=temp_dir
        )
        
        result = options.to_dict()
        
        assert isinstance(result, dict)
        assert result["max_turns"] == 5
        assert result["system_prompt"] == "Test prompt"
        assert result["cwd"] == str(Path(temp_dir).resolve())
        assert "allowed_tools" in result
        assert "permission_mode" in result
        assert "output_format" in result
    
    def test_from_dict(self, temp_dir):
        """测试from_dict方法
        Given: 有效的字典数据
        When: 调用from_dict方法
        Then: 应该创建正确的AutoCodeOptions实例
        """
        data = {
            "max_turns": 5,
            "system_prompt": "Test prompt",
            "cwd": temp_dir,
            "allowed_tools": ["Read"],
            "permission_mode": "manual",
            "output_format": "json"
        }
        
        options = AutoCodeOptions.from_dict(data)
        
        assert options.max_turns == 5
        assert options.system_prompt == "Test prompt"
        assert options.cwd == str(Path(temp_dir).resolve())
        assert options.allowed_tools == ["Read"]
        assert options.permission_mode == "manual"
        assert options.output_format == "json"
    
    def test_copy(self, temp_dir):
        """测试copy方法
        Given: AutoCodeOptions实例
        When: 调用copy方法并传入更改
        Then: 应该返回新的实例，包含更改
        """
        original = AutoCodeOptions(
            max_turns=3,
            cwd=temp_dir
        )
        
        copied = original.copy(max_turns=5, system_prompt="New prompt")
        
        # 原实例不应该改变
        assert original.max_turns == 3
        assert original.system_prompt is None
        
        # 新实例应该包含更改
        assert copied.max_turns == 5
        assert copied.system_prompt == "New prompt"
        assert copied.cwd == original.cwd  # 未更改的字段应该相同
    
    def test_merge(self, temp_dir):
        """测试merge方法
        Given: 两个AutoCodeOptions实例
        When: 调用merge方法
        Then: 应该返回合并后的新实例
        """
        base = AutoCodeOptions(
            max_turns=3,
            system_prompt="Base prompt",
            cwd=temp_dir
        )
        
        override = AutoCodeOptions(
            max_turns=5,
            output_format="json"
        )
        
        merged = base.merge(override)
        
        # base实例不应该改变
        assert base.max_turns == 3
        assert base.output_format == "text"
        
        # 合并后的实例应该包含override的非None值
        assert merged.max_turns == 5  # 被override覆盖
        assert merged.system_prompt == "Base prompt"  # 保持base的值
        assert merged.output_format == "json"  # 被override覆盖
        assert merged.cwd == str(Path(temp_dir).resolve())  # 保持base的值
    
    def test_normalization(self, temp_dir):
        """测试值标准化
        Given: 需要标准化的输入值
        When: 创建AutoCodeOptions实例
        Then: 值应该被正确标准化
        """
        options = AutoCodeOptions(
            cwd=temp_dir,
            output_format="JSON",  # 大写
            permission_mode="MANUAL",  # 大写
            allowed_tools=[]  # 空列表，应该使用默认值
        )
        
        assert options.output_format == "json"  # 应该被转换为小写
        assert options.permission_mode == "manual"  # 应该被转换为小写
        assert len(options.allowed_tools) > 0  # 应该使用默认工具列表
        assert options.cwd == str(Path(temp_dir).resolve())  # 应该被解析为绝对路径






