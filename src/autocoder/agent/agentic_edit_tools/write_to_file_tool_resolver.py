import os
import re
from typing import Dict, Any, Optional, List, Tuple
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import WriteToFileTool, ToolResult  # Import ToolResult from types
from loguru import logger


class WriteToFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: WriteToFileTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: WriteToFileTool = tool  # For type hinting

    def parse_diff(self, diff_content: str) -> List[Tuple[str, str]]:
        """
        Parses the diff content into a list of (search_block, replace_block) tuples.
        """
        blocks = []
        # Regex to find SEARCH/REPLACE blocks, handling potential variations in line endings
        pattern = re.compile(r"<<<<<<< SEARCH\r?\n(.*?)\r?\n=======\r?\n(.*?)\r?\n>>>>>>> REPLACE", re.DOTALL)
        matches = pattern.findall(diff_content)
        for search_block, replace_block in matches:
            blocks.append((search_block, replace_block))
        if not matches and diff_content.strip():
            logger.warning(f"Could not parse any SEARCH/REPLACE blocks from diff: {diff_content}")
        return blocks

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        content = self.tool.content
        source_dir = self.args.source_dir or "."
        absolute_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check: ensure the path is within the source directory
        if not absolute_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to write file outside the project directory: {file_path}")

        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            # Check if the content contains SEARCH/REPLACE blocks
            parsed_blocks = self.parse_diff(content)
            if parsed_blocks:
                # If file exists, read its current content
                if os.path.exists(absolute_path):
                    try:
                        with open(absolute_path, 'r', encoding='utf-8', errors='replace') as f:
                            original_content = f.read()
                    except Exception as e:
                        logger.error(f"Error reading existing file '{file_path}' for diff apply: {str(e)}")
                        return ToolResult(success=False, message=f"An error occurred while reading the existing file: {str(e)}")
                else:
                    # If file does not exist, start with empty content
                    original_content = ""

                current_content = original_content
                applied_count = 0
                errors = []

                for i, (search_block, replace_block) in enumerate(parsed_blocks):
                    start_index = current_content.find(search_block)
                    if start_index != -1:
                        current_content = (
                            current_content[:start_index]
                            + replace_block
                            + current_content[start_index + len(search_block):]
                        )
                        applied_count += 1
                        logger.info(f"Applied SEARCH/REPLACE block {i+1} in file {file_path}")
                    else:
                        error_message = f"SEARCH block {i+1} not found in current content. Search block:\n---\n{search_block}\n---"
                        logger.warning(error_message)
                        errors.append(error_message)
                        # Continue with next block

                try:
                    with open(absolute_path, 'w', encoding='utf-8') as f:
                        f.write(current_content)
                    message = f"Successfully applied {applied_count}/{len(parsed_blocks)} changes to file: {file_path}."
                    if errors:
                        message += "\nWarnings:\n" + "\n".join(errors)
                    logger.info(message)
                    return ToolResult(success=True, message=message, content=current_content)
                except Exception as e:
                    logger.error(f"Error writing replaced content to file '{file_path}': {str(e)}")
                    return ToolResult(success=False, message=f"An error occurred while writing the modified file: {str(e)}")
            else:
                # No diff blocks detected, treat as full content overwrite
                with open(absolute_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                logger.info(f"Successfully wrote to file: {file_path}")
                return ToolResult(success=True, message=f"Successfully wrote to file: {file_path}", content=content)

        except Exception as e:
            logger.error(f"Error writing to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while writing to the file: {str(e)}")