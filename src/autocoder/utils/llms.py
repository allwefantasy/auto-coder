import byzerllm
from typing import Union,Optional

def get_llm_names(llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM,str], target_model_type:Optional[str]=None) -> List[str]:
    """Get model names for a given LLM client and target model type.
    
    Args:
        llm: The LLM client instance or model name string
        target_model_type: Optional model type filter (e.g. "code_model")
    
    Returns:
        List of model names
    
    Example:
        >>> get_llm_names(llm)  # Get default model name
        ['deepseek_chat']
    """
    if isinstance(llm, str):
        return [llm]
        
    if target_model_type is None:
        return [llm.default_model_name] if llm.default_model_name else []
        
    llms = llm.get_sub_client(target_model_type)
    if llms is None:
        return [llm.default_model_name] if llm.default_model_name else []
        
    if isinstance(llms, list):
        return [llm.default_model_name for llm in llms if llm and llm.default_model_name]
    elif isinstance(llms, str):
        return llms.split(",") if llms else []
    elif isinstance(llms, (byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM)):
        return [llms.default_model_name] if llms.default_model_name else []
        
    return []

def get_single_llm(model_names: str, product_mode: str):
    from autocoder import models as models_module
    if product_mode == "pro":
        if "," in model_names:
            # Multiple code models specified
            model_names = model_names.split(",")
            for _, model_name in enumerate(model_names):
                return byzerllm.ByzerLLM.from_default_model(model_name)
        else:
            # Single code model
            return byzerllm.ByzerLLM.from_default_model(model_names)

    if product_mode == "lite":
        if "," in model_names:
            # Multiple code models specified
            model_names = model_names.split(",")            
            for _, model_name in enumerate(model_names):
                model_name = model_name.strip()
                model_info = models_module.get_model_by_name(model_name)
                target_llm = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                target_llm.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"]
                    }
                )
                return target_llm
            
        else:
            # Single code model
            model_info = models_module.get_model_by_name(model_names)
            model_name = model_names
            target_llm = byzerllm.SimpleByzerLLM(default_model_name=model_name)
            target_llm.deploy(
                model_path="",
                pretrained_model_type=model_info["model_type"],
                udf_name=model_name,
                infer_params={
                    "saas.base_url": model_info["base_url"],
                    "saas.api_key": model_info["api_key"],
                    "saas.model": model_info["model_name"],
                    "saas.is_reasoning": model_info["is_reasoning"]
                }
            )
            return target_llm