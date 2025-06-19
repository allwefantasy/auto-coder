"""
输出格式化器模块

提供不同格式的输出处理，支持文本、JSON和流式JSON格式。
"""

import json
import asyncio
from typing import Any, Dict, AsyncIterator, Union, Optional


class OutputFormatter:
    """输出格式化器，处理不同格式的输出。"""
    
    def __init__(self, verbose: bool = False):
        """
        初始化输出格式化器。
        
        Args:
            verbose: 是否输出详细信息
        """
        self.verbose = verbose
    
    def format_text(self, content: Union[str, Dict[str, Any]]) -> str:
        """
        格式化为文本输出。
        
        Args:
            content: 要格式化的内容，可以是字符串或字典
            
        Returns:
            格式化后的文本
        """
        if isinstance(content, dict):
            # 如果是字典，提取主要内容
            if "content" in content:
                result = content["content"]
            else:
                result = str(content)
        else:
            result = str(content)
            
        if self.verbose:
            # 在详细模式下添加调试信息
            debug_info = self._get_debug_info(content)
            if debug_info:
                result += f"\n\n[DEBUG]\n{debug_info}"
                
        return result
    
    def format_json(self, content: Any) -> str:
        """
        格式化为JSON输出。
        
        Args:
            content: 要格式化的内容
            
        Returns:
            JSON格式的字符串
        """
        # 确保内容可以被序列化为JSON
        if isinstance(content, str):
            try:
                # 尝试解析为JSON
                parsed = json.loads(content)
                content = parsed
            except json.JSONDecodeError:
                # 如果不是有效的JSON，则包装为字典
                content = {"content": content}
        
        # 添加调试信息（如果启用详细模式）
        if self.verbose and isinstance(content, dict):
            content["debug"] = self._get_debug_info_dict(content)
            
        return json.dumps(content, ensure_ascii=False, indent=2)
    
    async def format_stream_json(self, stream: AsyncIterator[Any]) -> AsyncIterator[str]:
        """
        格式化为流式JSON输出。
        
        Args:
            stream: 异步迭代器，提供流式内容
            
        Yields:
            JSON格式的字符串，每行一个JSON对象
        """
        async for item in stream:
            # 处理不同类型的项
            if isinstance(item, dict):
                output = item
            elif isinstance(item, str):
                try:
                    output = json.loads(item)
                except json.JSONDecodeError:
                    output = {"content": item, "type": "text"}
            else:
                output = {"content": str(item), "type": "text"}
            
            # 添加调试信息（如果启用详细模式）
            if self.verbose:
                output["debug"] = self._get_debug_info_dict(output)
                
            yield json.dumps(output, ensure_ascii=False)
    
    def _get_debug_info(self, content: Any) -> str:
        """
        获取调试信息的文本表示。
        
        Args:
            content: 内容对象
            
        Returns:
            调试信息文本
        """
        debug_dict = self._get_debug_info_dict(content)
        if debug_dict:
            return json.dumps(debug_dict, ensure_ascii=False, indent=2)
        return ""
    
    def _get_debug_info_dict(self, content: Any) -> Dict[str, Any]:
        """
        获取调试信息的字典表示。
        
        Args:
            content: 内容对象
            
        Returns:
            调试信息字典
        """
        debug_info = {}
        
        # 从内容中提取元数据
        if isinstance(content, dict):
            if "metadata" in content:
                debug_info["metadata"] = content["metadata"]
            
            # 提取令牌计数信息
            if "tokens" in content:
                debug_info["tokens"] = content["tokens"]
            elif "metadata" in content and "tokens" in content["metadata"]:
                debug_info["tokens"] = content["metadata"]["tokens"]
                
            # 提取模型信息
            if "model" in content:
                debug_info["model"] = content["model"]
            elif "metadata" in content and "model" in content["metadata"]:
                debug_info["model"] = content["metadata"]["model"]
                
            # 提取时间信息
            if "timestamp" in content:
                debug_info["timestamp"] = content["timestamp"]
            elif "metadata" in content and "timestamp" in content["metadata"]:
                debug_info["timestamp"] = content["metadata"]["timestamp"]
        
        return debug_info


class InputFormatter:
    """输入格式化器，处理不同格式的输入。"""
    
    def format_text(self, content: str) -> str:
        """
        格式化文本输入。
        
        Args:
            content: 输入文本
            
        Returns:
            格式化后的文本
        """
        return content.strip()
    
    def format_json(self, content: str) -> Dict[str, Any]:
        """
        格式化JSON输入。
        
        Args:
            content: JSON格式的输入字符串
            
        Returns:
            解析后的字典
            
        Raises:
            ValueError: 如果输入不是有效的JSON
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"无效的JSON输入: {str(e)}")
    
    async def format_stream_json(self, content: str) -> AsyncIterator[Dict[str, Any]]:
        """
        格式化流式JSON输入。
        
        Args:
            content: 包含多行JSON对象的字符串
            
        Yields:
            解析后的字典
            
        Raises:
            ValueError: 如果某行不是有效的JSON
        """
        for line in content.strip().split("\n"):
            if not line.strip():
                continue
                
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"无效的JSON行: {line}, 错误: {str(e)}")
