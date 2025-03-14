import json
import logging
import os
import time
import traceback
import uuid
from typing import Dict, Any, Optional, Union, Callable, List
from pydantic import BaseModel, Field, SkipValidation
import byzerllm
from byzerllm import ByzerLLM
from byzerllm.utils.client import code_utils
from autocoder.common.printer import Printer
from byzerllm.utils.str2model import to_model
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.result_manager import ResultManager
from autocoder.utils import llms as llms_utils
from autocoder.common import AutoCoderArgs

logger = logging.getLogger(__name__)

class ConfigMessage(BaseModel):
    role: str
    content: str

class ExtenedConfigMessage(BaseModel):
    message: ConfigMessage
    timestamp: str

class ConfigConversation(BaseModel):
    history: Dict[str, ExtenedConfigMessage]
    current_conversation: List[ConfigMessage]

def save_to_memory_file(query: str, response: str):
    """Save conversation to memory file using ConfigConversation structure"""
    memory_dir = os.path.join(".auto-coder", "memory")
    os.makedirs(memory_dir, exist_ok=True)
    file_path = os.path.join(memory_dir, "config_chat_history.json")
    
    # Create new message objects
    user_msg = ConfigMessage(role="user", content=query)
    assistant_msg = ConfigMessage(role="assistant", content=response)
    
    extended_user_msg = ExtenedConfigMessage(
        message=user_msg,
        timestamp=str(int(time.time()))
    )
    extended_assistant_msg = ExtenedConfigMessage(
        message=assistant_msg,
        timestamp=str(int(time.time()))
    )
    
    # Load existing conversation or create new
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                existing_conv = ConfigConversation.model_validate_json(f.read())
            except Exception:
                existing_conv = ConfigConversation(
                    history={},
                    current_conversation=[]
                )
    else:
        existing_conv = ConfigConversation(
            history={},
            current_conversation=[]
        )

    existing_conv.current_conversation.append(extended_user_msg)
    existing_conv.current_conversation.append(extended_assistant_msg)        
    # Save updated conversation
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(existing_conv.model_dump_json(indent=2))

class MemoryConfig(BaseModel):
    """
    A model to encapsulate memory configuration and operations.
    """
    memory: Dict[str, Any]
    save_memory_func: SkipValidation[Callable]

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


class AutoConfigResponse(BaseModel):
    configs: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning: str = "" 


@byzerllm.prompt()
def config_readme() -> str:
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

    ## rank_times_same_model: 相同模型重排序次数
    默认值为1. 如果 generate_times_same_model 参数设置大于1，那么 coding 函数会自动对多份代码进行重排序。
    rank_times_same_model 表示重拍的次数，次数越多，选择到最好的代码的可能性越高，但是也会显著增加消耗的token和时间。
    建议保持默认，要修改也建议不要超过3。

    ## project_type: 项目类型
    项目类型通常为如下三种选择：
    1. ts
    2. py
    3. 代码文件后缀名列表（比如.java,.py,.go,.js,.ts），多个按逗号分割    

    推荐使用 3 选项，因为项目类型通常为多种后缀名混合。    

    ## conversation_prune_safe_zone_tokens: 对话剪枝安全区token数量
    在对话剪枝时，会根据对话的token数量，如果token数量超过该值，那么会剪枝掉一部分对话。

    ## enable_task_history
    该参数对 /auto 指令有效， 当你使用 /auto 指令的时候，系统会自动将近期对项目的变更(commit) 信息给到大模型，方便大模型对用户的需求有更好的理解。
    默认为 false

    ## include_project_structure
    使用 /chat , /coding 等指令时，是否将项目的目录结构也放到上下文中。
    默认为true, 如果你项目很大，请设置为 false
    """

class ConfigAutoTuner:
    def __init__(self,args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], memory_config: MemoryConfig):
        self.llm = llm
        self.memory_config = memory_config
        self.args = args
            

    def configure(self, conf: str, skip_print: bool = False) -> None:
        """
        Delegate configuration to MemoryConfig instance.
        """
        self.memory_config.configure(conf, skip_print)


    

    def command_readme(self) -> str:
        """
        # 命令说明
        ## /chat: 进入配置对话模式
        ## /coding: 进入代码生成模式
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
            "configs": [{
                "config": {
                    "auto_merge": "editblock",
                },
                "reasoning": "配置变更原因",            
                }
            ]
        }
        ```
        """
        return {
            "query": request.query,
            "current_conf": json.dumps(self.memory_config.memory["conf"], indent=2),        
            "last_execution_stat": "",
            "config_readme": config_readme.prompt()
        }

    def tune(self, request: AutoConfigRequest) -> 'AutoConfigResponse':
        result_manager = ResultManager()
        try:
            # 获取 prompt 内容
            prompt = self._generate_config_str.prompt(request)
            
            # 构造对话上下文
            conversations = [{"role": "user", "content": prompt}]

            def extract_command_response(content):
                # 提取 JSON 并转换为 AutoConfigResponse
                try:
                    response = to_model(content, AutoConfigResponse)
                    return response.reasoning
                except Exception as e:
                    return content
            
            
            # 使用 stream_out 进行输出
            model_name = ",".join(llms_utils.get_llm_names(self.llm))
            printer = Printer()
            title = printer.get_message_from_key("auto_config_analyzing")
            start_time = time.monotonic()
            result, last_meta = stream_out(
                self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
                model_name=self.llm.default_model_name,
                title=title,
                display_func=extract_command_response
            )            

            if last_meta:
                elapsed_time = time.monotonic() - start_time
                printer = Printer()
                speed = last_meta.generated_tokens_count / elapsed_time
                
                # Get model info for pricing
                from autocoder.utils import llms as llm_utils
                model_info = llm_utils.get_model_info(model_name, self.args.product_mode) or {}
                input_price = model_info.get("input_price", 0.0) if model_info else 0.0
                output_price = model_info.get("output_price", 0.0) if model_info else 0.0
                
                # Calculate costs
                input_cost = (last_meta.input_tokens_count * input_price) / 1000000  # Convert to millions
                output_cost = (last_meta.generated_tokens_count * output_price) / 1000000  # Convert to millions
                
                printer.print_in_terminal("stream_out_stats", 
                                    model_name=",".join(llms_utils.get_llm_names(self.llm)),
                                    elapsed_time=elapsed_time,
                                    first_token_time=last_meta.first_token_time,
                                    input_tokens=last_meta.input_tokens_count,
                                    output_tokens=last_meta.generated_tokens_count,
                                    input_cost=round(input_cost, 4),
                                    output_cost=round(output_cost, 4),
                                    speed=round(speed, 2))
                        
            
            # 提取 JSON 并转换为 AutoConfigResponse            
            response = to_model(result, AutoConfigResponse)
            
            # 保存对话记录
            save_to_memory_file(                
                query=request.query,
                response=response.model_dump_json(indent=2)
            )
                        
            content = response.reasoning or "success"
            for config in response.configs:
                for k, v in config["config"].items():
                    self.configure(f"{k}:{v}")
                    content += f"\nconf({k}:{v})"

            result_manager = ResultManager()
            
            result_manager.add_result(content=content, meta={
                "action": "help",
                "input": {
                    "query": request.query
                }
            })        
            return response
        except Exception as e:
            v = f"help error: {str(e)} {traceback.format_exc()}"
            logger.error(v)            
            result_manager.add_result(content=v, meta={
                "action": "help",
                "input": {
                    "query": request.query
                }
            })
            return AutoConfigResponse()
