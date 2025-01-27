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
    Load models from ~/.auto-coder/keys/models.json and merge with default_models_list.
    Models are merged and deduplicated based on their name field.
    If file doesn't exist or is invalid, use default_models_list.
    """
    os.makedirs(os.path.dirname(MODELS_JSON), exist_ok=True)
    
    # Start with default models
    models_dict = {model["name"]: model for model in default_models_list}
    
    # If JSON file exists, read and merge with defaults
    if os.path.exists(MODELS_JSON):
        try:
            with open(MODELS_JSON, 'r', encoding='utf-8') as f:
                custom_models = json.load(f)
                # Custom models will override defaults with same name
                for model in custom_models:
                    models_dict[model["name"]] = model
        except json.JSONDecodeError:
            # If JSON is invalid, just use defaults
            save_models(default_models_list)
    else:
        # If file doesn't exist, create it with defaults
        save_models(default_models_list)
    
    # Convert merged dictionary back to list
    return list(models_dict.values())

def save_models(models: List[Dict]) -> None:
    """
    Save models to ~/.auto-coder/keys/models.json
    """
    os.makedirs(os.path.dirname(MODELS_JSON), exist_ok=True)
    with open(MODELS_JSON, 'w', encoding='utf-8') as f:
        json.dump(models, f, indent=2, ensure_ascii=False)


def process_api_key_path(base_url: str) -> str:
    """
    从 base_url 中提取 host 部分并处理特殊字符
    例如: https://api.example.com:8080/v1 -> api.example.com_8080
    """
    if not base_url:
        return ""
    
    parsed = urlparse(base_url)
    host = parsed.netloc
    
    # 将冒号替换为下划线
    host = host.replace(":", "_")
    
    return host

def update_model_with_api_key(name: str, api_key: str) -> Dict:
    """
    根据模型名称查找并更新模型的 api_key_path。
    如果找到模型，会根据其 base_url 处理 api_key_path。
    
    Args:
        name: 模型名称
        api_key: API密钥
        
    Returns:
        Dict: 更新后的模型信息，如果未找到则返回None
    """
    models = load_models()
    
    # 在现有模型中查找
    found_model = None
    for model in models:
        if model["name"] == name:
            found_model = model
            break
                    
    if not found_model:
        return None
        
    # 从 base_url 中提取并处理 host
    api_key_path = process_api_key_path(found_model["base_url"])
    if api_key_path:
        found_model["api_key_path"] = api_key_path
        
        # 保存 API 密钥
        api_key_dir = os.path.expanduser("~/.auto-coder/keys")
        os.makedirs(api_key_dir, exist_ok=True)
        api_key_file = os.path.join(api_key_dir, api_key_path)
        with open(api_key_file, "w") as f:
            f.write(api_key)
        
        # 如果是新模型，添加到模型列表中
        if all(model["name"] != name for model in models):
            models.append(found_model)
        else:
            # 更新现有模型
            for i, model in enumerate(models):
                if model["name"] == name:
                    models[i] = found_model
                    break
        
        save_models(models)
    
    return found_model

