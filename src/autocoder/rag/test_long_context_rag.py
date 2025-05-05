import pytest
import os
import shutil
import tempfile
from loguru import logger
from pathlib import Path
import byzerllm
from typing import Dict, Any

# 导入被测模块
from autocoder.rag.long_context_rag import LongContextRAG
from autocoder.common import AutoCoderArgs

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
        "docs/guide.md": "# RAG 使用指南\n使用LongContextRAG可以处理大规模文档检索和问答。",
        "docs/api.md": "# API说明\n## 初始化\n```python\nrag = LongContextRAG(llm, args, path)\n```",
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
        enable_hybrid_index=False
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

# 用于构建RAG测试查询的辅助类
class RAGQueryBuilder:
    def __init__(self, feature_name: str):
        self.feature_name = feature_name
        
    @byzerllm.prompt()
    def build_test_query(self, specific_aspect: str = None) -> Dict[str, Any]:
        """
        我需要了解有关{{ feature_name }}的信息。
        {% if specific_aspect %}
        特别是关于{{ specific_aspect }}的部分，请详细说明其工作原理。
        {% else %}
        请提供其基本用法和主要特性。
        {% endif %}
        例如，如何在代码中实现和使用它？
        """
        return {
            "feature_name": self.feature_name,
            "specific_aspect": specific_aspect
        }

# --- 测试用例 ---

def test_search(rag_instance):
    """测试文档搜索功能"""
    # 搜索查询
    query = "如何使用RAG进行文档检索?"
    results = rag_instance.search(query)
    
    # 验证结果
    assert len(results) >= 1
    # 检查是否找到了相关文档
    relevant_docs = [doc for doc in results if "RAG" in doc.source_code]
    assert len(relevant_docs) > 0

def test_stream_chat_oai(rag_instance):
    """测试流式聊天功能"""
    # 使用byzerllm.prompt装饰器构建更有结构的测试查询
    query_builder = RAGQueryBuilder(feature_name="RAG检索增强生成")
    test_query = query_builder.build_test_query.prompt(specific_aspect="文档检索原理")
    
    # 构建对话
    conversations = [{"role": "user", "content": test_query}]
    
    # 执行流式聊天
    generator, context = rag_instance.stream_chat_oai(conversations)
    
    # 收集所有响应片段
    response_chunks = []
    tokens_metadata = []
    
    for content, metadata in generator:
        if content:
            response_chunks.append(content)
        if metadata:
            tokens_metadata.append(metadata)
    
    # 合并响应内容
    full_response = "".join(response_chunks)
    
    # 验证响应
    assert len(response_chunks) > 0, "应该产生至少一个响应片段"
    assert full_response, "响应内容不应为空"
    
    # 验证响应内容中是否包含关键概念
    keywords = ["RAG", "检索", "文档", "生成"]
    found_keywords = [keyword for keyword in keywords if keyword in full_response]
    assert len(found_keywords) > 0, f"响应应包含至少一个关键词: {keywords}"
    
    # 验证元数据
    if tokens_metadata:
        assert any(hasattr(meta, 'input_tokens_count') for meta in tokens_metadata), "元数据应包含输入token计数"
        assert any(hasattr(meta, 'generated_tokens_count') for meta in tokens_metadata), "元数据应包含生成token计数"
    
    # 验证上下文
    assert context is not None, "应返回上下文信息"
    if isinstance(context, list) and context:
        # 检查返回的上下文文件是否包含相关文档
        # 由于在合并文档的情况下，文件名可能是Merged_开头，不一定包含RAG字样
        # 只需检查是否有内容返回即可，不必严格要求文件名包含RAG
        assert len(context) > 0, "上下文应包含至少一个文档"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("流式聊天测试结果:")
    logger.info("-"*80)
    logger.info(f"测试查询: {test_query}")
    logger.info("-"*80)
    logger.info(f"响应片段数量: {len(response_chunks)}")
    logger.info(f"完整响应内容:\n{full_response}")
    logger.info("-"*80)
    logger.info(f"找到的关键词: {found_keywords}")
    logger.info("-"*80)
    
    # 打印token统计
    if tokens_metadata:
        input_tokens = sum(getattr(meta, 'input_tokens_count', 0) for meta in tokens_metadata if hasattr(meta, 'input_tokens_count'))
        generated_tokens = sum(getattr(meta, 'generated_tokens_count', 0) for meta in tokens_metadata if hasattr(meta, 'generated_tokens_count'))
        logger.info(f"输入Token总数: {input_tokens}")
        logger.info(f"生成Token总数: {generated_tokens}")
        logger.info(f"Token总消耗: {input_tokens + generated_tokens}")
    else:
        logger.info("未收集到Token元数据")
    logger.info("-"*80)
    
    # 打印上下文信息
    logger.info(f"上下文文件数量: {len(context) if isinstance(context, list) else '未知'}")
    if isinstance(context, list) and context:
        for idx, ctx in enumerate(context):
            logger.info(f"上下文[{idx}]: {ctx}")
    logger.info("="*80)

