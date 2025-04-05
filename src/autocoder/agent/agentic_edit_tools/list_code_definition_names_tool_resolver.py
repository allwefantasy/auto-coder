import os
from typing import Dict, Any, TYPE_CHECKING
from .base_tool_resolver import BaseToolResolver, ToolResult
from autocoder.agent.agentic_edit import ListCodeDefinitionNamesTool
from autocoder.indexer.repo_parser import RepoParser # Assuming RepoParser can handle this
from loguru import logger

if TYPE_CHECKING:
    from autocoder.auto_coder import AutoCoder

class ListCodeDefinitionNamesToolResolver(BaseToolResolver):
    def __init__(self, agent: 'AutoCoder', tool: ListCodeDefinitionNamesTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: ListCodeDefinitionNamesTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        target_path_str = self.tool.path
        source_dir = self.args.get("source_dir", ".")
        absolute_target_path = os.path.abspath(os.path.join(source_dir, target_path_str))

        # Security check
        if not absolute_target_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to analyze code outside the project directory: {target_path_str}")

        if not os.path.exists(absolute_target_path):
            return ToolResult(success=False, message=f"Error: Path not found: {target_path_str}")
        # Allow analyzing single file or directory
        # if not os.path.isdir(absolute_target_path):
        #      return ToolResult(success=False, message=f"Error: Path is not a directory: {target_path_str}")


        try:
            # Use RepoParser or a similar mechanism to extract definitions
            # RepoParser might need adjustments or a specific method for this tool's purpose.
            # This is a placeholder implementation. A real implementation needs robust code parsing.
            logger.info(f"Analyzing definitions in: {absolute_target_path}")

            # Simplified example: Use RepoParser to get symbols from files in the target path
            parser = RepoParser(base_dir=source_dir, target_dir=absolute_target_path) # Pass target_dir if RepoParser supports it
            all_symbols = []

            if os.path.isdir(absolute_target_path):
                file_paths = parser.get_file_list(absolute_target_path) # Get files within the target dir
            elif os.path.isfile(absolute_target_path):
                file_paths = [absolute_target_path]
            else:
                 return ToolResult(success=False, message=f"Error: Path is neither a file nor a directory: {target_path_str}")

            for file_path in file_paths:
                 relative_path = os.path.relpath(file_path, source_dir)
                 try:
                     symbols = parser.extract_symbols(file_path)
                     if symbols:
                         all_symbols.append({
                             "path": relative_path,
                             "definitions": [{"name": s.name, "type": s.kind.name} for s in symbols] # Example structure
                         })
                 except Exception as e:
                     logger.warning(f"Could not parse symbols from {relative_path}: {e}")


            message = f"Successfully extracted {sum(len(s['definitions']) for s in all_symbols)} definitions from {len(all_symbols)} files in '{target_path_str}'."
            logger.info(message)
            return ToolResult(success=True, message=message, content=all_symbols)

        except Exception as e:
            logger.error(f"Error extracting code definitions from '{target_path_str}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while extracting code definitions: {str(e)}")
