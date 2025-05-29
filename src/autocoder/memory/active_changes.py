"""
当前变更模块 - 负责生成和更新 active.md 文件的当前变更部分
"""

import re
import time
from typing import Dict, Any, Optional, Tuple
import byzerllm
from byzerllm import MetaHolder
from loguru import logger as global_logger
from autocoder.common.token_cost_caculate import TokenCostCalculator, TokenUsageStats
from autocoder.common import AutoCoderArgs


class ActiveChanges:
    """
    负责处理 active.md 文件的当前变更部分
    """
    
    def __init__(self, llm: byzerllm.ByzerLLM, product_mode: str = "lite"):
        """
        初始化当前变更处理器
        
        Args:
            llm: ByzerLLM实例，用于生成变更内容
            product_mode: 产品模式，用于获取模型价格信息
        """
        self.llm = llm
        self.product_mode = product_mode
        self.logger = global_logger.bind(name="ActiveChanges")
    
    def generate_changes(self, context: Dict[str, Any], query: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        生成当前变更内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 生成的变更内容和token使用统计
        """
        try:
            meta_holder = MetaHolder()
            start_time = time.monotonic()
            
            current_change = self.generate_current_change.with_llm(self.llm).with_meta(
                meta_holder).run(context, query)
            
            end_time = time.monotonic()
            
            # 使用TokenCostCalculator跟踪token使用情况
            token_calculator = TokenCostCalculator(logger_name="ActiveChanges", args=args)
            stats: TokenUsageStats = token_calculator.track_token_usage(
                llm=self.llm,
                meta_holder=meta_holder,
                operation_name="Current Change Generation",
                start_time=start_time,
                end_time=end_time,
                product_mode=self.product_mode
            )
            
            self.logger.info(f"Current Change Generation - Total tokens: {stats.total_tokens}, Total cost: ${stats.total_cost:.6f}")
            
            return current_change, {
                "total_tokens": stats.total_tokens,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cost": stats.total_cost
            }
        except Exception as e:
            self.logger.error(f"Error generating changes: {e}")
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            return f"生成变更内容时出错: {str(e)}", empty_stats
    
    def extract_changes(self, content: str) -> str:
        """
        从现有内容中提取当前变更部分
        
        Args:
            content: 现有文件内容
            
        Returns:
            str: 提取的当前变更部分
        """
        try:
            # 提取当前变更部分
            current_change_match = re.search(r'## 当前变更\s*\n(.*?)(?=\n## |$)', content, re.DOTALL)
            if current_change_match:
                changes = current_change_match.group(1).strip()
                self.logger.debug("Successfully extracted changes from existing content")
                return changes
            else:
                self.logger.warning("No changes section found in existing content")
                return ""
        except Exception as e:
            self.logger.error(f"Error extracting changes: {e}")
            return ""
    
    def update_changes(self, context: Dict[str, Any], query: str, existing_changes: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        更新现有的当前变更内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            existing_changes: 现有的变更内容
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 更新后的变更内容和token使用统计
        """
        try:
            meta_holder = MetaHolder()
            start_time = time.monotonic()
            
            updated_changes = self.update_current_change.with_llm(self.llm).with_meta(
                meta_holder).run(context, query, existing_changes)
            
            end_time = time.monotonic()
            
            # 使用TokenCostCalculator跟踪token使用情况
            token_calculator = TokenCostCalculator(logger_name="ActiveChanges", args=args)
            stats: TokenUsageStats = token_calculator.track_token_usage(
                llm=self.llm,
                meta_holder=meta_holder,
                operation_name="Update Current Change",
                start_time=start_time,
                end_time=end_time,
                product_mode=self.product_mode
            )
            
            self.logger.info(f"Current Change Update - Total tokens: {stats.total_tokens}, Total cost: ${stats.total_cost:.6f}")
            
            return updated_changes, {
                "total_tokens": stats.total_tokens,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cost": stats.total_cost
            }
        except Exception as e:
            self.logger.error(f"Error updating changes: {e}")
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            return f"更新变更内容时出错: {str(e)}", empty_stats
    
    @byzerllm.prompt()
    def update_current_change(self, context: Dict[str, Any], query: str, existing_current_change: str) -> str:
        """
        请基于现有的"当前变更"文档和新的变更信息，生成一个更新后的"当前变更"部分。
        
        现有的"当前变更"内容：
        ```
        {{ existing_current_change }}
        ```
        
        当前需求：
        {{ query }}
        
        目录：{{ context.directory_path }}
        
        最新变更的文件：
        {% for file in context.changed_files %}
        - {{ file.path }}
        {% endfor %}
        
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
        1. 保留现有文档中的有用历史信息
        2. 添加最新的变更信息，重点描述当前需求相关的变更
        3. 明确指出新的变更与之前变更的关系（如继续完善、修复问题、新增功能等）
        4. 确保变更描述清晰、具体，并表明每个文件的变更内容和目的
        5. 如果有冲突的信息，优先保留最新的信息
        6. 变更部分最多保留20条。
        
        你的回答应该是一个完整的"当前变更"部分内容，不需要包含标题。
        """
    
    @byzerllm.prompt()
    def generate_current_change(self, context: Dict[str, Any], query: str) -> str:
        """
        请分析下面的代码变更，并描述它们与当前需求的关系。
        
        需求：
        {{ query }}
        
        目录：{{ context.directory_path }}
        
        变更的文件：
        {% for file in context.changed_files %}
        - {{ file.path }}
        {% endfor %}
        
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
        
        分析并描述这些变更如何满足需求，以及这个目录中的文件在整体变更中起到什么作用。
        描述应该清晰、具体，并表明每个文件的变更内容和目的。
        """ 