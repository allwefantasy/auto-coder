import pytest
import os
import shutil
import tempfile
from loguru import logger
from pathlib import Path
import time
from typing import Dict, Any, List, Optional, Generator, Tuple

# 导入被测模块
from autocoder.rag.doc_filter import DocFilter
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.rag.long_context_rag import RAGStat, RecallStat, ChunkStat, AnswerStat
from autocoder.rag.relevant_utils import DocFilterResult, DocRelevance, ProgressUpdate
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
        "docs/guide.md": "# DocFilter 使用指南\n使用DocFilter可以筛选相关文档。",
        "docs/api.md": "# API说明\n## 初始化\n```python\ndoc_filter = DocFilter(llm, args, on_ray=False, path='.')\n```",
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
        rag_context_window_limit=8000,
        rag_doc_filter_relevance=3,
        full_text_ratio=0.7,
        segment_ratio=0.2,
        index_filter_workers=1,
        required_exts=".py,.md",
        monitor_mode=False,
        enable_hybrid_index=False,
        rag_recall_max_queries=3
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

# 5. DocFilter实例
@pytest.fixture
def doc_filter(real_llm, test_args, test_files):
    """创建DocFilter实例"""
    doc_filter = DocFilter(
        llm=real_llm,
        args=test_args,
        on_ray=False,
        path=test_files
    )
    logger.info("DocFilter初始化完成")
    return doc_filter

# 6. 测试文档生成函数
@pytest.fixture
def test_documents(test_files):
    """生成测试用文档"""
    documents = [
        SourceCode(
            module_name=os.path.join(test_files, "docs/guide.md"),
            source_code="# DocFilter 使用指南\n使用DocFilter可以筛选相关文档。",
            metadata={}
        ),
        SourceCode(
            module_name=os.path.join(test_files, "docs/api.md"),
            source_code="# API说明\n## 初始化\n```python\ndoc_filter = DocFilter(llm, args, on_ray=False, path='.')\n```",
            metadata={}
        ),
        SourceCode(
            module_name=os.path.join(test_files, "src/example.py"),
            source_code="def add(a, b):\n    return a + b\n\ndef subtract(a, b):\n    return a - b",
            metadata={}
        ),
        SourceCode(
            module_name=os.path.join(test_files, "src/utils/helpers.py"),
            source_code="def format_text(text):\n    return text.strip()\n\ndef count_words(text):\n    return len(text.split())",
            metadata={}
        )
    ]
    
    def document_generator():
        for doc in documents:
            yield doc
    
    return document_generator

# --- 测试用例 ---

def test_filter_docs_basic(doc_filter, test_documents):
    """测试DocFilter基本文档过滤功能"""
    # 创建对话
    conversations = [{"role": "user", "content": "如何使用DocFilter筛选文档?"}]
    
    # 执行文档过滤
    result = doc_filter.filter_docs(
        conversations=conversations,
        documents=test_documents()
    )
    
    # 验证结果
    assert result is not None, "应该返回结果"
    assert len(result.docs) > 0, "应该至少返回一个文档"
    assert len(result.input_tokens_counts) > 0, "应该有输入token计数"
    assert len(result.generated_tokens_counts) > 0, "应该有生成token计数"
    
    # 检查返回的文档是否都有相关性信息
    for doc in result.docs:
        assert hasattr(doc, "relevance"), "应该有相关性信息"
        assert isinstance(doc.relevance, DocRelevance), "相关性应该是DocRelevance类型"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("DocFilter基本功能测试结果:")
    logger.info("-"*80)
    logger.info(f"过滤后的文档数: {len(result.docs)}")
    logger.info(f"输入token计数: {result.input_tokens_counts}")
    logger.info(f"生成token计数: {result.generated_tokens_counts}")
    logger.info(f"处理时间: {result.durations}")
    logger.info(f"模型名称: {result.model_name}")
    
    # 打印文档相关性信息
    for i, doc in enumerate(result.docs):
        rel_score = doc.relevance.score if hasattr(doc.relevance, 'score') else "未知"
        is_relevant = doc.relevance.is_relevant if hasattr(doc.relevance, 'is_relevant') else "未知"
        reason = doc.relevance.reason if hasattr(doc.relevance, 'reason') else "无"
        
        logger.info(f"文档[{i}]: {os.path.basename(doc.source_code.module_name)}")
        logger.info(f"  - 相关性评分: {rel_score}")
        logger.info(f"  - 是否相关: {is_relevant}")
        logger.info(f"  - 原因: {reason}")
    
    logger.info("="*80)

def test_filter_docs_with_progress(doc_filter, test_documents):
    """测试带进度报告的文档过滤功能"""
    # 创建对话
    conversations = [{"role": "user", "content": "如何使用DocFilter进行文档过滤?"}]
    
    # 使用带进度报告的过滤方法
    progress_updates = []
    final_result = None
    
    # 收集进度更新和最终结果
    for progress_update, result in doc_filter.filter_docs_with_progress(
        conversations=conversations,
        documents=test_documents()
    ):
        if progress_update:
            progress_updates.append(progress_update)
        if result is not None:
            final_result = result
    
    # 验证进度更新
    assert len(progress_updates) > 0, "应该至少有一个进度更新"
    for update in progress_updates:
        assert isinstance(update, ProgressUpdate), "进度更新应该是ProgressUpdate类型"
        assert hasattr(update, "completed"), "应该有completed属性"
        assert hasattr(update, "total"), "应该有total属性"
    
    # 验证最终结果
    assert final_result is not None, "应该有最终结果"
    assert len(final_result.docs) > 0, "应该至少返回一个文档"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("DocFilter带进度报告功能测试结果:")
    logger.info("-"*80)
    logger.info(f"进度更新次数: {len(progress_updates)}")
    logger.info(f"最终文档数: {len(final_result.docs)}")
    
    # 打印进度更新信息
    for i, update in enumerate(progress_updates):
        logger.info(f"进度更新[{i}]: {update.message} ({update.completed}/{update.total})")
    
    logger.info("="*80)

