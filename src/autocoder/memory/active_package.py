"""
活动包 - 生成目录的活动上下文文档
"""

from typing import Dict, Any, Optional, Tuple, List
import os
import sys
import re
import byzerllm
from byzerllm import MetaHolder
import time
from loguru import logger as global_logger
from autocoder.common.token_cost_caculate import TokenCostCalculator, TokenUsageStats
from autocoder.common import AutoCoderArgs

# 导入新的独立模块
from .active_header import ActiveHeader
from .active_changes import ActiveChanges
from .active_documents import ActiveDocuments
from .active_diagrams import ActiveDiagrams

class ActivePackage:
    """
    ActivePackage负责生成每个目录的活动上下文文档，
    包括当前变更信息和相关文件的详细文档。
    
    如果目录中已存在active.md文件，会先读取现有内容作为参考，
    然后基于现有信息和新信息一起生成更新后的文档。
    """
    
    def __init__(self, llm: byzerllm.ByzerLLM, product_mode: str = "lite"):
        """
        初始化活动包生成器
        
        Args:
            llm: ByzerLLM实例，用于生成文档内容
            product_mode: 产品模式，用于获取模型价格信息
        """
        self.llm = llm
        self.product_mode = product_mode
        # 创建专用的 logger 实例
        self.logger = global_logger.bind(name="ActivePackage")
        
        # 初始化四个独立的处理模块
        self.header_processor = ActiveHeader()
        self.changes_processor = ActiveChanges(llm, product_mode)
        self.documents_processor = ActiveDocuments(llm, product_mode)
        self.diagrams_processor = ActiveDiagrams(llm, product_mode)
    
    def generate_active_file(self, context: Dict[str, Any], query: str, 
                            existing_file_path: Optional[str] = None, 
                            file_changes: Optional[Dict[str, Tuple[str, str]]] = None,
                            args: Optional[AutoCoderArgs] = None) -> Tuple[str, Dict[str, Any]]:
        """
        生成完整的活动文件内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            existing_file_path: 可选的现有文件路径，如果提供，将读取并参考现有内容
            file_changes: 文件变更字典，键为文件路径，值为(变更前内容, 变更后内容)的元组
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 生成的活动文件内容和token使用及费用信息
        """
        try:
            # 初始化token和费用统计
            total_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            
            # 检查是否有现有文件
            existing_content = None
            if existing_file_path and os.path.exists(existing_file_path):
                try:
                    with open(existing_file_path, 'r', encoding='utf-8') as f:
                        existing_content = f.read()
                    self.logger.info(f"Found existing active.md file: {existing_file_path}")
                except Exception as e:
                    self.logger.error(f"Error reading existing file {existing_file_path}: {e}")
            
            # 增强上下文信息，添加文件变更信息
            enhanced_context = self._enhance_context_with_changes(context, file_changes)
            
            # 根据是否有现有内容选择不同的生成方式
            if existing_content:
                # 有现有内容，使用更新模式
                file_content, usage_stats = self.generate_updated_active_file(enhanced_context, query, existing_content, args)
                # 合并token和费用统计
                total_stats["total_tokens"] += usage_stats["total_tokens"]
                total_stats["input_tokens"] += usage_stats["input_tokens"]
                total_stats["output_tokens"] += usage_stats["output_tokens"]
                total_stats["cost"] += usage_stats["cost"]
            else:
                # 无现有内容，使用创建模式
                file_content, usage_stats = self.generate_new_active_file(enhanced_context, query, args)
                # 合并token和费用统计
                total_stats["total_tokens"] += usage_stats["total_tokens"]
                total_stats["input_tokens"] += usage_stats["input_tokens"]
                total_stats["output_tokens"] += usage_stats["output_tokens"]
                total_stats["cost"] += usage_stats["cost"]
            
            return file_content, total_stats
        except Exception as e:
            self.logger.error(f"Error generating active file: {e}")
            # 创建空统计
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            # 返回错误信息和空统计
            dir_name = os.path.basename(context.get('directory_path', '未知目录')) if context else '未知目录'
            return f"# 生成文档时出错 - {dir_name}\n\n错误: {str(e)}", empty_stats
    
    def _enhance_context_with_changes(self, context: Dict[str, Any], 
                                    file_changes: Optional[Dict[str, Tuple[str, str]]]) -> Dict[str, Any]:
        """
        使用文件变更信息增强上下文
        
        Args:
            context: 原始上下文字典
            file_changes: 文件变更字典
            
        Returns:
            Dict[str, Any]: 增强后的上下文字典
        """
        # 增加空值检查
        if not context:
            self.logger.warning("调用_enhance_context_with_changes时传入空context")
            return {}
            
        if not file_changes:
            return context
        
        # 创建上下文的深拷贝，避免修改原始内容
        enhanced_context = context.copy()
        
        # 添加文件变更信息到changed_files
        if 'changed_files' in enhanced_context:
            changed_files_with_diffs = []
            for file_info in enhanced_context['changed_files']:
                file_path = file_info['path']
                # 创建文件信息的副本
                new_file_info = file_info.copy()
                
                # 添加变更内容（如果有）
                if file_path in file_changes:
                    before_content, after_content = file_changes[file_path]
                    new_file_info['before_content'] = before_content
                    new_file_info['after_content'] = after_content
                    new_file_info['has_diff'] = True
                
                changed_files_with_diffs.append(new_file_info)
            
            enhanced_context['changed_files'] = changed_files_with_diffs
        
        # 在上下文中添加文件变更摘要信息
        file_diffs = []
        for file_path, (before, after) in file_changes.items():
            if before and after:
                # 简单计算差异 - 实际应用中可能需要更复杂的差异计算
                diff_info = {
                    'path': file_path,
                    'type': 'modified',
                    'before_lines': len(before.split('\n')) if before else 0,
                    'after_lines': len(after.split('\n')) if after else 0
                }
            elif not before and after:
                diff_info = {'path': file_path, 'type': 'added'}
            elif before and not after:
                diff_info = {'path': file_path, 'type': 'deleted'}
            else:
                continue
                
            file_diffs.append(diff_info)
        
        enhanced_context['file_diffs'] = file_diffs
        
        return enhanced_context
    
    def generate_new_active_file(self, context: Dict[str, Any], query: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        生成全新的活动文件内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 新生成的活动文件内容和token使用及费用信息
        """
        try:
            # 初始化总统计
            total_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            
            # 1. 生成标题部分
            header = self.header_processor.generate_header(context)
            
            # 2. 生成当前变更部分
            current_change, changes_stats = self.changes_processor.generate_changes(context, query, args)
            # 合并统计
            total_stats["total_tokens"] += changes_stats["total_tokens"]
            total_stats["input_tokens"] += changes_stats["input_tokens"]
            total_stats["output_tokens"] += changes_stats["output_tokens"]
            total_stats["cost"] += changes_stats["cost"]
            
            # 3. 生成文档部分
            document, document_stats = self.documents_processor.generate_documents(context, query, args)
            # 合并统计
            total_stats["total_tokens"] += document_stats["total_tokens"]
            total_stats["input_tokens"] += document_stats["input_tokens"]
            total_stats["output_tokens"] += document_stats["output_tokens"]
            total_stats["cost"] += document_stats["cost"]
            
            # 4. 生成关系图表部分
            diagrams, diagrams_stats = self.diagrams_processor.generate_diagrams(context, query, args)
            # 合并统计
            total_stats["total_tokens"] += diagrams_stats["total_tokens"]
            total_stats["input_tokens"] += diagrams_stats["input_tokens"]
            total_stats["output_tokens"] += diagrams_stats["output_tokens"]
            total_stats["cost"] += diagrams_stats["cost"]
            
            self.logger.info(f"Total Usage - Tokens: {total_stats['total_tokens']}, Input: {total_stats['input_tokens']}, Output: {total_stats['output_tokens']}, Cost: ${total_stats['cost']:.6f}")
            
            # 5. 组合成完整的活动文件内容
            file_content = header
            file_content += f"## 当前变更\n\n{current_change}\n\n"
            file_content += f"## 文档\n\n{document}\n\n"
            file_content += f"## 关系图表\n\n{diagrams}\n"
            
            return file_content, total_stats
        except Exception as e:
            self.logger.error(f"Error generating new active file: {e}")
            # 返回错误信息和空统计
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            err_content = f"# 生成文档时出错 - {os.path.basename(context.get('directory_path', '未知目录'))}\n\n错误: {str(e)}"
            return err_content, empty_stats
    
    def extract_sections(self, content: str) -> Tuple[str, str, str, str]:
        """
        从现有内容中提取标题、当前变更、文档和图表部分
        
        Args:
            content: 现有文件内容
            
        Returns:
            Tuple[str, str, str, str]: 标题部分、当前变更部分、文档部分、图表部分
        """
        try:
            # 使用各个处理器提取对应部分
            header = self.header_processor.extract_header(content)
            current_change_section = self.changes_processor.extract_changes(content)
            document_section = self.documents_processor.extract_documents(content)
            diagrams_section = self.diagrams_processor.extract_diagrams(content)
            
            return header, current_change_section, document_section, diagrams_section
        except Exception as e:
            self.logger.error(f"Error extracting sections: {e}")
            # 返回默认值
            default_header = "# 活动上下文\n\n"
            return default_header, "", "", ""
    
    def generate_updated_active_file(self, context: Dict[str, Any], query: str, existing_content: str, args: AutoCoderArgs) -> Tuple[str, Dict[str, Any]]:
        """
        基于现有内容生成更新后的活动文件内容
        
        Args:
            context: 目录上下文字典
            query: 用户查询/需求
            existing_content: 现有的活动文件内容
            args: AutoCoderArgs实例，包含配置信息
            
        Returns:
            Tuple[str, Dict[str, Any]]: 更新后的活动文件内容和token使用及费用信息
        """
        try:
            # 初始化总统计
            total_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            
            # 1. 从现有内容中提取各部分
            header, existing_current_change, existing_document, existing_diagrams = self.extract_sections(existing_content)
            
            # 2. 更新标题部分
            updated_header = self.header_processor.update_header(context, header)
            
            # 3. 更新当前变更部分
            updated_current_change, changes_stats = self.changes_processor.update_changes(
                context, query, existing_current_change, args)
            # 合并统计
            total_stats["total_tokens"] += changes_stats["total_tokens"]
            total_stats["input_tokens"] += changes_stats["input_tokens"]
            total_stats["output_tokens"] += changes_stats["output_tokens"]
            total_stats["cost"] += changes_stats["cost"]
            
            # 4. 更新文档部分
            updated_document, document_stats = self.documents_processor.update_documents(
                context, query, existing_document, args)
            # 合并统计
            total_stats["total_tokens"] += document_stats["total_tokens"]
            total_stats["input_tokens"] += document_stats["input_tokens"]
            total_stats["output_tokens"] += document_stats["output_tokens"]
            total_stats["cost"] += document_stats["cost"]
            
            # 5. 更新关系图表部分
            updated_diagrams, diagrams_stats = self.diagrams_processor.update_diagrams(
                context, query, existing_diagrams, args)
            # 合并统计
            total_stats["total_tokens"] += diagrams_stats["total_tokens"]
            total_stats["input_tokens"] += diagrams_stats["input_tokens"]
            total_stats["output_tokens"] += diagrams_stats["output_tokens"]
            total_stats["cost"] += diagrams_stats["cost"]
            
            self.logger.info(f"Total Usage - Tokens: {total_stats['total_tokens']}, Input: {total_stats['input_tokens']}, Output: {total_stats['output_tokens']}, Cost: ${total_stats['cost']:.6f}")
            
            # 6. 组合成完整的活动文件内容
            file_content = updated_header
            file_content += f"## 当前变更\n\n{updated_current_change}\n\n"
            file_content += f"## 文档\n\n{updated_document}\n\n"
            file_content += f"## 关系图表\n\n{updated_diagrams}\n"
            
            return file_content, total_stats
        except Exception as e:
            self.logger.error(f"Error updating active file: {e}")
            # 返回错误信息和空统计
            empty_stats = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cost": 0.0
            }
            dir_name = os.path.basename(context.get('directory_path', '未知目录'))
            err_content = f"# 更新文档时出错 - {dir_name}\n\n错误: {str(e)}\n\n## 原始内容\n\n{existing_content}"
            return err_content, empty_stats 