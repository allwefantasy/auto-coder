import os
import json
from typing import List, Dict

MODELS_JSON = os.path.expanduser("~/.auto-coder/keys/models.json")

# Default built-in models
default_models_list = [
    {
        "name": "deepseek-reasoner",
        "description": "DeepSeek Reasoner is for design/review",
        "model_name": "deepseek-reasoner",
        "model_type": "saas/openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_path": "api.deepseek.com"
    },    
    {
        "name": "deepseek-chat",
        "description": "DeepSeek Chat is for coding",
        "model_name": "deepseek-chat",
        "model_type": "saas/openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_path": "api.deepseek.com"
    },
    {
        "name":"sonnet-3.5",
        "description": "Sonnet 3.5 is for code generation",
        "model_name": "claude-3-5-sonnet-20240620",
        "model_type": "saas/claude",
        "base_url": "",
        "api_key_path": "api.anthropic.com"
    },
    {
        "name":"o1-mini",
        "description": "o1 is for design/review",
        "model_name": "o1-2024-12-17",
        "model_type": "saas/openai",
        "base_url": "https://api.openai.com/v1",
        "api_key_path": "api.openai.com"
    }
]

def load_models() -> List[Dict]:
    """
    Load models from ~/.auto-coder/keys/models.json
    If file doesn't exist, create it with default_models_list
    """
    os.makedirs(os.path.dirname(MODELS_JSON), exist_ok=True)
    if not os.path.exists(MODELS_JSON):
        save_models(default_models_list)
        return default_models_list
    
    with open(MODELS_JSON, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # If JSON is invalid, reset to defaults
            save_models(default_models_list)
            return default_models_list

def save_models(models: List[Dict]) -> None:
    """
    Save models to ~/.auto-coder/keys/models.json
    """
    os.makedirs(os.path.dirname(MODELS_JSON), exist_ok=True)
    with open(MODELS_JSON, 'w', encoding='utf-8') as f:
        json.dump(models, f, indent=2, ensure_ascii=False)