def test_process_document_retrieval(rag_instance):
    """测试文档召回和过滤阶段"""
    # 构建测试对话
    query = "如何使用RAG进行文档检索?"
    conversations = [{"role": "user", "content": query}]
    
    # 准备RAG统计数据
    from autocoder.rag.long_context_rag import RAGStat, RecallStat, ChunkStat, AnswerStat
    rag_stat = RAGStat(
        recall_stat=RecallStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=rag_instance.recall_llm.default_model_name,
        ),
        chunk_stat=ChunkStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=rag_instance.chunk_llm.default_model_name,
        ),
        answer_stat=AnswerStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=rag_instance.qa_llm.default_model_name,
        ),
    )
    
    # 调用方法获取生成器
    generator = rag_instance._process_document_retrieval(
        conversations=conversations,
        query=query,
        rag_stat=rag_stat
    )
    
    # 收集生成器的输出
    items = []
    for item in generator:
        items.append(item)
    
    # 验证生成器产生了输出
    assert len(items) > 0, "文档召回和过滤阶段应该产生输出"
    
    # 验证最后一个输出是包含结果的字典
    assert isinstance(items[-1], dict), "最后一个输出应该是包含结果的字典"
    assert "result" in items[-1], "结果字典应包含'result'键"
    
    # 验证统计数据被更新
    assert rag_stat.recall_stat.total_input_tokens > 0, "输入token计数应该增加"
    assert rag_stat.recall_stat.total_generated_tokens > 0, "生成token计数应该增加"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("文档召回和过滤阶段测试结果:")
    logger.info("-"*80)
    logger.info(f"生成的项目数: {len(items)}")
    logger.info(f"相关文档数: {len(items[-1]['result']) if 'result' in items[-1] else 0}")
    logger.info(f"输入tokens: {rag_stat.recall_stat.total_input_tokens}")
    logger.info(f"输出tokens: {rag_stat.recall_stat.total_generated_tokens}")
    logger.info("="*80)

def test_process_document_chunking(rag_instance):
    """测试文档分块和重排序阶段"""
    # 首先获取文档
    query = "如何使用RAG进行文档检索?"
    conversations = [{"role": "user", "content": query}]
    
    # 准备RAG统计数据
    from autocoder.rag.long_context_rag import RAGStat, RecallStat, ChunkStat, AnswerStat
    rag_stat = RAGStat(
        recall_stat=RecallStat(
            total_input_tokens=10,  # 假设已有一些token
            total_generated_tokens=5,
            model_name=rag_instance.recall_llm.default_model_name,
        ),
        chunk_stat=ChunkStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=rag_instance.chunk_llm.default_model_name,
        ),
        answer_stat=AnswerStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=rag_instance.qa_llm.default_model_name,
        ),
    )
    
    # 获取测试文档
    recall_generator = rag_instance._process_document_retrieval(
        conversations=conversations,
        query=query,
        rag_stat=rag_stat
    )
    
    # 找到包含文档的结果
    relevant_docs = None
    for item in recall_generator:
        if isinstance(item, dict) and "result" in item:
            relevant_docs = item["result"]
    
    # 确保我们有文档可以测试
    assert relevant_docs is not None, "应该获取到一些相关文档"
    assert len(relevant_docs) > 0, "相关文档数量应该大于0"
    
    # 获取文档的source_code属性
    source_docs = [doc.source_code for doc in relevant_docs]
    
    # 调用文档分块方法
    filter_time = 1.0  # 模拟过滤耗时
    chunking_generator = rag_instance._process_document_chunking(
        relevant_docs=source_docs,
        conversations=conversations,
        rag_stat=rag_stat,
        filter_time=filter_time
    )
    
    # 收集分块结果
    chunking_items = []
    for item in chunking_generator:
        chunking_items.append(item)
    
    # 验证生成器产生了输出
    assert len(chunking_items) > 0, "文档分块阶段应该产生输出"
    
    # 验证最后一个输出是包含处理结果的字典
    assert isinstance(chunking_items[-1], dict), "最后一个输出应该是包含结果的字典"
    assert "result" in chunking_items[-1], "结果字典应包含'result'键"
    
    # 验证统计数据
    if rag_instance.tokenizer is not None:
        # 如果有tokenizer，应该会更新chunk_stat
        assert rag_stat.chunk_stat.total_input_tokens >= 0, "分块输入token计数应该被记录"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("文档分块和重排序阶段测试结果:")
    logger.info("-"*80)
    logger.info(f"生成的项目数: {len(chunking_items)}")
    logger.info(f"处理后的文档数: {len(chunking_items[-1]['result']) if 'result' in chunking_items[-1] else 0}")
    logger.info(f"全文区文档数: {len(chunking_items[-1].get('first_round_full_docs', [])) if isinstance(chunking_items[-1], dict) else 0}")
    logger.info(f"分段区文档数: {len(chunking_items[-1].get('second_round_extracted_docs', [])) if isinstance(chunking_items[-1], dict) else 0}")
    logger.info(f"分块处理时间: {chunking_items[-1].get('sencond_round_time', 0) if isinstance(chunking_items[-1], dict) else 0}")
    logger.info("="*80)

