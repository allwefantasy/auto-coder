"""
文件文档模块 - 负责生成和更新 active.md 文件的文档部分
"""

import re
import time
from typing import Dict, Any, Optional, Tuple
import byzerllm
from byzerllm import MetaHolder
from loguru import logger as global_logger
from autocoder.common.token_cost_caculate import TokenCostCalculator, TokenUsageStats
from autocoder.common import AutoCoderArgs


class ActiveDocuments:
    """
    负责处理 active.md 文件的文档部分
    """
    
    def __init__(self, llm: byzerllm.ByzerLLM, product_mode: str = "lite"):
        """
        初始化文档处理器
        
        Args:
            llm: ByzerLLM实例，用于生成文档内容
            product_mode: 产品模式，用于获取模型价格信息
        """
        self.llm = llm
        self.product_mode = product_mode
        self.logger = global_logger.bind(name="ActiveDocuments")
    
    def generate_documents(self, context: Dict[str, Any], query: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        生成文档内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 生成的文档内容和token使用统计
        """
        try:
            meta_holder = MetaHolder()
            start_time = time.monotonic()
            
            document = self.generate_document.with_llm(self.llm).with_meta(
                meta_holder).run(context, query)
            
            end_time = time.monotonic()
            
            # 使用TokenCostCalculator跟踪token使用情况
            token_calculator = TokenCostCalculator(logger_name="ActiveDocuments", args=args)
            stats: TokenUsageStats = token_calculator.track_token_usage(
                llm=self.llm,
                meta_holder=meta_holder,
                operation_name="Document Generation",
                start_time=start_time,
                end_time=end_time,
                product_mode=self.product_mode
            )
            
            self.logger.info(f"Document Generation - Total tokens: {stats.total_tokens}, Total cost: ${stats.total_cost:.6f}")
            
            return document, {
                "total_tokens": stats.total_tokens,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cost": stats.total_cost
            }
        except Exception as e:
            self.logger.error(f"Error generating documents: {e}")
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            return f"生成文档内容时出错: {str(e)}", empty_stats
    
    def extract_documents(self, content: str) -> str:
        """
        从现有内容中提取文档部分
        
        Args:
            content: 现有文件内容
            
        Returns:
            str: 提取的文档部分
        """
        try:
            # 提取文档部分
            document_match = re.search(r'## 文档\s*\n(.*?)(?=\n## |$)', content, re.DOTALL)
            if document_match:
                document = document_match.group(1).strip()
                self.logger.debug("Successfully extracted documents from existing content")
                return document
            else:
                self.logger.warning("No documents section found in existing content")
                return ""
        except Exception as e:
            self.logger.error(f"Error extracting documents: {e}")
            return ""
    
    def update_documents(self, context: Dict[str, Any], query: str, existing_document: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        更新现有的文档内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            existing_document: 现有的文档内容
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 更新后的文档内容和token使用统计
        """
        try:
            meta_holder = MetaHolder()
            start_time = time.monotonic()
            
            updated_document = self.update_document.with_llm(self.llm).with_meta(
                meta_holder).run(context, query, existing_document)
            
            end_time = time.monotonic()
            
            # 使用TokenCostCalculator跟踪token使用情况
            token_calculator = TokenCostCalculator(logger_name="ActiveDocuments", args=args)
            stats: TokenUsageStats = token_calculator.track_token_usage(
                llm=self.llm,
                meta_holder=meta_holder,
                operation_name="Update Document",
                start_time=start_time,
                end_time=end_time,
                product_mode=self.product_mode
            )
            
            self.logger.info(f"Document Update - Total tokens: {stats.total_tokens}, Total cost: ${stats.total_cost:.6f}")
            
            return updated_document, {
                "total_tokens": stats.total_tokens,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cost": stats.total_cost
            }
        except Exception as e:
            self.logger.error(f"Error updating documents: {e}")
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            return f"更新文档内容时出错: {str(e)}", empty_stats
    
    @byzerllm.prompt()
    def update_document(self, context: Dict[str, Any], query: str, existing_document: str) -> str:
        """
        请基于现有的"文档"部分和新的变更信息，生成一个更新后的"文档"部分。
        
        现有的"文档"内容：
        ```
        {{ existing_document }}
        ```
        
        当前需求：
        {{ query }}
        
        目录：{{ context.directory_path }}
        
        相关文件：
        {% for file in context.changed_files %}
        - {{ file.path }}
        {% endfor %}
        
        {% if context.current_files %}
        当前目录中的其他相关文件：
        {% for file in context.current_files %}
        - {{ file.path }}
        {% endfor %}
        {% endif %}
        
        {% if context.file_diffs %}
        文件变更摘要：
        {% for diff in context.file_diffs %}
        - {{ diff.path }}: {% if diff.type == 'modified' %}修改 (从{{ diff.before_lines }}行到{{ diff.after_lines }}行){% elif diff.type == 'added' %}新增{% elif diff.type == 'deleted' %}删除{% endif %}
        {% endfor %}
        {% endif %}
        
        {% if context.changed_files and context.changed_files[0].has_diff %}
        变更前后的代码对比：
        {% for file in context.changed_files %}
        {% if file.has_diff %}
        文件: {{ file.path }}
        变更前:
        ```
        {{ file.before_content }}
        ```
        
        变更后:
        ```
        {{ file.after_content }}
        ```
        {% endif %}
        {% endfor %}
        {% endif %}
        
        请执行以下任务：
        1. 保留现有文档中的准确信息
        2. 更新每个文件的文档，反映最新的变更
        3. 如果有新文件，为其创建完整的文档
        4. 确保文档格式一致性，每个文件的文档包含：功能、关键组件、变更影响、与其他文件的关系
        5. 如有冲突信息，优先保留最新信息，但保留历史上下文
        
        格式应为：
        
        ### [文件名]
        - **功能**：
        - **关键组件**：
        - **变更影响**：
        - **关系**：
        
        你的回答应该是一个完整的"文档"部分内容，不需要包含标题。
        """
    
    @byzerllm.prompt()
    def generate_document(self, context: Dict[str, Any], query: str) -> str:
        """
        请为下面列出的每个文件生成详细的文档说明。
        
        需求：
        {{ query }}
        
        目录：{{ context.directory_path }}
        
        文件列表：
        {% for file in context.changed_files %}
        - {{ file.path }}
        {% endfor %}
        
        {% if context.current_files %}
        当前目录中的其他相关文件：
        {% for file in context.current_files %}
        - {{ file.path }}
        {% endfor %}
        {% endif %}
        
        {% if context.file_diffs %}
        文件变更摘要：
        {% for diff in context.file_diffs %}
        - {{ diff.path }}: {% if diff.type == 'modified' %}修改 (从{{ diff.before_lines }}行到{{ diff.after_lines }}行){% elif diff.type == 'added' %}新增{% elif diff.type == 'deleted' %}删除{% endif %}
        {% endfor %}
        {% endif %}
        
        {% if context.changed_files and context.changed_files[0].has_diff %}
        变更前后的代码对比：
        {% for file in context.changed_files %}
        {% if file.has_diff %}
        文件: {{ file.path }}
        变更前:
        ```
        {{ file.before_content }}
        ```
        
        变更后:
        ```
        {{ file.after_content }}
        ```
        {% endif %}
        {% endfor %}
        {% endif %}
        
        对于每个文件，请提供：
        1. 文件的主要功能
        2. 文件中的关键组件（类、函数等）
        3. 此次变更对文件的影响（如果适用）
        4. 文件与其他文件的关系
        
        格式应为：
        
        ### [文件名]
        - **功能**：
        - **关键组件**：
        - **变更影响**：
        - **关系**：
        """ 