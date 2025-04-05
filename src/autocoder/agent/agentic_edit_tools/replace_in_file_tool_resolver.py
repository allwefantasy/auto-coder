import os
import re
from typing import Dict, Any, Optional, List, Tuple
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import ReplaceInFileTool, ToolResult # Import ToolResult from types
from loguru import logger


class ReplaceInFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: ReplaceInFileTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: ReplaceInFileTool = tool # For type hinting

    def parse_diff(self, diff_content: str) -> List[Tuple[str, str]]:
        """
        Parses the diff content into a list of (search_block, replace_block) tuples.
        """
        blocks = []
        # Regex to find SEARCH/REPLACE blocks, handling potential variations in line endings
        pattern = re.compile(r"<<<<<<< SEARCH\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>> REPLACE", re.DOTALL)
        matches = pattern.findall(diff_content)
        for search_block, replace_block in matches:
            # Normalize line endings within blocks if needed, though exact match is preferred
            blocks.append((search_block, replace_block))
        if not matches and diff_content.strip():
             logger.warning(f"Could not parse any SEARCH/REPLACE blocks from diff: {diff_content}")
        return blocks

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        diff_content = self.tool.diff
        source_dir = self.args.get("source_dir", ".")
        absolute_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check
        if not absolute_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to modify file outside the project directory: {file_path}")

        if not os.path.exists(absolute_path):
            return ToolResult(success=False, message=f"Error: File not found at path: {file_path}")
        if not os.path.isfile(absolute_path):
             return ToolResult(success=False, message=f"Error: Path is not a file: {file_path}")

        try:
            with open(absolute_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
        except Exception as e:
            logger.error(f"Error reading file for replace '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while reading the file for replacement: {str(e)}")

        parsed_blocks = self.parse_diff(diff_content)
        if not parsed_blocks:
             return ToolResult(success=False, message="Error: No valid SEARCH/REPLACE blocks found in the provided diff.")

        current_content = original_content
        applied_count = 0
        errors = []

        # Apply blocks sequentially
        for i, (search_block, replace_block) in enumerate(parsed_blocks):
            # Use find() for exact, first match semantics
            start_index = current_content.find(search_block)

            if start_index != -1:
                # Replace the first occurrence
                current_content = current_content[:start_index] + replace_block + current_content[start_index + len(search_block):]
                applied_count += 1
                logger.info(f"Applied SEARCH/REPLACE block {i+1} in file {file_path}")
            else:
                error_message = f"SEARCH block {i+1} not found in the current file content. Content to search:\n---\n{search_block}\n---"
                logger.warning(error_message)
                # Log surrounding context for debugging
                context_start = max(0, original_content.find(search_block[:20]) - 100) # Approximate location
                context_end = min(len(original_content), context_start + 200 + len(search_block[:20]))
                logger.warning(f"Approximate context in file:\n---\n{original_content[context_start:context_end]}\n---")
                errors.append(error_message)
                # Stop applying further changes if one fails? Or continue? Let's continue for now.

        if applied_count == 0 and errors:
            return ToolResult(success=False, message=f"Failed to apply any changes. Errors:\n" + "\n".join(errors))

        try:
            with open(absolute_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
            logger.info(f"Successfully applied {applied_count}/{len(parsed_blocks)} changes to file: {file_path}")

            message = f"Successfully applied {applied_count}/{len(parsed_blocks)} changes to file: {file_path}."
            if errors:
                message += "\nWarnings:\n" + "\n".join(errors)

            # Return the final content (might be changed by auto-formatting later)
            return ToolResult(success=True, message=message, content=current_content)
        except Exception as e:
            logger.error(f"Error writing replaced content to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while writing the modified file: {str(e)}")