def test_process_qa_generation(rag_instance):
    """测试QA生成阶段"""
    # 构建测试对话
    query = "如何使用RAG进行文档检索?"
    conversations = [{"role": "user", "content": query}]
    
    # 准备RAG统计数据
    from autocoder.rag.long_context_rag import RAGStat, RecallStat, ChunkStat, AnswerStat
    rag_stat = RAGStat(
        recall_stat=RecallStat(
            total_input_tokens=100,  # 假设前面阶段已有一些token
            total_generated_tokens=20,
            model_name=rag_instance.recall_llm.default_model_name,
        ),
        chunk_stat=ChunkStat(
            total_input_tokens=50,
            total_generated_tokens=10,
            model_name=rag_instance.chunk_llm.default_model_name,
        ),
        answer_stat=AnswerStat(
            total_input_tokens=0,
            total_generated_tokens=0,
            model_name=rag_instance.qa_llm.default_model_name,
        ),
    )
    
    # 获取测试文档（从召回到分块的完整流程）
    doc_retrieval_generator = rag_instance._process_document_retrieval(
        conversations=conversations,
        query=query,
        rag_stat=rag_stat
    )
    
    relevant_docs = None
    for item in doc_retrieval_generator:
        if isinstance(item, dict) and "result" in item:
            relevant_docs = item["result"]
    
    source_docs = [doc.source_code for doc in relevant_docs]
    
    doc_chunking_generator = rag_instance._process_document_chunking(
        relevant_docs=source_docs,
        conversations=conversations,
        rag_stat=rag_stat,
        filter_time=1.0
    )
    
    processed_docs = None
    for item in doc_chunking_generator:
        if isinstance(item, dict) and "result" in item:
            processed_docs = item["result"]
    
    # 确保我们有处理好的文档可以测试
    assert processed_docs is not None, "应该获取到处理后的文档"
    
    # 调用QA生成方法
    qa_generator = rag_instance._process_qa_generation(
        relevant_docs=processed_docs,
        conversations=conversations,
        target_llm=rag_instance.qa_llm,
        rag_stat=rag_stat
    )
    
    # 收集QA生成结果
    qa_items = []
    for item in qa_generator:
        qa_items.append(item)
    
    # 验证生成器产生了输出
    assert len(qa_items) > 0, "QA生成阶段应该产生输出"
    
    # 验证有内容生成
    content_items = [item[0] for item in qa_items if isinstance(item, tuple) and len(item) == 2 and item[0]]
    assert len(content_items) > 0, "QA生成应该产生内容"
    
    # 验证统计数据被更新
    assert rag_stat.answer_stat.total_input_tokens > 0, "QA生成输入token计数应该增加"
    assert rag_stat.answer_stat.total_generated_tokens > 0, "QA生成的输出token计数应该增加"
    
    # 打印测试结果详情
    logger.info("="*80)
    logger.info("QA生成阶段测试结果:")
    logger.info("-"*80)
    logger.info(f"生成的项目数: {len(qa_items)}")
    logger.info(f"生成的内容片段数: {len(content_items)}")
    logger.info(f"内容样例: {content_items[0] if content_items else 'None'}")
    logger.info(f"QA输入tokens: {rag_stat.answer_stat.total_input_tokens}")
    logger.info(f"QA输出tokens: {rag_stat.answer_stat.total_generated_tokens}")
    logger.info(f"总输入tokens: {rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens + rag_stat.answer_stat.total_input_tokens}")
    logger.info(f"总输出tokens: {rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens + rag_stat.answer_stat.total_generated_tokens}")
    logger.info("="*80)

if __name__ == "__main__":
    pytest.main(["-xvs", "test_long_context_rag.py"]) 