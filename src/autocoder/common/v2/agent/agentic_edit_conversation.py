# src/autocoder/common/v2/agent/agentic_edit_conversation.py
import os
import json
import uuid
from typing import List, Dict, Any, Optional
from autocoder.common import AutoCoderArgs

# Define a type alias for a message dictionary
MessageType = Dict[str, Any]

class AgenticConversation:
    """
    Manages the conversation history for an agentic editing process.

    Handles adding messages (user, assistant, tool calls, tool results)
    and retrieving the history.
    """

    def __init__(self, args: AutoCoderArgs, initial_history: Optional[List[MessageType]] = None, conversation_name: Optional[str] = None):
        """
        Initializes the conversation history.

        Args:
            initial_history: An optional list of messages to start with.
            conversation_name: Optional conversation identifier. If provided, history is saved/loaded from a file named after it.
        """
        self.project_path = args.source_dir
        self._history: List[MessageType] = initial_history if initial_history is not None else []

        # Determine the memory directory
        memory_dir = os.path.join(self.project_path, ".auto-coder", "memory", "agentic_edit_memory")
        os.makedirs(memory_dir, exist_ok=True)

        # Determine conversation file path
        if conversation_name:
            filename = f"{conversation_name}.json"
        else:
            conversation_name = str(uuid.uuid4())
            filename = f"{conversation_name}.json"

        self.conversation_name = conversation_name
        self.memory_file_path = os.path.join(memory_dir, filename)

        # Load existing history if file exists
        self._load_memory()

    def add_message(self, role: str, content: Any, **kwargs):
        """
        Adds a message to the conversation history.

        Args:
            role: The role of the message sender (e.g., "user", "assistant", "tool").
            content: The content of the message. Can be None for messages like tool calls.
            **kwargs: Additional key-value pairs to include in the message dictionary (e.g., tool_calls, tool_call_id).
        """
        message: MessageType = {"role": role}
        if content is not None:
            message["content"] = content
        message.update(kwargs)
        self._history.append(message)
        self._save_memory()

    def add_user_message(self, content: str):
        """Adds a user message."""
        self.add_message(role="user", content=content)

    def add_assistant_message(self, content: str):
        """Adds an assistant message (potentially containing text response)."""
        self.add_message(role="assistant", content=content)

    def append_to_last_message(self, content: str, role: str = "assistant"):
        """Appends content to the last message."""
        if self._history:
            last_message = self._history[-1]  
            if role and last_message["role"] == role:
                last_message["content"] += content   
            elif not role:
                last_message["content"] += content

    def add_assistant_tool_call_message(self, tool_calls: List[Dict[str, Any]], content: Optional[str] = None):
         """
         Adds a message representing one or more tool calls from the assistant.
         Optionally includes assistant's textual reasoning/content alongside the calls.
         """
         self.add_message(role="assistant", content=content, tool_calls=tool_calls)


    def add_tool_result_message(self, tool_call_id: str, content: Any):
         """Adds a message representing the result of a specific tool call."""
         # The content here is typically the output/result from the tool execution.
         self.add_message(role="tool", content=content, tool_call_id=tool_call_id)


    def get_history(self) -> List[MessageType]:
        """
        Returns the latest 20 pairs of (user, assistant) conversation history.
        Merges adjacent same-role messages into one, concatenated by newline.
        Ensures that each user message is paired with the subsequent assistant response,
        skips other roles, and that the last message is always assistant (drops trailing user if unpaired).
        
        Returns:
            A list of message dictionaries, ordered chronologically.
        """
        paired_history = []
        pair_count = 0
        pending_assistant = None
        pending_user = None

        # Traverse history in reverse to collect latest pairs with merging
        for msg in reversed(self._history):
            role = msg.get("role")
            if role == "assistant":
                if pending_assistant is None:
                    pending_assistant = dict(msg)
                else:
                    # Merge with previous assistant
                    prev_content = pending_assistant.get("content", "")
                    curr_content = msg.get("content", "")
                    merged_content = (curr_content.strip() + "\n" + prev_content.strip()).strip()
                    pending_assistant["content"] = merged_content
            elif role == "user":
                if pending_user is None:
                    pending_user = dict(msg)
                else:
                    # Merge with previous user
                    prev_content = pending_user.get("content", "")
                    curr_content = msg.get("content", "")
                    merged_content = (curr_content.strip() + "\n" + prev_content.strip()).strip()
                    pending_user["content"] = merged_content

                if pending_assistant is not None:
                    # Have a full pair, insert in order
                    paired_history.insert(0, pending_user)
                    paired_history.insert(1, pending_assistant)
                    pair_count += 1
                    pending_assistant = None
                    pending_user = None
                    if pair_count >= 20:
                        break
                else:
                    # User without assistant yet, continue accumulating
                    continue
            else:
                # Ignore other roles
                continue

        # Ensure last message is assistant, drop trailing user if unpaired
        if paired_history and paired_history[-1].get("role") == "user":
            paired_history.pop()

        return paired_history

    def clear_history(self):
        """Clears the conversation history."""
        self._history = []
        self._save_memory()

    def __len__(self) -> int:
        """Returns the number of messages in the history."""
        return len(self._history)

    def __str__(self) -> str:
        """Returns a string representation of the conversation history."""
        # Consider a more readable format if needed for debugging
        return str(self._history)

    # Potential future enhancements:
    # - Method to limit history size (by tokens or message count)
    # - Method to format history specifically for different LLM APIs
    # - Serialization/deserialization methods

    def _save_memory(self):
        try:
            os.makedirs(os.path.dirname(self.memory_file_path), exist_ok=True)
            with open(self.memory_file_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # Optionally log or ignore
            pass

    def _load_memory(self):
        try:
            if os.path.exists(self.memory_file_path):
                with open(self.memory_file_path, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
        except Exception as e:
            # Ignore loading errors, start fresh
            pass