def test_process_document_retrieval_integration(doc_filter, test_documents, real_llm):
    """集成测试：模拟LongContextRAG中的_process_document_retrieval调用"""
    # 创建对话和查询
    query = "如何使用DocFilter筛选文档?"
    conversations = [{"role": "user", "content": query}]
    
    # 准备RAG统计数据
    rag_stat = RAGStat(
        recall_stat=RecallStat(
            total_input_tokens=0,
            total_generated_tokens=0,
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
    
    # 模拟_process_document_retrieval的流程
    # 1. 初始生成模型信息
    mock_progress_items = []
    
    mock_progress_items.append(("", SingleOutputMeta(
        input_tokens_count=0,
        generated_tokens_count=0,
        reasoning_content=f"正在使用{rag_stat.recall_stat.model_name}模型搜索文档..."
    )))
    
    # 创建初始的DocFilterResult
    doc_filter_result = DocFilterResult(
        docs=[],
        raw_docs=[],
        input_tokens_counts=[],
        generated_tokens_counts=[],
        durations=[],
        model_name=rag_stat.recall_stat.model_name
    )
    
    # 2. 使用带进度报告的过滤方法
    for progress_update, result in doc_filter.filter_docs_with_progress(
        conversations=conversations,
        documents=test_documents()
    ):
        if result is not None:
            doc_filter_result = result
        else:
            # 生成进度更新
            mock_progress_items.append(("", SingleOutputMeta(
                input_tokens_count=rag_stat.recall_stat.total_input_tokens,
                generated_tokens_count=rag_stat.recall_stat.total_generated_tokens,
                reasoning_content=f"{progress_update.message} ({progress_update.completed}/{progress_update.total})"
            )))
    
    # 3. 更新统计信息
    rag_stat.recall_stat.total_input_tokens += sum(doc_filter_result.input_tokens_counts)
    rag_stat.recall_stat.total_generated_tokens += sum(doc_filter_result.generated_tokens_counts)
    rag_stat.recall_stat.model_name = doc_filter_result.model_name
    
    relevant_docs = doc_filter_result.docs
    
    # 4. 添加过滤结果信息
    mock_progress_items.append(("", SingleOutputMeta(
        input_tokens_count=rag_stat.recall_stat.total_input_tokens,
        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens,
        reasoning_content=f"已完成文档过滤，共找到{len(relevant_docs)}篇相关文档。"
    )))
    
    # 5. 仅保留高相关性文档
    highly_relevant_docs = [doc for doc in relevant_docs if doc.relevance.is_relevant]
    if highly_relevant_docs:
        relevant_docs = highly_relevant_docs
        logger.info(f"Found {len(relevant_docs)} highly relevant documents")
    
    # 6. 返回最终结果
    mock_progress_items.append({"result": relevant_docs})
    
    # 验证结果
    assert len(mock_progress_items) > 0, "应该有处理结果"
    assert isinstance(mock_progress_items[-1], dict), "最后一项应该是结果字典"
    assert "result" in mock_progress_items[-1], "结果字典应该包含'result'键"
    assert len(mock_progress_items[-1]["result"]) > 0, "应该至少返回一个文档"
    assert rag_stat.recall_stat.total_input_tokens > 0, "输入token计数应该增加"
    assert rag_stat.recall_stat.total_generated_tokens > 0, "生成token计数应该增加"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("DocFilter集成测试结果:")
    logger.info("-"*80)
    logger.info(f"处理项数: {len(mock_progress_items)}")
    logger.info(f"相关文档数: {len(mock_progress_items[-1]['result'])}")
    logger.info(f"输入token总数: {rag_stat.recall_stat.total_input_tokens}")
    logger.info(f"生成token总数: {rag_stat.recall_stat.total_generated_tokens}")
    
    # 打印高相关性文档
    if highly_relevant_docs:
        logger.info(f"高相关性文档数: {len(highly_relevant_docs)}")
        for i, doc in enumerate(highly_relevant_docs):
            logger.info(f"高相关文档[{i}]: {os.path.basename(doc.source_code.module_name)}")
            logger.info(f"  - 相关性评分: {doc.relevance.score}")
            logger.info(f"  - 原因: {doc.relevance.reason}")
    
    logger.info("="*80)

def test_extract_search_queries_integration(doc_filter, real_llm, test_args):
    """测试集成查询提取功能"""
    # 创建对话
    conversations = [
        {"role": "system", "content": "你是一个助手，帮助用户解决问题。"},
        {"role": "user", "content": "我想知道DocFilter如何工作，以及如何使用它来筛选文档？"}
    ]
    
    # 使用extract_search_queries函数
    from autocoder.rag.conversation_to_queries import extract_search_queries
    
    queries = extract_search_queries(
        conversations=conversations,
        args=test_args,
        llm=real_llm,
        max_queries=test_args.rag_recall_max_queries
    )
    
    # 验证结果
    assert queries is not None, "应该返回查询结果"
    assert len(queries) > 0, "应该至少有一个查询"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("查询提取测试结果:")
    logger.info("-"*80)
    logger.info(f"提取的查询数量: {len(queries)}")
    
    for i, query in enumerate(queries):
        logger.info(f"查询[{i}]: {query.query}")
        if hasattr(query, 'explanation') and query.explanation:
            logger.info(f"  - 解释: {query.explanation}")
    
    logger.info("="*80)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_doc_filter.py"]) 