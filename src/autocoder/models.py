import os
import json
from typing import List, Dict
from urllib.parse import urlparse

MODELS_JSON = os.path.expanduser("~/.auto-coder/keys/models.json")

# Default built-in models
default_models_list = [
    {
        "name": "deepseek/r1",
        "description": "DeepSeek Reasoner is for design/review",
        "model_name": "deepseek-reasoner",
        "model_type": "saas/openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_path": "api.deepseek.com",
        "is_reasoning": True,
        "input_price": 0.0,  # 单位:M/百万 input tokens
        "output_price": 0.0,  # 单位:M/百万 output tokens
        "average_speed": 0.0,  # 单位:秒/请求
        "max_output_tokens": 8096
    },    
    {
        "name": "deepseek/v3",
        "description": "DeepSeek Chat is for coding",
        "model_name": "deepseek-chat",
        "model_type": "saas/openai",
        "base_url": "https://api.deepseek.com/v1",
        "api_key_path": "api.deepseek.com",
        "is_reasoning": False,
        "input_price": 0.0,
        "output_price": 0.0,
        "average_speed": 0.0,
        "max_output_tokens": 8096
    },
    {
        "name": "ark/deepseek-v3-250324",
        "description": "DeepSeek Chat is for coding",
        "model_name": "deepseek-v3-250324",
        "model_type": "saas/openai",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_path": "",
        "is_reasoning": False,
        "input_price": 2.0,
        "output_price": 8.0,
        "average_speed": 0.0,
        "max_output_tokens": 8096
    },    
    {
        "name": "ark/deepseek-r1-250120",
        "description": "DeepSeek Reasoner is for design/review",
        "model_name": "deepseek-r1-250120",
        "model_type": "saas/openai",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
        "api_key_path": "",
        "is_reasoning": True,
        "input_price": 4.0,
        "output_price": 16.0,
        "average_speed": 0.0,
        "max_output_tokens": 8096
    },    
    {
        "name": "openai/gpt-4.1-mini",
        "description": "",
        "model_name": "openai/gpt-4.1-mini",
        "model_type": "saas/openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_path": "",
        "is_reasoning": False,
        "input_price": 2.8,
        "output_price": 11.2,
        "average_speed": 0.0,
        "max_output_tokens": 8096*3
    },
    {
        "name": "openai/gpt-4.1",
        "description": "",
        "model_name": "openai/gpt-4.1",
        "model_type": "saas/openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_path": "",
        "is_reasoning": False,
        "input_price": 14.0,
        "output_price": 42.0,
        "average_speed": 0.0,
        "max_output_tokens": 8096*3
    },   
    {
        "name": "openai/gpt-4.1-nano",
        "description": "",
        "model_name": "openai/gpt-4.1-nano",
        "model_type": "saas/openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_path": "",
        "is_reasoning": False,
        "input_price": 0.0,
        "output_price": 0.0,
        "average_speed": 0.0,
        "max_output_tokens": 8096*3
    },  
    {
        "name": "openrouter/google/gemini-2.5-pro-preview-03-25",
        "description": "",
        "model_name": "google/gemini-2.5-pro-preview-03-25",
        "model_type": "saas/openai",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_path": "",
        "is_reasoning": False,
        "input_price": 0.0,
        "output_price": 0.0,
        "average_speed": 0.0,
        "max_output_tokens": 8096*2
    }
]

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
                    model["is_reasoning"] = model.get("is_reasoning", False)
                    models_dict[model["name"]] = model

        except json.JSONDecodeError:
            # If JSON is invalid, just use defaults
            print("JSON is invalid, using defaults")
            save_models(default_models_list)
    else:
        # If file doesn't exist, create it with defaults
        save_models(default_models_list)
    
    # Convert merged dictionary back to list
    target_models = list(models_dict.values())
    api_key_dir = os.path.expanduser("~/.auto-coder/keys")
    for model in target_models:    
        if model.get("api_key_path",""):           
            api_key_file = os.path.join(api_key_dir, model["api_key_path"])
            if os.path.exists(api_key_file):
                with open(api_key_file, "r", encoding="utf-8") as f:
                    model["api_key"] = f.read().strip()
    return target_models

def save_models(models: List[Dict]) -> None:
    """
    Save models to ~/.auto-coder/keys/models.json
    """
    os.makedirs(os.path.dirname(MODELS_JSON), exist_ok=True)
    with open(MODELS_JSON, 'w', encoding='utf-8') as f:
        json.dump(models, f, indent=2, ensure_ascii=False)


def add_and_activate_models(models: List[Dict]) -> None:
    """
    添加模型
    """
    exits_models = load_models()
    for model in models:        
        if model["name"] not in [m["name"] for m in exits_models]:
            exits_models.append(model)
    save_models(exits_models)

    for model in models:
        if "api_key" in model:
            update_model_with_api_key(model["name"], model["api_key"])

def get_model_by_name(name: str) -> Dict:
    """
    根据模型名称查找模型
    """
    from autocoder.common.auto_coder_lang import get_message_with_format
    models = load_models()
    v = [m for m in models if m["name"] == name.strip()]
    
    if len(v) == 0:        
        raise Exception(get_message_with_format("model_not_found", model_name=name))
    return v[0]


