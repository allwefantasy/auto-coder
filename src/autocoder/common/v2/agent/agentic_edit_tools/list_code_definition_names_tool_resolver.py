import os
from typing import Dict, Any, Optional
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ListCodeDefinitionNamesTool, ToolResult # Import ToolResult from types
import json
from autocoder.index.index import IndexManager
from loguru import logger
import traceback
from autocoder.index.symbols_utils import (
    extract_symbols,
    SymbolType,
    symbols_info_to_str,
)
import typing
from autocoder.common import AutoCoderArgs

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit


class ListCodeDefinitionNamesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ListCodeDefinitionNamesTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ListCodeDefinitionNamesTool = tool # For type hinting
        self.llm = self.agent.llm

    def _get_index(self):        
        index_manager = IndexManager(
            llm=self.llm, sources=[], args=self.args)
        return index_manager
    
    def resolve(self) -> ToolResult:

        index_items = self._get_index().read_index()
        index_data = {item.module_name: item for item in index_items}

        target_path_str = self.tool.path
        source_dir = self.args.source_dir or "."
        absolute_target_path = os.path.abspath(os.path.join(source_dir, target_path_str))

        # Security check
        if not absolute_target_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to analyze code outside the project directory: {target_path_str}")

        if not os.path.exists(absolute_target_path):
            return ToolResult(success=False, message=f"Error: Path not found: {target_path_str}")        

        try:
            # Use RepoParser or a similar mechanism to extract definitions
            # RepoParser might need adjustments or a specific method for this tool's purpose.
            # This is a placeholder implementation. A real implementation needs robust code parsing.
            logger.info(f"Analyzing definitions in: {absolute_target_path}")                        
            all_symbols = []
            
            if os.path.isfile(absolute_target_path):
                file_paths = [absolute_target_path]
            else:
                 return ToolResult(success=False, message=f"Error: Path is neither a file nor a directory: {target_path_str}")

            for file_path in file_paths:                
                try:
                    item = index_data[file_path]
                    symbols_str = item.symbols            
                    symbols = extract_symbols(symbols_str)
                    if symbols:
                        all_symbols.append({
                            "path": file_path,
                            "definitions": [{"name": s, "type": "function"} for s in symbols.functions]  +  [{"name": s, "type": "variable"} for s in symbols.variables] + [{"name": s, "type": "class"} for s in symbols.classes]
                        })
                except Exception as e:
                    logger.warning(f"Could not parse symbols from {file_path}: {e}")


            message = f"Successfully extracted {sum(len(s['definitions']) for s in all_symbols)} definitions from {len(all_symbols)} files in '{target_path_str}'."
            logger.info(message)
            return ToolResult(success=True, message=message, content=all_symbols)

        except Exception as e:
            logger.error(f"Error extracting code definitions from '{target_path_str}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while extracting code definitions: {str(e)}")
