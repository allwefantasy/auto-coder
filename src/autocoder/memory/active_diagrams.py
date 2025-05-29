"""
活动图表模块 - 负责生成和更新 active.md 文件的 Mermaid 图表部分
"""

import re
import time
from typing import Dict, Any, Optional, Tuple
import byzerllm
from byzerllm import MetaHolder
from loguru import logger as global_logger
from autocoder.common.token_cost_caculate import TokenCostCalculator, TokenUsageStats
from autocoder.common import AutoCoderArgs


class ActiveDiagrams:
    """
    负责处理 active.md 文件的 Mermaid 图表部分
    """
    
    def __init__(self, llm: byzerllm.ByzerLLM, product_mode: str = "lite"):
        """
        初始化图表处理器
        
        Args:
            llm: ByzerLLM实例，用于生成图表内容
            product_mode: 产品模式，用于获取模型价格信息
        """
        self.llm = llm
        self.product_mode = product_mode
        self.logger = global_logger.bind(name="ActiveDiagrams")
    
    def generate_diagrams(self, context: Dict[str, Any], query: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        生成 Mermaid 图表内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 生成的图表内容和token使用统计
        """
        try:
            meta_holder = MetaHolder()
            start_time = time.monotonic()
            
            diagrams = self.generate_mermaid_diagrams.with_llm(self.llm).with_meta(
                meta_holder).run(context, query)
            
            end_time = time.monotonic()
            
            # 使用TokenCostCalculator跟踪token使用情况
            token_calculator = TokenCostCalculator(logger_name="ActiveDiagrams", args=args)
            stats: TokenUsageStats = token_calculator.track_token_usage(
                llm=self.llm,
                meta_holder=meta_holder,
                operation_name="Diagram Generation",
                start_time=start_time,
                end_time=end_time,
                product_mode=self.product_mode
            )
            
            self.logger.info(f"Diagram Generation - Total tokens: {stats.total_tokens}, Total cost: ${stats.total_cost:.6f}")
            
            return diagrams, {
                "total_tokens": stats.total_tokens,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cost": stats.total_cost
            }
        except Exception as e:
            self.logger.error(f"Error generating diagrams: {e}")
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            return f"生成图表内容时出错: {str(e)}", empty_stats
    
    def extract_diagrams(self, content: str) -> str:
        """
        从现有内容中提取图表部分
        
        Args:
            content: 现有文件内容
            
        Returns:
            str: 提取的图表部分
        """
        try:
            # 提取图表部分
            diagram_match = re.search(r'## 关系图表\s*\n(.*?)(?=\n## |$)', content, re.DOTALL)
            if diagram_match:
                diagrams = diagram_match.group(1).strip()
                self.logger.debug("Successfully extracted diagrams from existing content")
                return diagrams
            else:
                self.logger.warning("No diagrams section found in existing content")
                return ""
        except Exception as e:
            self.logger.error(f"Error extracting diagrams: {e}")
            return ""
    
    def update_diagrams(self, context: Dict[str, Any], query: str, existing_diagrams: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        更新现有的图表内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            existing_diagrams: 现有的图表内容
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 更新后的图表内容和token使用统计
        """
        try:
            meta_holder = MetaHolder()
            start_time = time.monotonic()
            
            updated_diagrams = self.update_mermaid_diagrams.with_llm(self.llm).with_meta(
                meta_holder).run(context, query, existing_diagrams)
            
            end_time = time.monotonic()
            
            # 使用TokenCostCalculator跟踪token使用情况
            token_calculator = TokenCostCalculator(logger_name="ActiveDiagrams", args=args)
            stats: TokenUsageStats = token_calculator.track_token_usage(
                llm=self.llm,
                meta_holder=meta_holder,
                operation_name="Update Diagrams",
                start_time=start_time,
                end_time=end_time,
                product_mode=self.product_mode
            )
            
            self.logger.info(f"Diagrams Update - Total tokens: {stats.total_tokens}, Total cost: ${stats.total_cost:.6f}")
            
            return updated_diagrams, {
                "total_tokens": stats.total_tokens,
                "input_tokens": stats.input_tokens,
                "output_tokens": stats.output_tokens,
                "cost": stats.total_cost
            }
        except Exception as e:
            self.logger.error(f"Error updating diagrams: {e}")
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            return f"更新图表内容时出错: {str(e)}", empty_stats
    
    @byzerllm.prompt()
    def update_mermaid_diagrams(self, context: Dict[str, Any], query: str, existing_diagrams: str) -> str:
        """
        请基于现有的"关系图表"部分和新的变更信息，生成一个更新后的"关系图表"部分。
        
        现有的"关系图表"内容：
        ```
        {{ existing_diagrams }}
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
        1. 分析现有图表的准确性，保留正确的关系信息
        2. 根据最新的变更更新文件之间的关系图
        3. 更新函数/类之间的调用关系图
        4. 如果有新文件或新函数，将它们添加到相应的图表中
        5. 确保 Mermaid 语法正确，图表清晰易读
        6. 如有冲突信息，优先保留最新信息
        
        请生成以下两个图表：
        
        ### 文件关系图
        使用 Mermaid graph 语法展示文件之间的依赖关系、导入关系等。
        
        ### 函数/类关系图  
        使用 Mermaid graph 或 classDiagram 语法展示主要函数和类之间的调用关系。
        
        你的回答应该是一个完整的"关系图表"部分内容，不需要包含标题。
        """
    
    @byzerllm.prompt()
    def generate_mermaid_diagrams(self, context: Dict[str, Any], query: str) -> str:
        """
        请根据下面的代码变更信息，生成 Mermaid 图表来展示文件之间的关系和函数之间的关系。
        
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
        
        请分析代码变更，生成以下两个 Mermaid 图表：
        
        ### 文件关系图
        分析文件之间的依赖关系、导入关系、继承关系等，使用 Mermaid graph 语法展示。
        - 显示文件之间的导入依赖
        - 标注关系类型（import、inherit、compose等）
        - 突出显示本次变更涉及的文件
        
        ### 函数/类关系图
        分析主要函数和类之间的调用关系、继承关系等，使用 Mermaid graph 或 classDiagram 语法展示。
        - 显示类的继承关系
        - 显示函数/方法的调用关系
        - 突出显示本次变更涉及的函数/类
        - 包含重要的属性和方法
        
        要求：
        1. 使用正确的 Mermaid 语法
        2. 图表要清晰易读，避免过于复杂        
        3. 添加适当的注释说明关系类型
        4. 确保图表能够帮助理解代码结构和变更影响
        
        格式示例：
        ```mermaid
        graph TD
            A[文件A] -->|包含| B[文件B]
            B -->|包含| C[文件C]
        ```
        """ 