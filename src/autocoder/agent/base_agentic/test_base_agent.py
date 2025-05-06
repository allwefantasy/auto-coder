"""
BaseAgent类和byzerllm.prompt装饰器的单元测试
"""
import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import byzerllm

# 导入被测类
from autocoder.agent.base_agentic import BaseAgent
from autocoder.agent.base_agentic.types import BaseTool, AgentRequest, ToolResult
from autocoder.common import AutoCoderArgs, SourceCodeList, SourceCode

# 测试环境辅助函数
def create_test_environment(base_dir, structure):
    """创建测试所需的文件/目录结构"""
    for path, content in structure.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

# Pytest Fixture: 临时目录
@pytest.fixture(scope="function")
def temp_test_dir():
    """提供一个临时的、测试后自动清理的目录"""
    temp_dir = tempfile.mkdtemp()
    print(f"Created temp dir for test: {temp_dir}")
    yield temp_dir
    print(f"Cleaning up temp dir: {temp_dir}")
    shutil.rmtree(temp_dir)

# Pytest Fixture: 重置FileMonitor
@pytest.fixture
def setup_file_monitor(temp_test_dir):
    """初始化FileMonitor，必须最先执行"""
    try:
        from autocoder.common.file_monitor.monitor import FileMonitor
        # 重置FileMonitor实例，确保测试隔离性
        monitor = FileMonitor(temp_test_dir)
        monitor.reset_instance()
        if not monitor.is_running():
            monitor.start()
            print(f"文件监控已启动: {temp_test_dir}")
        else:
            print(f"文件监控已在运行中: {monitor.root_dir}")
    except Exception as e:
        print(f"初始化文件监控出错: {e}")
    
    # 加载规则文件
    try:
        from autocoder.common.rulefiles.autocoderrules_utils import get_rules, reset_rules_manager
        reset_rules_manager()  # 重置规则管理器，确保测试隔离性
        rules = get_rules(temp_test_dir)
        print(f"已加载规则: {len(rules)} 条")
    except Exception as e:
        print(f"加载规则出错: {e}")
    
    return temp_test_dir

# Pytest Fixture: 加载tokenizer
@pytest.fixture
def load_tokenizer_fixture(setup_file_monitor):
    """加载tokenizer，必须在FileMonitor和rules初始化之后"""
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()
    print("Tokenizer加载完成")
    return True

# Pytest Fixture: mock的LLM
@pytest.fixture
def mock_llm():
    """创建模拟的LLM对象"""
    mock = MagicMock()
    # 模拟chat_oai方法返回结果
    mock.chat_oai.return_value = [{"role": "assistant", "content": "这是模拟的LLM回答"}]
    # 设置必要的属性
    mock.default_model_name = "mock_model"
    return mock

