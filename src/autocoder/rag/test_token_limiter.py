import pytest
import os
import shutil
import tempfile
from loguru import logger
from pathlib import Path
import time
import json
from typing import Dict, Any, List, Optional

# 导入被测模块
from autocoder.rag.token_limiter import TokenLimiter
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.rag.long_context_rag import RAGStat, RecallStat, ChunkStat, AnswerStat
from byzerllm.utils.types import SingleOutputMeta

# 1. 初始化FileMonitor（必须最先进行）
@pytest.fixture(scope="function")
def setup_file_monitor(temp_test_dir):
    """初始化FileMonitor，必须最先执行"""
    try:
        from autocoder.common.file_monitor.monitor import FileMonitor
        monitor = FileMonitor(temp_test_dir)
        monitor.reset_instance()
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
        reset_rules_manager()
        rules = get_rules(temp_test_dir)
        logger.info(f"已加载规则: {len(rules)} 条")
    except Exception as e:
        logger.error(f"加载规则出错: {e}")
    
    return temp_test_dir

# Pytest Fixture: 临时测试目录
@pytest.fixture(scope="function")
def temp_test_dir():
    """提供一个临时的、测试后自动清理的目录"""
    temp_dir = tempfile.mkdtemp()
    logger.info(f"创建测试临时目录: {temp_dir}")
    yield temp_dir
    logger.info(f"清理测试临时目录: {temp_dir}")
    shutil.rmtree(temp_dir)

# Pytest Fixture: 测试文件结构
@pytest.fixture(scope="function")
def test_files(temp_test_dir):
    """创建测试所需的文件/目录结构"""
    # 创建示例文件
    file_structure = {
        "docs/guide.md": "# TokenLimiter 使用指南\n使用TokenLimiter可以控制文档分块和令牌限制。",
        "docs/api.md": "# API说明\n## 初始化\n```python\nlimiter = TokenLimiter(count_tokens, full_text_limit, segment_limit, buff_limit, llm)\n```",
        "src/example.py": "def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b",
        "src/utils/helpers.py": "def format_text(text):\n    return text.strip()\n\ndef count_words(text):\n    return len(text.split())",
        ".gitignore": "*.log\n__pycache__/\n.cache/",
        ".autocoderignore": "*.log\n__pycache__/\n.cache/"
    }
    
    for file_path, content in file_structure.items():
        full_path = os.path.join(temp_test_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return temp_test_dir

# Pytest Fixture: 配置参数
@pytest.fixture
def test_args():
    """创建测试用配置参数"""
    return AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=400,
        context_prune_sliding_window_size=10,
        context_prune_sliding_window_overlap=2,
        rag_context_window_limit=8000,
        rag_doc_filter_relevance=3,
        full_text_ratio=0.7,
        segment_ratio=0.2,
        index_filter_workers=1,
        required_exts=".py,.md",
        monitor_mode=False,
        enable_hybrid_index=False,
        disable_segment_reorder=False
    )

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

# 5. TokenCounter实例
@pytest.fixture
def token_counter(load_tokenizer_fixture):
    """创建TokenCounter实例"""
    from autocoder.rag.token_counter import TokenCounter
    from autocoder.rag.variable_holder import VariableHolder
    
    tokenizer_path = None
    if hasattr(VariableHolder, "TOKENIZER_PATH") and VariableHolder.TOKENIZER_PATH:
        tokenizer_path = VariableHolder.TOKENIZER_PATH
        return TokenCounter(tokenizer_path)
    
    # 如果没有可用的tokenizer_path，使用RemoteTokenCounter
    from autocoder.rag.token_counter import RemoteTokenCounter
    from byzerllm import ByzerLLM
    
    tokenizer_llm = ByzerLLM()
    if tokenizer_llm.is_model_exist("deepseek_tokenizer"):
        tokenizer_llm.setup_default_model_name("deepseek_tokenizer")
        return RemoteTokenCounter(tokenizer_llm)
    
    pytest.skip("没有可用的tokenizer，跳过测试")

