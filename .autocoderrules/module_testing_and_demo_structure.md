---
description: 为新模块添加Pytest测试和示例Demo的标准结构
globs: ["src/**/*.py"] # 适用于src目录下所有Python模块
alwaysApply: false
---

# 模块测试与演示标准结构

## 简要说明
本规则定义了为项目中的新Python模块添加单元测试（使用Pytest）和演示脚本（在examples目录）的标准方法。旨在确保模块的功能正确性、覆盖各种场景，并提供清晰的使用示例，提高代码质量和可维护性。

## 典型用法

### 1. 单元测试 (`test_<module_name>.py`)

在与被测模块相同的目录下（或指定的tests目录）创建 `test_<module_name>.py` 文件。

```python
# /path/to/your/module/test_your_module.py
import pytest
import os
import tempfile
import shutil
# from unittest.mock import patch, MagicMock # 如果需要Mock

# 导入被测模块/类
from .your_module import YourClassOrFunction
# 导入相关类型或配置类
from ..common.types import InputType, OutputType, ConfigArgs # 示例路径

# [可选] 测试环境辅助函数
def create_test_environment(base_dir, structure):
    """创建测试所需的文件/目录结构"""
    for path, content in structure.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

# Pytest Fixture: 临时目录
@pytest.fixture(scope="function") # 根据需要选择 scope: function, class, module, session
def temp_test_dir():
    """提供一个临时的、测试后自动清理的目录"""
    temp_dir = tempfile.mkdtemp()
    print(f"Created temp dir for test: {temp_dir}") # Debugging output
    yield temp_dir
    print(f"Cleaning up temp dir: {temp_dir}") # Debugging output
    shutil.rmtree(temp_dir)

# Pytest Fixture: 被测类的实例
@pytest.fixture
def instance_to_test(temp_test_dir):
    """创建并配置被测类的实例"""
    # 准备必要的配置和输入
    args = ConfigArgs(source_dir=temp_test_dir) # 示例配置
    tool_input = InputType(param="initial_value") # 示例输入
    
    # 实例化被测类 (根据实际构造函数调整)
    instance = YourClassOrFunction(agent=None, tool=tool_input, args=args)
    return instance

# --- 测试用例 ---

def test_happy_path(instance_to_test, temp_test_dir):
    """测试核心功能的成功路径"""
    # [可选] 准备特定于此测试的环境或输入
    create_test_environment(temp_test_dir, {"file1.txt": "hello world"})
    instance_to_test.tool.param = "world"

    # 执行被测方法
    result: OutputType = instance_to_test.resolve() # 或直接调用函数

    # 验证结果
    assert isinstance(result, OutputType)
    assert result.success is True
    assert "成功" in result.message # 假设成功消息包含 "成功"
    # 验证具体内容 (根据实际情况调整)
    # assert len(result.content) == 1
    # assert result.content[0]["path"] == "file1.txt"

def test_no_match_scenario(instance_to_test):
    """测试未找到匹配项的场景"""
    instance_to_test.tool.param = "non_existent"
    result = instance_to_test.resolve()
    assert result.success is True # 通常无匹配也是成功执行
    assert "Found 0 matches" in result.message # 示例消息
    # assert len(result.content) == 0

def test_error_handling_invalid_input(instance_to_test):
    """测试处理无效输入的错误情况"""
    instance_to_test.tool.param = "[invalid regex(" # 示例无效输入
    result = instance_to_test.resolve()
    assert result.success is False
    assert "Invalid" in result.message # 检查错误消息

# 添加更多覆盖不同逻辑分支、边界条件和错误处理的测试用例...

```

### 2. 演示脚本 (`demo_<module_name>.py`)

在项目根目录下的 `examples/` 目录中创建 `demo_<module_name>.py` 文件。

```python
# /examples/demo_your_module.py
import os
import shutil
from loguru import logger

# 导入被测模块/类
from <path.to.your.module> import YourClassOrFunction # 修改为实际路径
# 导入相关类型或配置类
from <path.to.types> import InputType, ConfigArgs # 修改为实际路径
# [可选] 导入环境设置助手
# from autocoder.helper.rag_doc_creator import create_sample_files

def main():
    logger.info(f"--- 开始演示 {YourClassOrFunction.__name__} ---")

    # 1. 准备演示环境 (如果需要)
    base_dir = "sample_your_module_demo"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(os.path.join(base_dir, "subdir"), exist_ok=True)
    with open(os.path.join(base_dir, "file1.txt"), "w") as f:
        f.write("Some demo content here.\nLine two.")
    with open(os.path.join(base_dir, "subdir", "script.py"), "w") as f:
        f.write("print('hello from script')")
    # 或使用助手函数: create_sample_files(base_dir)
    logger.info(f"创建演示环境于: {base_dir}")

    # 2. 初始化配置参数
    args = ConfigArgs(
        source_dir=base_dir,
        # ... 其他所需参数 ...
    )
    logger.info(f"使用配置: {args}")

    # 3. 构造输入数据
    tool_input = InputType(
        param1="demo_value",
        # ... 其他输入字段 ...
    )
    logger.info(f"使用输入: {tool_input}")

    # 4. 实例化或准备调用
    instance = YourClassOrFunction(
        agent=None, # 或模拟对象
        tool=tool_input,
        args=args
    )
    logger.info("实例已创建")

    # 5. 执行核心逻辑
    logger.info("开始执行核心功能...")
    result = instance.resolve() # 或直接调用函数

    # 6. 处理并展示结果
    if not result.success:
        logger.error(f"执行失败: {result.message}")
    else:
        logger.success(f"执行成功: {result.message}")
        logger.info("详细结果:")
        if hasattr(result, 'content') and result.content:
            if isinstance(result.content, list):
                 logger.info(f"共找到 {len(result.content)} 项结果。")
                 for idx, item in enumerate(result.content[:5]): # 显示前5项
                    logger.info(f"  结果 {idx + 1}: {item}")
            else:
                 logger.info(f"内容: {result.content}")
        else:
            logger.info("无具体内容返回。")

    # 7. [可选] 清理环境
    # logger.info(f"清理演示环境: {base_dir}")
    # shutil.rmtree(base_dir)

    logger.info(f"--- 演示 {YourClassOrFunction.__name__} 结束 ---")

if __name__ == "__main__":
    main()

```

## 依赖说明
- **测试**:
    - `pytest`: 用于运行测试和使用 fixture。 (`pip install pytest`)
    - 标准库: `os`, `tempfile`, `shutil`.
    - `unittest.mock` (可选): 如果需要模拟依赖项。
- **演示**:
    - `loguru`: 用于日志记录 (推荐)。 (`pip install loguru`)
    - 标准库: `os`, `shutil`.
    - 项目内部依赖: 被测模块、配置类、类型定义等。
- **环境**:
    - Python 3.x 环境。
    - 确保项目依赖已安装。

## 学习来源
从以下文件的结构和实践中提取：
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/agent/agentic_edit_tools/test_search_files_tool_resolver.py`
- `/Users/allwefantasy/projects/auto-coder/examples/demo_search_files_tool_resolver.py`
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/agent/agentic_edit_tools/search_files_tool_resolver.py` (作为被测试和演示的对象)