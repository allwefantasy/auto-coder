import os
from pydantic import BaseModel
from typing import Optional

class RagConfig(BaseModel):
    filter_config: Optional[str] = None
    answer_config: Optional[str] = None

class RagConfigManager:
    def __init__(self, path: str):
        self.config_dir = os.path.join(path, ".rag_config")

    def load_config(self) -> RagConfig:
        filter_config = self._load_file("filter_config")
        answer_config = self._load_file("answer_config")
        return RagConfig(filter_config=filter_config, answer_config=answer_config)

    def _load_file(self, filename: str) -> Optional[str]:
        file_path = os.path.join(self.config_dir, filename)
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return file.read().strip()
        return None