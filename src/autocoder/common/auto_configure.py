import json
import logging
from typing import Dict, Any, Optional, Union
from pydantic import BaseModel, Field
import byzerllm
from byzerllm import ByzerLLM
from byzerllm.utils.client import code_utils
from autocoder.common.printer import Printer

logger = logging.getLogger(__name__)

class MemoryConfig(BaseModel):
    """
    A model to encapsulate memory configuration and operations.
    """
    memory: Dict[str, Any]
    save_memory_func: callable

    class Config:
        arbitrary_types_allowed = True
    
    def configure(self, conf: str, skip_print: bool = False) -> None:
        """
        Configure memory with the given key-value pair.
        """
        printer = Printer()
        parts = conf.split(None, 1)
        if len(parts) == 2 and parts[0] in ["/drop", "/unset", "/remove"]:
            key = parts[1].strip()
            if key in self.memory["conf"]:
                del self.memory["conf"][key]
                self.save_memory_func()
                printer.print_in_terminal("config_delete_success", style="green", key=key)
            else:
                printer.print_in_terminal("config_not_found", style="yellow", key=key)
        else:
            parts = conf.split(":", 1)
            if len(parts) != 2:
                printer.print_in_terminal("config_invalid_format", style="red")
                return
            key, value = parts
            key = key.strip()
            value = value.strip()
            if not value:
                printer.print_in_terminal("config_value_empty", style="red")
                return
            self.memory["conf"][key] = value
            self.save_memory_func()
            if not skip_print:
                printer.print_in_terminal("config_set_success", style="green", key=key, value=value)



class AutoConfigRequest(BaseModel):
    query: str = Field(..., description="用户原始请求内容")
    current_conf: Dict[str, Any] = Field(..., description="当前配置项")


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
            module = __import__(self.call_configure["location"].replace(
                ".py", "").replace("/", "."))
            func = getattr(module, self.call_configure["method"], None)
            if func:
                for k, v in self.configs.items():
                    func(f"{k}:{v}")



class ConfigAutoTuner:
    def __init__(self, llm: ByzerLLM, memory_config: MemoryConfig):
        self.llm = llm
        self.memory_config = memory_config
            

    def configure(self, conf: str, skip_print: bool = False) -> None:
        """
        Delegate configuration to MemoryConfig instance.
        """
        self.memory_config.configure(conf, skip_print)


    @byzerllm.prompt()
    def config_readme(self) -> str:
        """
        # 配置项说明
        ## auto_merge: 代码合并方式，可选值为editblock、diff、wholefile.
        - editblock: 生成 SEARCH/REPLACE 块，然后根据 SEARCH块到对应的源码查找，如果相似度阈值大于 editblock_similarity， 那么则将
        找到的代码块替换为 REPLACE 块。大部分情况都推荐使用 editblock。        
        - wholefile: 重新生成整个文件，然后替换原来的文件。对于重构场景，推荐使用 wholefile。
        - diff: 生成标准 git diff 格式，适用于简单的代码修改。        

        ## editblock_similarity: editblock相似度阈值
        - editblock相似度阈值，取值范围为0-1，默认值为0.9。如果设置的太低，虽然能合并进去，但是会引入错误。推荐不要修改该值。

        ## generate_times_same_model: 相同模型生成次数
        当进行生成代码时，大模型会对同一个需求生成多份代码，然后会使用 generate_rerank_model 模型对多份代码进行重排序，
        然后选择得分最高的代码。一般次数越多，最终得到正确的代码概率越高。默认值为1，推荐设置为3。但是设置值越多，可能速度就越慢，消耗的token也越多。

        ## skip_filter_index: 是否跳过索引过滤
        是否跳过根据用户的query 自动查找上下文。推荐设置为 false
        
        ## skip_build_index: 是否跳过索引构建
        是否自动构建索引。推荐设置为 false。注意，如果该值设置为 true, 那么 skip_filter_index 设置不会生效。
        """
        
    @byzerllm.prompt()
    def _generate_config_str(self, request: AutoConfigRequest) -> str:
        """
        配置项说明：
        <config_readme>
        {{ config_readme }}
        </config_readme>

        用户请求: 
        <query>
        {{ query }}
        </query>

        当前配置: 
        <current_conf>
        {{ current_conf }}
        </current_conf>
        
        上次执行情况：
        <last_execution_stat>
        {{ last_execution_stat }}
        </last_execution_stat>

        阅读配置说明，根据用户请求和当前配置以及上次执行情况，生成优化参数，严格使用以下JSON格式：

        ```json
        {
            "configs": {
                "config": {
                    "auto_merge": "editblock",
                },
                "reasoning": "配置变更原因",            
            }
        }
        ```
        """
        return {
            "query": request.query,
            "current_conf": json.dumps(request.current_conf, indent=2),        
            "last_execution_stat": "",
            "config_readme": self.config_readme.prompt()
        }

    def tune(self, request: AutoConfigRequest) -> 'AutoConfigResponse':
        try:
            response = self._generate_config_str.with_llm(
                self.llm).with_return_type(AutoConfigResponse).run(request)
            
            for k, v in response.configs.items():
                self.configure(f"{k}:{v}")
            return response
        except Exception as e:
            logger.error(f"Auto config failed: {str(e)}")
            return AutoConfigResponse()
