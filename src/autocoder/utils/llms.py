import byzerllm
from autocoder.auto_coder import models_module

def get_single_llm(model_names: str, product_mode: str):
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