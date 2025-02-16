import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import byzerllm
from byzerllm import ByzerLLM
from byzerllm.utils.client import code_utils

logger = logging.getLogger(__name__)

class AutoConfigRequest(BaseModel):
    query: str = Field(..., description="用户原始请求内容")
    current_conf: Dict[str, Any] = Field(..., description="当前配置项")

CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "auto_merge": {"type": "string", "enum": ["editblock", "diff", "wholefile"]},
        "chat_model": {"type": "string"},
        "code_model": {"type": "string"},
        "editblock_similarity": {"type": "number", "minimum": 0, "maximum": 1},
        "generate_times_same_model": {"type": "integer", "minimum": 1},
        "index_build_workers": {"type": "integer", "minimum": 1},
        "index_filter_workers": {"type": "integer", "minimum": 1},
    },
    "required": ["auto_merge", "chat_model"],
    "additionalProperties": True
}

class ConfigAutoTuner:
    def __init__(self, llm: ByzerLLM):
        self.llm = llm
        self.prompt_template = """
        根据用户请求和当前配置生成优化参数，严格使用以下JSON格式：
        
        ```json
        {{
            "configs": {config_schema},
            "reasoning": "配置变更原因",
            "call_configure": {{
                "location": "src/autocoder/chat_auto_coder.py",
                "method": "configure"
            }}
        }}
        ```
        
        用户请求: {query}
        当前配置: {current_conf}
        
        配置策略：
        1. 复杂逻辑用editblock，简单修改用wholefile
        2. 需要多方案时generate_times_same_model=3
        3. 涉及外部知识时启用rag_search
        """.replace("{config_schema}", json.dumps(CONFIG_SCHEMA, indent=2))

    @byzerllm.prompt()
    def _generate_config_str(self, request: AutoConfigRequest) -> str:
        return self.prompt_template.format(
            query=request.query,
            current_conf=json.dumps(request.current_conf, indent=2)
        )

    def tune(self, request: AutoConfigRequest) -> 'AutoConfigResponse':
        try:
            response_str = self._generate_config_str.with_llm(self.llm).run(request)
            return AutoConfigResponse.from_str(response_str)
        except Exception as e:
            logger.error(f"Auto config failed: {str(e)}")
            return AutoConfigResponse()

class AutoConfigResponse(BaseModel):
    configs: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = "No configuration changes"
    call_configure: Optional[Dict[str, str]] = None

    @classmethod
    def from_str(cls, response_str: str) -> 'AutoConfigResponse':
        try:
            json_str = code_utils.extract_code(response_str)[0][1]
            data = json.loads(json_str)
            return cls(**data)
        except Exception as e:
            logger.warning(f"Failed to parse response: {str(e)}")
            return cls()

    def apply(self, current_conf: Dict[str, Any]) -> Dict[str, Any]:
        # 保留用户手动设置的配置
        merged = current_conf.copy()
        merged.update(self.configs)
        return merged

    def execute_configure(self):
        if self.call_configure:
            module = __import__(self.call_configure["location"].replace(".py", "").replace("/", "."))
            func = getattr(module, self.call_configure["method"], None)
            if func:
                for k, v in self.configs.items():
                    func(f"{k}:{v}")