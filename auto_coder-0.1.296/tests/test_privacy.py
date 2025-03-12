import pytest
from pathlib import Path
from autocoder.privacy import ModelPathFilter


def test_model_filter_basic(tmp_path):
    # 创建临时配置文件
    config_content = """
model_filters:
  test_model:
    forbidden_paths:
      - "^src/autocoder/index/.*"
      - "^tests/.*"
    """
    config_file = tmp_path / "test_filters.yml"
    config_file.write_text(config_content)

    # 创建过滤器实例
    filter = ModelPathFilter("test_model", str(config_file))

    # 测试路径检查
    assert filter.is_accessible("src/main.py") is True
    assert filter.is_accessible("src/autocoder/index/core.py") is False
    assert filter.is_accessible("tests/test_index.py") is False


def test_model_filter_empty_config(tmp_path):
    # 测试空配置文件
    config_file = tmp_path / "empty_filters.yml"
    config_file.write_text("")

    filter = ModelPathFilter("test_model", str(config_file))
    assert filter.is_accessible("any/path.py") is True


def test_model_filter_default_rules():
    # 测试默认规则
    default_rules = ["^config/.*", "\\.env$"]
    filter = ModelPathFilter(
        "test_model",
        config_path="non_existent.yml",
        default_forbidden=default_rules
    )

    assert filter.is_accessible("src/main.py") is True
    assert filter.is_accessible("config/settings.py") is False
    assert filter.is_accessible(".env") is False


def test_model_filter_add_temp_rule():
    # 测试添加临时规则
    filter = ModelPathFilter("test_model", "non_existent.yml")
    
    # 初始状态应该允许访问
    assert filter.is_accessible("temp/file.py") is True
    
    # 添加临时规则后应该禁止访问
    filter.add_temp_rule("^temp/.*")
    assert filter.is_accessible("temp/file.py") is False


def test_model_filter_from_model_object():
    # 模拟LLM对象
    class MockLLM:
        default_model_name = "mock_model"

    llm = MockLLM()
    filter = ModelPathFilter.from_model_object(llm)
    assert filter.model_name == "mock_model"


def test_model_filter_reload_rules(tmp_path):
    # 测试规则重新加载
    config_file = tmp_path / "reload_filters.yml"
    
    # 初始配置
    initial_config = """
model_filters:
  test_model:
    forbidden_paths:
      - "^src/.*"
    """
    config_file.write_text(initial_config)
    
    filter = ModelPathFilter("test_model", str(config_file))
    assert filter.is_accessible("src/main.py") is False
    
    # 更新配置
    new_config = """
model_filters:
  test_model:
    forbidden_paths:
      - "^tests/.*"
    """
    config_file.write_text(new_config)
    
    # 重新加载规则
    filter.reload_rules()
    assert filter.is_accessible("src/main.py") is True
    assert filter.is_accessible("tests/test.py") is False


def test_model_filter_empty_path():
    # 测试空路径处理
    filter = ModelPathFilter("test_model", "non_existent.yml")
    assert filter.is_accessible("") is True
    assert filter.is_accessible(None) is True