# 6. TokenLimiter实例
@pytest.fixture
def token_limiter(real_llm, token_counter, test_args):
    """创建TokenLimiter实例"""
    from autocoder.rag.token_limiter import TokenLimiter
    
    full_text_limit = int(test_args.rag_context_window_limit * test_args.full_text_ratio)
    segment_limit = int(test_args.rag_context_window_limit * test_args.segment_ratio)
    buff_limit = int(test_args.rag_context_window_limit * (1 - test_args.full_text_ratio - test_args.segment_ratio))
    
    limiter = TokenLimiter(
        count_tokens=token_counter.count_tokens,
        full_text_limit=full_text_limit,
        segment_limit=segment_limit,
        buff_limit=buff_limit,
        llm=real_llm,
        disable_segment_reorder=test_args.disable_segment_reorder
    )
    
    return limiter

# --- 测试用例 ---

def test_limit_tokens_basic(token_limiter, test_files):
    """测试TokenLimiter的基本功能"""
    # 创建测试文档
    relevant_docs = [
        SourceCode(
            module_name=os.path.join(test_files, "docs/guide.md"),
            source_code="# TokenLimiter 使用指南\n使用TokenLimiter可以控制文档分块和令牌限制。"
        ),
        SourceCode(
            module_name=os.path.join(test_files, "docs/api.md"),
            source_code="# API说明\n## 初始化\n```python\nlimiter = TokenLimiter(count_tokens, full_text_limit, segment_limit, buff_limit, llm)\n```"
        )
    ]
    
    # 创建对话
    conversations = [{"role": "user", "content": "如何使用TokenLimiter进行文档分块?"}]
    
    # 执行令牌限制
    result = token_limiter.limit_tokens(
        relevant_docs=relevant_docs,
        conversations=conversations,
        index_filter_workers=1
    )
    
    # 验证结果
    assert result is not None, "应该返回结果"
    assert hasattr(result, "docs"), "结果应该包含文档"
    assert len(result.docs) > 0, "应该至少返回一个文档"
    assert hasattr(result, "input_tokens_counts"), "结果应该包含输入token计数"
    assert hasattr(result, "generated_tokens_counts"), "结果应该包含生成token计数"
    
    # 检查是否有第一轮全文文档
    assert hasattr(token_limiter, "first_round_full_docs"), "应该有first_round_full_docs属性"
    
    # 检查是否有第二轮提取文档
    assert hasattr(token_limiter, "second_round_extracted_docs"), "应该有second_round_extracted_docs属性"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("TokenLimiter基本功能测试结果:")
    logger.info("-"*80)
    logger.info(f"输入文档数: {len(relevant_docs)}")
    logger.info(f"输出文档数: {len(result.docs)}")
    logger.info(f"第一轮全文文档数: {len(token_limiter.first_round_full_docs)}")
    logger.info(f"第二轮提取文档数: {len(token_limiter.second_round_extracted_docs)}")
    logger.info(f"输入token计数: {result.input_tokens_counts}")
    logger.info(f"生成token计数: {result.generated_tokens_counts}")
    logger.info("="*80)

def test_limit_tokens_with_large_docs(token_limiter, test_files):
    """测试TokenLimiter处理大文档的能力"""
    # 创建一个大的测试文档
    large_content = "# 大文档测试\n\n" + "这是一个很长的文档。" * 100
    
    relevant_docs = [
        SourceCode(
            module_name=os.path.join(test_files, "docs/large_doc.md"),
            source_code=large_content
        ),
        SourceCode(
            module_name=os.path.join(test_files, "docs/guide.md"),
            source_code="# TokenLimiter 使用指南\n使用TokenLimiter可以控制文档分块和令牌限制。"
        )
    ]
    
    # 创建对话
    conversations = [{"role": "user", "content": "如何处理大型文档?"}]
    
    # 执行令牌限制
    result = token_limiter.limit_tokens(
        relevant_docs=relevant_docs,
        conversations=conversations,
        index_filter_workers=1
    )
    
    # 验证结果
    assert result is not None, "应该返回结果"
    assert len(result.docs) > 0, "应该至少返回一个文档"
    
    # 检查所有文档的总令牌数是否低于限制
    total_tokens = sum([
        token_limiter.count_tokens(doc.source_code) for doc in result.docs
    ])
    total_limit = token_limiter.full_text_limit + token_limiter.segment_limit + token_limiter.buff_limit
    
    assert total_tokens <= total_limit, f"总令牌数({total_tokens})应该不超过限制({total_limit})"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("TokenLimiter处理大文档测试结果:")
    logger.info("-"*80)
    logger.info(f"输入文档数: {len(relevant_docs)}")
    logger.info(f"输出文档数: {len(result.docs)}")
    logger.info(f"总令牌数: {total_tokens}")
    logger.info(f"总限制: {total_limit}")
    logger.info(f"第一轮全文文档数: {len(token_limiter.first_round_full_docs)}")
    logger.info(f"第二轮提取文档数: {len(token_limiter.second_round_extracted_docs)}")
    logger.info("="*80)

