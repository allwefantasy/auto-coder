
import os
from typing import Optional
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ListPackageInfoTool, ToolResult
from loguru import logger
import typing

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class ListPackageInfoToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ListPackageInfoTool, args):
        super().__init__(agent, tool, args)
        self.tool: ListPackageInfoTool = tool

    def resolve(self) -> ToolResult:
        source_dir = self.args.source_dir or "."
        abs_source_dir = os.path.abspath(source_dir)

        input_path = self.tool.path.strip()
        abs_input_path = os.path.abspath(os.path.join(source_dir, input_path)) if not os.path.isabs(input_path) else input_path

        # 校验输入目录是否在项目目录内
        if not abs_input_path.startswith(abs_source_dir):
            return ToolResult(success=False, message=f"Error: Access denied. Path outside project: {self.tool.path}")

        rel_package_path = os.path.relpath(abs_input_path, abs_source_dir)
        active_md_path = os.path.join(abs_source_dir, ".auto-coder", "active-context", rel_package_path, "active.md")

        logger.info(f"Looking for package info at: {active_md_path}")

        if not os.path.exists(active_md_path):
            return ToolResult(success=True, message="No package info found for this path.", content="没有相关包信息。")

        try:
            with open(active_md_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            return ToolResult(success=True, message="Successfully retrieved package info.", content=content)
        except Exception as e:
            logger.error(f"Error reading package info file: {e}")
            return ToolResult(success=False, message=f"Error reading package info file: {e}")
