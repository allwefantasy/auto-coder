from typing import List, Dict, Any
import json
import os
from pydantic import BaseModel

class ConversationItem(BaseModel):
    role: str
    content: str

class HistoryManager:
    def __init__(self, persist_dir: str = ".auto-coder/plugins/chat-auto-coder"):
        self.persist_dir = persist_dir
        os.makedirs(self.persist_dir, exist_ok=True)
        self.history_file = os.path.join(self.persist_dir, "conversation_history.json")

    def load_history(self) -> List[ConversationItem]:
        if os.path.exists(self.history_file):
            with open(self.history_file, "r") as f:
                try:
                    return [ConversationItem(**item) for item in json.load(f)]
                except:
                    return []
        return []

    def save_history(self, history: List[Dict[str, Any]]) -> None:
        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def get_recent_history(self, max_items: int = 5) -> List[ConversationItem]:
        history = self.load_history()
        return history[-max_items:]

    def format_history(self, max_items: int = 5) -> str:
        history = self.get_recent_history(max_items)
        formatted = []
        for item in history:
            formatted.append(f"{item.role}: {item.content}")
        return "\n".join(formatted)