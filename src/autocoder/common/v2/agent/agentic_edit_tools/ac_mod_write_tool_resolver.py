import os
import re
from typing import Optional, List, Tuple
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_tools.replace_in_file_tool_resolver import ReplaceInFileToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ACModWriteTool, ToolResult,ReplaceInFileTool
from loguru import logger
import typing

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class ACModWriteToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ACModWriteTool, args):
        super().__init__(agent, tool, args)
        self.tool: ACModWriteTool = tool           

    def resolve(self) -> ToolResult:
        source_dir = self.args.source_dir or "."
        input_path = self.tool.path.strip()
        
        # Check if the path already contains .ac.mod.md file name
        if input_path.endswith('.ac.mod.md'):
            # Path already includes the filename
            if not os.path.isabs(input_path):
                mod_file_path = os.path.abspath(os.path.join(source_dir, input_path))
            else:
                mod_file_path = input_path
            
            # Create the parent directory if it doesn't exist
            parent_dir = os.path.dirname(mod_file_path)
            os.makedirs(parent_dir, exist_ok=True)
        else:
            # Path is a directory, need to append .ac.mod.md
            abs_input_path = os.path.abspath(os.path.join(source_dir, input_path)) if not os.path.isabs(input_path) else input_path
            
            # Create the directory if it doesn't exist
            os.makedirs(abs_input_path, exist_ok=True)
            
            # Path to the .ac.mod.md file
            mod_file_path = os.path.join(abs_input_path, ".ac.mod.md")
        
        return ReplaceInFileToolResolver(self.agent, ReplaceInFileTool(path=mod_file_path, diff=self.tool.diff), self.args).resolve()
