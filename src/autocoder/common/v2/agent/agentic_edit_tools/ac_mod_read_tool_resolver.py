
import os
from typing import Optional
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ACModReadTool, ToolResult
from loguru import logger
import typing

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class ACModReadToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ACModReadTool, args):
        super().__init__(agent, tool, args)
        self.tool: ACModReadTool = tool

    def resolve(self) -> ToolResult:
        source_dir = self.args.source_dir or "."        
        input_path = self.tool.path.strip()
        abs_input_path = os.path.abspath(os.path.join(source_dir, input_path)) if not os.path.isabs(input_path) else input_path

        # # 校验输入目录是否在项目目录内
        # if not abs_input_path.startswith(abs_source_dir):
        #     return ToolResult(success=False, message=f"Error: Access denied. Path outside project: {self.tool.path}")

        # 直接在输入文件夹中查找 .ac.mod.md 文件
        mod_file_path = os.path.join(abs_input_path, ".ac.mod.md")
        
        logger.info(f"Looking for package info at: {mod_file_path}")

        if not os.path.exists(mod_file_path):
            return ToolResult(success=True, message=f"The path {self.tool.path} is NOT AC module.", content="")

        try:
            with open(mod_file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return ToolResult(success=True, message="The path {self.tool.path} is AC module.", content=content)
        except Exception as e:
            logger.error(f"Error reading package info file: {e}")
            return ToolResult(success=False, message=f"Error reading {self.tool.path}/.ac.mod.md file: {e}")
