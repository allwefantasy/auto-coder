from src.autocoder.common.conf_validator import ConfigValidator, ConfigValidationError
import pytest

def test_validate_boolean():
    # 测试布尔值验证
    assert ConfigValidator.validate_boolean("true") == True
    assert ConfigValidator.validate_boolean("false") == False
    assert ConfigValidator.validate_boolean("1") == True
    assert ConfigValidator.validate_boolean("0") == False
    
    with pytest.raises(ConfigValidationError):
        ConfigValidator.validate_boolean("invalid")

def test_validate_auto_merge():
    # 测试auto_merge配置项验证
    assert ConfigValidator.validate("auto_merge", "editblock", "lite") == "editblock"
    assert ConfigValidator.validate("auto_merge", "diff", "lite") == "diff"
    assert ConfigValidator.validate("auto_merge", "wholefile", "lite") == "wholefile"
    
    with pytest.raises(ConfigValidationError):
        ConfigValidator.validate("auto_merge", "invalid_value", "lite")

def test_validate_editblock_similarity():
    # 测试editblock_similarity配置项验证
    assert ConfigValidator.validate("editblock_similarity", 0.5, "lite") == 0.5
    assert ConfigValidator.validate("editblock_similarity", 0.9, "lite") == 0.9
    
    with pytest.raises(ConfigValidationError):
        ConfigValidator.validate("editblock_similarity", 1.1, "lite")
    
    with pytest.raises(ConfigValidationError):
        ConfigValidator.validate("editblock_similarity", -0.1, "lite")

def test_validate_generate_times_same_model():
    # 测试generate_times_same_model配置项验证
    assert ConfigValidator.validate("generate_times_same_model", 1, "lite") == 1
    assert ConfigValidator.validate("generate_times_same_model", 5, "lite") == 5
    
    with pytest.raises(ConfigValidationError):
        ConfigValidator.validate("generate_times_same_model", 0, "lite")
    
    with pytest.raises(ConfigValidationError):
        ConfigValidator.validate("generate_times_same_model", 6, "lite")

def test_validate_unknown_key():
    # 测试未知配置项
    assert ConfigValidator.validate("unknown_key", "value", "lite") is None

def test_get_config_docs():
    # 测试获取配置文档
    docs = ConfigValidator.get_config_docs()
    assert "auto_merge" in docs
    assert "editblock_similarity" in docs
    assert "generate_times_same_model" in docs

if __name__ == "__main__":
    pytest.main([__file__])