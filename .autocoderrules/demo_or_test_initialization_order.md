---
description: 在实现demo或者单元测试时，需要遵循的的初始化规则
globs:  
  - "examples/demo_*.py"
  - "examples/test_*.py"
  - "src/autocoder/rag/test_*.py"
alwaysApply: false
---

# 实现demo或者单元测试时，需要遵循的的初始化规则

比如对LongContextRAG等基于检索增强生成的组件生成demo或者测试代码时，必须严格遵循特定的初始化顺序，以避免FileMonitor、token计数器等组件的冲突和错误初始化。

## 关键初始化顺序

1. **首先初始化FileMonitor**：必须首先初始化文件监控系统，并指定正确的监控目录
2. **然后获取rules**：从项目目录加载规则文件
3. **接着加载tokenizer**：tokenizer的加载必须在前两步完成后进行
4. **再初始化LLM**：获取语言模型客户端
5. **最后初始化RAG组件**：使用上述组件初始化RAG相关类

## Demo标准初始化代码模板

```python
import os
from loguru import logger

# 1. 初始化FileMonitor（必须最先进行）
try:
    from autocoder.common.file_monitor.monitor import FileMonitor
    monitor = FileMonitor(args.source_dir)  # 使用项目根目录
    if not monitor.is_running():
        monitor.start()
        logger.info(f"文件监控已启动: {args.source_dir}")
    else:
        logger.info(f"文件监控已在运行中: {monitor.root_dir}")
except Exception as e:
    logger.error(f"初始化文件监控出错: {e}")

# 2. 加载规则文件
try:
    from autocoder.common.rulefiles.autocoderrules_utils import get_rules
    rules = get_rules(args.source_dir)
    logger.info(f"已加载规则: {len(rules)} 条")
except Exception as e:
    logger.error(f"加载规则出错: {e}")

# 3. 加载tokenizer (必须在前两步之后)
# 注意: auto_coder_runner会自动触发FileMonitor和rules初始化
# 如果前两步没有正确设置，这里会用错误的目录初始化
from autocoder.auto_coder_runner import load_tokenizer
load_tokenizer()
logger.info("Tokenizer加载完成")

# 4. 初始化LLM
from autocoder.utils.llms import get_single_llm
llm = get_single_llm("v3_chat", product_mode="lite")
logger.info(f"LLM初始化完成: {llm.default_model_name}")

# 5. 最后初始化RAG组件
from autocoder.rag.long_context_rag import LongContextRAG
rag = LongContextRAG(
    llm=llm,
    args=args,
    path=args.source_dir,
    tokenizer_path=None  # 使用默认tokenizer
)
logger.info("RAG组件初始化完成")
```

## 测试代码初始化模板

在测试环境中，需要额外进行实例重置以确保测试的隔离性：

```python
import pytest
from loguru import logger

# 1. 初始化FileMonitor（必须最先进行）
@pytest.fixture(scope="function")
def setup_file_monitor(temp_test_dir):
    """初始化FileMonitor，必须最先执行"""
    try:
        from autocoder.common.file_monitor.monitor import FileMonitor
        monitor = FileMonitor(temp_test_dir)
        monitor.reset_instance()  # 重置FileMonitor实例，确保测试隔离性
        if not monitor.is_running():
            monitor.start()
            logger.info(f"文件监控已启动: {temp_test_dir}")
        else:
            logger.info(f"文件监控已在运行中: {monitor.root_dir}")
    except Exception as e:
        logger.error(f"初始化文件监控出错: {e}")
    
    # 2. 加载规则文件
    try:
        from autocoder.common.rulefiles.autocoderrules_utils import get_rules, reset_rules_manager
        reset_rules_manager()  # 重置规则管理器，确保测试隔离性
        rules = get_rules(temp_test_dir)
        logger.info(f"已加载规则: {len(rules)} 条")
    except Exception as e:
        logger.error(f"加载规则出错: {e}")
    
    return temp_test_dir

# 3. 加载tokenizer (必须在FileMonitor和rules初始化之后)
@pytest.fixture
def load_tokenizer_fixture(setup_file_monitor):
    """加载tokenizer，必须在FileMonitor和rules初始化之后"""
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()
    logger.info("Tokenizer加载完成")
    return True

# 4. 初始化LLM
@pytest.fixture
def real_llm(load_tokenizer_fixture):
    """创建真实的LLM对象，必须在tokenizer加载之后"""
    from autocoder.utils.llms import get_single_llm
    llm = get_single_llm("v3_chat", product_mode="lite")
    logger.info(f"LLM初始化完成: {llm.default_model_name}")
    return llm

# 5. LongContextRAG实例
@pytest.fixture
def rag_instance(real_llm, test_args, test_files, setup_file_monitor, load_tokenizer_fixture):
    """创建LongContextRAG实例，必须在前面所有步骤之后"""
    # 创建实例
    instance = LongContextRAG(
        llm=real_llm,
        args=test_args,
        path=test_files,
        tokenizer_path=None
    )
    logger.info("RAG组件初始化完成")
    return instance
```

## 初始化顺序说明

1. **FileMonitor初始化优先级**：
   - `auto_coder_runner`模块会自动触发FileMonitor初始化
   - 如果不提前手动初始化，会以运行目录作为监控目录，可能导致错误
   - 因此必须在调用`load_tokenizer()`前手动初始化FileMonitor

2. **规则加载次序**：
   - `get_rules()`应在FileMonitor初始化后立即调用
   - 确保规则加载使用正确的项目根目录

3. **Tokenizer加载时机**：
   - 必须在前两步完成后加载，因为`load_tokenizer()`会隐式引用FileMonitor
   - 如果顺序错误，可能导致Tokenizer使用错误的监控目录

4. **测试代码中的特殊处理**：
   - 测试代码必须使用`monitor.reset_instance()`重置FileMonitor实例
   - 使用`reset_rules_manager()`重置规则管理器状态
   - 通过pytest fixture确保组件按正确顺序初始化
   - 可使用`monkeypatch`避免测试中的真实文件监控

## 错误初始化示例与问题

```python
# 错误示例：直接加载tokenizer
from autocoder.auto_coder_runner import load_tokenizer
load_tokenizer()  # 错误！这会使用当前运行目录初始化FileMonitor

# 获取LLM
llm = get_single_llm("v3_chat")  # 现在FileMonitor已经以错误目录初始化

# 初始化RAG - 可能与上面的监控目录不一致
rag = LongContextRAG(llm=llm, args=args, path=project_dir)  # 监控目录和RAG目录不一致！
```

此错误初始化会导致:
- 文件变化监控在错误的目录进行
- 规则文件从错误位置加载
- RAG和文件监控使用不同的目录，产生不一致行为

## 参考源码

相关实现逻辑见:
- `src/autocoder/auto_coder_runner.py`中的`load_tokenizer()`函数
- `src/autocoder/common/file_monitor/monitor.py`中的`FileMonitor`类
- `examples/demo_long_context_rag.py`中的初始化顺序
- `src/autocoder/rag/test_long_context_rag.py`中的测试初始化模式 