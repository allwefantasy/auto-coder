from typing import Dict, Any
from tokenizers import Tokenizer
from loguru import logger
from autocoder.rag.variable_holder import VariableHolder

class TokenCounterRules:
    """Rules for third-party modules to count text tokens"""
    
    @staticmethod
    def initialize(tokenizer_path: str) -> None:
        """Initialize tokenizer model"""
        try:
            VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
        except Exception as e:
            logger.error(f"Failed to initialize tokenizer: {str(e)}")
            raise

    @staticmethod
    def count_tokens(text: str) -> int:
        """Count tokens in text using the initialized tokenizer"""
        try:
            if not hasattr(VariableHolder, "TOKENIZER_MODEL"):
                raise ValueError("Tokenizer not initialized. Call initialize() first.")
                
            # Encode text with role format similar to quick_filter.py
            encoded = VariableHolder.TOKENIZER_MODEL.encode(
                '{"role":"user","content":"' + text + '"}'
            )
            return len(encoded.ids)
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            return -1

    @staticmethod
    def get_usage_rules() -> Dict[str, Any]:
        """Return usage rules documentation"""
        return {
            "description": "Token counting rules for third-party modules",
            "steps": [
                "1. Call TokenCounterRules.initialize(tokenizer_path) once at startup",
                "2. Use TokenCounterRules.count_tokens(text) to count tokens",
                "3. Handle errors (returns -1 on error)"
            ],
            "notes": [
                "Follows same token counting format as quick_filter.py",
                "Uses VariableHolder to share tokenizer instance",
                "Text is wrapped in role format for consistent counting"
            ]
        }