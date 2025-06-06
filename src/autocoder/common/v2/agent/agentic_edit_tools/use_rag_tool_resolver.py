from typing import Dict, Any, Optional
import typing
import openai
from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import UseRAGTool, ToolResult
from autocoder.common.rag_manager import RAGManager
from loguru import logger

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit


class UseRAGToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: UseRAGTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: UseRAGTool = tool  # For type hinting
        self.rag_manager = RAGManager(args)

    def resolve(self) -> ToolResult:
        """
        通过 OpenAI SDK 访问 RAG server 来执行查询。
        """
        server_name = self.tool.server_name
        query = self.tool.query

        logger.info(f"正在解析 UseRAGTool: Server='{server_name}', Query='{query}'")

        # 检查是否有可用的 RAG 配置
        if not self.rag_manager.has_configs():
            error_msg = "未找到可用的 RAG 服务器配置，请确保配置文件存在并格式正确"
            logger.error(error_msg)
            return ToolResult(success=False, message=error_msg)

        try:
            # 查找指定的 RAG 配置
            rag_config = None
            if server_name:
                # 尝试通过名称查找
                rag_config = self.rag_manager.get_config_by_name(server_name)
                # 如果按名称找不到，尝试直接使用 server_name 作为 URL
                if not rag_config:
                    # 检查是否是直接的 URL
                    if server_name.startswith('http'):
                        # 使用提供的 server_name 作为 base_url
                        base_url = server_name
                        api_key = "dummy-key"
                    else:
                        error_msg = f"未找到名为 '{server_name}' 的 RAG 服务器配置\n\n{self.rag_manager.get_config_info()}"
                        logger.error(error_msg)
                        return ToolResult(success=False, message=error_msg)
                else:
                    base_url = rag_config.server_name
                    api_key = rag_config.api_key or "dummy-key"
            else:
                # 如果没有指定 server_name，使用第一个可用的配置
                rag_config = self.rag_manager.get_all_configs()[0]
                base_url = rag_config.server_name
                api_key = rag_config.api_key or "dummy-key"
                logger.info(f"未指定服务器名称，使用默认配置: {rag_config.name}")

            logger.info(f"使用 RAG 服务器: {base_url}")
            
            # 使用 OpenAI SDK 访问 RAG server
            client = openai.OpenAI(
                base_url=base_url,
                api_key=api_key
            )
            
            response = client.chat.completions.create(
                model="default",
                messages=[
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                max_tokens=8024
            )
            
            result_content = response.choices[0].message.content
            logger.info(f"RAG server 响应成功，内容长度: {len(result_content)}")
            
            return ToolResult(success=True, message=result_content)
            
        except Exception as e:
            error_msg = f"访问 RAG server 时出错: {str(e)}"
            if not self.rag_manager.has_configs():
                error_msg += f"\n\n{self.rag_manager.get_config_info()}"
            logger.error(error_msg)
            return ToolResult(success=False, message=error_msg) 