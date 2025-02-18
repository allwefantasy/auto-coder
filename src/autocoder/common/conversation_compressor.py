import zlib
import json
from typing import List, Dict, Any
from pydantic import BaseModel

class CompressedConversation(BaseModel):
    compressed_data: bytes
    compression_ratio: float
    original_size: int
    compressed_size: int

class ConversationCompressor:
    def __init__(self, compression_level: int = 6):
        self.compression_level = compression_level

    def compress_conversations(self, conversations: List[Dict[str, Any]]) -> CompressedConversation:
        """压缩对话历史"""
        json_data = json.dumps(conversations, ensure_ascii=False).encode('utf-8')
        original_size = len(json_data)
        compressed_data = zlib.compress(json_data, level=self.compression_level)
        compressed_size = len(compressed_data)
        
        return CompressedConversation(
            compressed_data=compressed_data,
            compression_ratio=compressed_size / original_size,
            original_size=original_size,
            compressed_size=compressed_size
        )

    def decompress_conversations(self, compressed: CompressedConversation) -> List[Dict[str, Any]]:
        """解压缩对话历史"""
        json_data = zlib.decompress(compressed.compressed_data)
        return json.loads(json_data.decode('utf-8'))