def test_limit_tokens_integration(token_limiter, token_counter, real_llm, test_args, test_files):
    """集成测试：模拟LongContextRAG中的_process_document_chunking调用"""
    # 创建测试文档
    relevant_docs = [
        SourceCode(
            module_name=os.path.join(test_files, "docs/guide.md"),
            source_code="# TokenLimiter 使用指南\n使用TokenLimiter可以控制文档分块和令牌限制。"
        ),
        SourceCode(
            module_name=os.path.join(test_files, "docs/api.md"),
            source_code="# API说明\n## 初始化\n```python\nlimiter = TokenLimiter(count_tokens, full_text_limit, segment_limit, buff_limit, llm)\n```"
        ),
        SourceCode(
            module_name=os.path.join(test_files, "src/example.py"),
            source_code="def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b"
        )
    ]
    
    # 创建对话
    conversations = [{"role": "user", "content": "如何使用TokenLimiter?"}]
    
    # 准备RAG统计数据
    rag_stat = RAGStat(
        recall_stat=RecallStat(
            total_input_tokens=10,  # 假设已有一些token
            total_generated_tokens=5,
            model_name=real_llm.default_model_name,
        ),
        chunk_stat=ChunkStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=real_llm.default_model_name,
        ),
        answer_stat=AnswerStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=real_llm.default_model_name,
        ),
    )
    
    # 模拟_process_document_chunking的处理逻辑
    first_round_full_docs = []
    second_round_extracted_docs = []
    sencond_round_time = 0
    
    start_time = time.time()
    token_limiter_result = token_limiter.limit_tokens(
        relevant_docs=relevant_docs,
        conversations=conversations,
        index_filter_workers=test_args.index_filter_workers or 1,
    )
    sencond_round_time = time.time() - start_time
    
    # 更新统计信息
    rag_stat.chunk_stat.total_input_tokens += sum(token_limiter_result.input_tokens_counts)
    rag_stat.chunk_stat.total_generated_tokens += sum(token_limiter_result.generated_tokens_counts)
    rag_stat.chunk_stat.model_name = token_limiter_result.model_name
    
    final_relevant_docs = token_limiter_result.docs
    first_round_full_docs = token_limiter.first_round_full_docs
    second_round_extracted_docs = token_limiter.second_round_extracted_docs
    
    # 验证结果
    assert final_relevant_docs is not None, "应该返回处理后的文档"
    assert len(final_relevant_docs) > 0, "应该至少返回一个文档"
    assert rag_stat.chunk_stat.total_input_tokens > 0, "输入token计数应该增加"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("TokenLimiter集成测试结果:")
    logger.info("-"*80)
    logger.info(f"处理时间: {sencond_round_time:.4f}秒")
    logger.info(f"输入文档数: {len(relevant_docs)}")
    logger.info(f"输出文档数: {len(final_relevant_docs)}")
    logger.info(f"第一轮全文文档数: {len(first_round_full_docs)}")
    logger.info(f"第二轮提取文档数: {len(second_round_extracted_docs)}")
    logger.info(f"输入token总数: {rag_stat.chunk_stat.total_input_tokens}")
    logger.info(f"生成token总数: {rag_stat.chunk_stat.total_generated_tokens}")
    logger.info("="*80)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_token_limiter.py"]) 