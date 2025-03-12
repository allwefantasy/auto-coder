import pkg_resources
from tokenizers import Tokenizer
from typing import Optional

class BuildinTokenizer:
    _instance: Optional['BuildinTokenizer'] = None
    _tokenizer: Optional[Tokenizer] = None

    def __new__(cls) -> 'BuildinTokenizer':
        if cls._instance is None:
            cls._instance = super(BuildinTokenizer, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        try:
            tokenizer_path = pkg_resources.resource_filename(
                "autocoder", "data/tokenizer.json"
            )
        except FileNotFoundError:
            tokenizer_path = None
            
        if tokenizer_path:
            self._tokenizer = Tokenizer.from_file(tokenizer_path)
        else:
            raise ValueError("Cannot find tokenizer.json file in package data directory")

    def count_tokens(self, text: str) -> int:
        if not self._tokenizer:
            raise ValueError("Tokenizer is not initialized")
            
        encoded = self._tokenizer.encode('{"role":"user","content":"' + text + '"}')
        return len(encoded.ids)

    @property
    def tokenizer(self) -> Optional[Tokenizer]:
        return self._tokenizer