def update_model_input_price(name: str, price: float) -> bool:
    """更新模型输入价格
    
    Args:
        name (str): 要更新的模型名称，必须与models.json中的记录匹配
        price (float): 新的输入价格，单位：美元/百万tokens。必须大于等于0
        
    Returns:
        bool: 是否成功找到并更新了模型价格
        
    Raises:
        ValueError: 如果price为负数时抛出
        
    Example:
        >>> update_model_input_price("gpt-4", 3.0)
        True
        
    Notes:
        1. 价格设置后会立即生效并保存到models.json
        2. 实际费用计算时会按实际使用量精确到小数点后6位
        3. 设置价格为0表示该模型当前不可用
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
        
    models = load_models()
    updated = False
    for model in models:
        if model["name"] == name:
            model["input_price"] = float(price)
            updated = True
            break
    if updated:
        save_models(models)
    return updated

def update_model_output_price(name: str, price: float) -> bool:
    """更新模型输出价格
    
    Args:
        name (str): 要更新的模型名称，必须与models.json中的记录匹配
        price (float): 新的输出价格，单位：美元/百万tokens。必须大于等于0
        
    Returns:
        bool: 是否成功找到并更新了模型价格
        
    Raises:
        ValueError: 如果price为负数时抛出
        
    Example:
        >>> update_model_output_price("gpt-4", 6.0)
        True
        
    Notes:
        1. 输出价格通常比输入价格高30%-50%
        2. 对于按token计费的API，实际收费按(input_tokens * input_price + output_tokens * output_price)计算
        3. 价格变更会影响所有依赖模型计费的功能（如成本预测、用量监控等）
    """
    if price < 0:
        raise ValueError("Price cannot be negative")
        
    models = load_models()
    updated = False
    for model in models:
        if model["name"] == name:
            model["output_price"] = float(price)
            updated = True
            break
    if updated:
        save_models(models)
    return updated

def update_model_speed(name: str, speed: float) -> bool:
    """更新模型平均速度
    
    Args:
        name: 模型名称
        speed: 速度(秒/请求)
        
    Returns:
        bool: 是否更新成功
    """            
    models = load_models()
    updated = False
    for model in models:
        if model["name"] == name:
            model["average_speed"] = float(speed)
            updated = True
            break
    if updated:
        save_models(models)
    return updated

def check_model_exists(name: str) -> bool:
    """
    检查模型是否存在
    """
    models = load_models()
    return any(m["name"] == name.strip() for m in models)

def update_model_with_api_key(name: str, api_key: str) -> Dict:
    """
    根据模型名称查找并更新模型的 api_key_path。
    如果找到模型,会根据其 base_url 处理 api_key_path。
    
    Args:
        name: 模型名称
        api_key: API密钥
        
    Returns:
        Dict: 更新后的模型信息,如果未找到则返回None
    """
    models = load_models()
    
    # 在现有模型中查找
    found_model = None
    for model in models:
        if model["name"] == name.strip():
            found_model = model
            break
                    
    if not found_model:
        return None
            
    api_key_path = name.replace("/", "_")  # 替换 / 为 _，保证文件名合法
    if api_key_path:
        found_model["api_key_path"] = api_key_path
        
        # 保存 API 密钥
        api_key_dir = os.path.expanduser("~/.auto-coder/keys")
        os.makedirs(api_key_dir, exist_ok=True)
        api_key_file = os.path.join(api_key_dir, api_key_path)
        with open(api_key_file, "w",encoding="utf-8") as f:
            f.write(api_key.strip())
        
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

def update_model(name: str, model_data: Dict) -> Dict:
    """
    更新模型信息
    
    Args:
        name: 要更新的模型名称
        model_data: 包含模型新信息的字典，可以包含以下字段:
            - name: 模型名称
            - description: 模型描述
            - model_name: 模型实际名称
            - model_type: 模型类型
            - base_url: 基础URL
            - api_key: API密钥
            - is_reasoning: 是否为推理模型
            - input_price: 输入价格
            - output_price: 输出价格
            - max_output_tokens: 最大输出tokens
            - average_speed: 平均速度
            
    Returns:
        Dict: 更新后的模型信息，如果未找到则返回None
    """
    models = load_models()
    
    # 查找要更新的模型
    found = False
    for i, model in enumerate(models):
        if model["name"] == name:
            # 更新模型字段
            if "description" in model_data:
                model["description"] = model_data["description"]
            if "model_name" in model_data:
                model["model_name"] = model_data["model_name"]
            if "model_type" in model_data:
                model["model_type"] = model_data["model_type"]
            if "base_url" in model_data:
                model["base_url"] = model_data["base_url"]
            if "is_reasoning" in model_data:
                model["is_reasoning"] = model_data["is_reasoning"]
            if "input_price" in model_data:
                model["input_price"] = float(model_data["input_price"])
            if "output_price" in model_data:
                model["output_price"] = float(model_data["output_price"])
            if "max_output_tokens" in model_data:
                model["max_output_tokens"] = int(model_data["max_output_tokens"])
            if "average_speed" in model_data:
                model["average_speed"] = float(model_data["average_speed"])
            
            # 保存更新后的模型
            models[i] = model
            found = True
            
            # 如果提供了API密钥，则更新
            if "api_key" in model_data and model_data["api_key"]:
                update_model_with_api_key(name, model_data["api_key"])
            
            break
    
    if found:
        save_models(models)
        return models[i]
    
    return None

