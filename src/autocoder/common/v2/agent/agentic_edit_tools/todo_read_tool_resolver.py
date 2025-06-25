from typing import Dict, Any, Optional, List
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import TodoReadTool, ToolResult
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs
import os
import json
from datetime import datetime

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit


class TodoReadToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: TodoReadTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: TodoReadTool = tool  # For type hinting
        
    def _get_todo_file_path(self) -> str:
        """Get the path to the todo file for this session."""
        source_dir = self.args.source_dir or "."
        todo_dir = os.path.join(source_dir, ".auto-coder", "todos")
        os.makedirs(todo_dir, exist_ok=True)
        return os.path.join(todo_dir, "current_session.json")
    
    def _load_todos(self) -> List[Dict[str, Any]]:
        """Load todos from the session file."""
        todo_file = self._get_todo_file_path()
        if not os.path.exists(todo_file):
            return []
        
        try:
            with open(todo_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('todos', [])
        except Exception as e:
            logger.warning(f"Failed to load todos: {e}")
            return []
    
    def _format_todo_display(self, todos: List[Dict[str, Any]]) -> str:
        """Format todos for display."""
        if not todos:
            return "No todos found for this session."
        
        output = []
        output.append("=== Current Session Todo List ===\n")
        
        # Group by status
        pending = [t for t in todos if t.get('status') == 'pending']
        in_progress = [t for t in todos if t.get('status') == 'in_progress']
        completed = [t for t in todos if t.get('status') == 'completed']
        
        if in_progress:
            output.append("🔄 In Progress:")
            for todo in in_progress:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(todo.get('priority', 'medium'), "⚪")
                output.append(f"  {priority_icon} [{todo['id']}] {todo['content']}")
                if todo.get('notes'):
                    output.append(f"     📝 {todo['notes']}")
            output.append("")
        
        if pending:
            output.append("⏳ Pending:")
            for todo in pending:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(todo.get('priority', 'medium'), "⚪")
                output.append(f"  {priority_icon} [{todo['id']}] {todo['content']}")
                if todo.get('notes'):
                    output.append(f"     📝 {todo['notes']}")
            output.append("")
        
        if completed:
            output.append("✅ Completed:")
            for todo in completed:
                priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(todo.get('priority', 'medium'), "⚪")
                output.append(f"  {priority_icon} [{todo['id']}] {todo['content']}")
                if todo.get('notes'):
                    output.append(f"     📝 {todo['notes']}")
            output.append("")
        
        # Add summary
        total = len(todos)
        pending_count = len(pending)
        in_progress_count = len(in_progress)
        completed_count = len(completed)
        
        output.append(f"📊 Summary: Total {total} items | Pending {pending_count} | In Progress {in_progress_count} | Completed {completed_count}")
        
        return "\n".join(output)

    def resolve(self) -> ToolResult:
        """
        Read the current todo list and return it in a formatted display.
        """
        try:
            logger.info("Reading current todo list")
            
            # Load todos from file
            todos = self._load_todos()
            
            # Format for display
            formatted_display = self._format_todo_display(todos)
            
            logger.info(f"Found {len(todos)} todos in current session")
            
            return ToolResult(
                success=True,
                message="Todo list retrieved successfully.",
                content=formatted_display
            )
            
        except Exception as e:
            logger.error(f"Error reading todo list: {e}")
            return ToolResult(
                success=False,
                message=f"Failed to read todo list: {str(e)}",
                content=None
            ) 