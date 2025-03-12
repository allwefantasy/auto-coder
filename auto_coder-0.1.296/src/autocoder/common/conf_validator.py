from typing import Any
from autocoder.utils import llms as llms_utils
from autocoder.common.auto_coder_lang import get_message_with_format

class ConfigValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)

class ConfigValidator:
    CONFIG_SPEC = {
        # 核心配置项
        "auto_merge": {
            "type": str,
            "allowed": ["editblock", "diff", "wholefile"],
            "default": "editblock",
            "description": "代码合并方式(editblock/diff/wholefile)"
        },
        "editblock_similarity": {
            "type": float,
            "min": 0.0,
            "max": 1.0,
            "default": 0.9,
            "description": "代码块相似度阈值(0-1)"
        },
        "generate_times_same_model": {
            "type": int,
            "min": 1,
            "max": 5,
            "default": 1,
            "description": "同模型生成次数(1-5)"
        },
        "skip_filter_index": {
            "type": bool,
            "default": False,
            "description": "是否跳过根据用户的query自动查找上下文"
        },
        "skip_build_index": {
            "type": bool,
            "default": True,
            "description": "是否自动构建索引"
        },
        "enable_global_memory": {
            "type": bool,
            "default": True,
            "description": "是否开启全局记忆"
        },
        "rank_times_same_model": {
            "type": int,
            "min": 1,
            "max": 3,
            "default": 1,
            "description": "相同模型重排序次数"
        },
        "human_as_model": {
            "type": bool,
            "default": False,
            "description": "是否以人类作为模型"
        },
        "skip_confirm": {
            "type": bool,
            "default": True,
            "description": "是否跳过确认步骤"
        },
        "silence": {
            "type": bool,
            "default": True,
            "description": "是否静默模式"
        },
        "include_project_structure": {
            "type": bool,
            "default": True,
            "description": "是否包含项目结构"
        },
        "product_mode": {
            "type": str,
            "allowed": ["lite", "pro"],
            "default": "lite",
            "description": "产品模式(lite/pro)"
        },
        "model": {
            "type": str,
            "default": "v3_chat",
            "description": "默认模型名称"
        },
        "chat_model": {
            "type": str,
            "default": "r1_chat",
            "description": "聊天模型名称"
        },
        "code_model": {
            "type": str,
            "default": "v3_chat",
            "description": "代码生成模型名称"
        },
        "index_filter_model": {
            "type": str,
            "default": "r1_chat",
            "description": "索引过滤模型名称"
        },
        "generate_rerank_model": {
            "type": str,
            "default": "r1_chat",
            "description": "生成重排序模型名称"
        },
        "emb_model": {
            "type": str,
            "default": "v3_chat",
            "description": "嵌入模型名称"
        },
        "vl_model": {
            "type": str,
            "default": "v3_chat",
            "description": "视觉语言模型名称"
        },
        "designer_model": {
            "type": str,
            "default": "v3_chat",
            "description": "设计模型名称"
        },
        "sd_model": {
            "type": str,
            "default": "v3_chat",
            "description": "稳定扩散模型名称"
        },
        "voice2text_model": {
            "type": str,
            "default": "v3_chat",
            "description": "语音转文本模型名称"
        },
        "commit_model": {
            "type": str,
            "default": "v3_chat",
            "description": "提交信息生成模型名称"
        },
        "rank_strategy": {
            "type": str,
            "allowed": ["block", "file"],
            "default": "block",
            "description": "排序策略(block/file)"
        }
    }

    @classmethod
    def validate(cls, key: str, value: Any, product_mode: str) -> Any:        
        # 获取配置规范
        spec = cls.CONFIG_SPEC.get(key)
        if not spec:
            # raise ConfigValidationError(
            #     get_message_with_format("unknown_config_key", key=key)
            # )
            return

        # 类型转换和验证
        try:
            # 布尔类型特殊处理
            if isinstance(spec['type'], (list, tuple)):
                # 多个类型支持
                for type_ in spec['type']:
                    try:
                        if type_ == bool:
                            return cls.validate_boolean(value)
                        converted_value = type_(value)
                        break
                    except ValueError:
                        continue
                else:
                    types_str = ', '.join([t.__name__ for t in spec['type']])
                    raise ConfigValidationError(
                        get_message_with_format(f"invalid_type_value", 
                                  value=value,
                                  types=types_str)
                    )
            else:
                # 单个类型处理
                if spec['type'] == bool:
                    return cls.validate_boolean(value)
                converted_value = spec['type'](value)
        except ValueError:
            type_name = spec['type'].__name__ if not isinstance(spec['type'], (list, tuple)) else ', '.join([t.__name__ for t in spec['type']])
            raise ConfigValidationError(
                get_message_with_format(f"invalid_type_value", 
                          value=value,
                          types=type_name)
            )

        # 范围检查
        if 'min' in spec and converted_value < spec['min']:
            raise ConfigValidationError(
                get_message_with_format("value_out_of_range", 
                          value=converted_value,
                          min=spec['min'],
                          max=spec['max'])
            )
        
        if 'max' in spec and converted_value > spec['max']:
            raise ConfigValidationError(
                get_message_with_format("value_out_of_range", 
                          value=converted_value,
                          min=spec['min'],
                          max=spec['max'])
            )

        # 枚举值检查
        if 'allowed' in spec and converted_value not in spec['allowed']:
            raise ConfigValidationError(
                get_message_with_format("invalid_enum_value", 
                          value=converted_value,
                          allowed=', '.join(map(str, spec['allowed'])))
            )
        
        # 模型存在性检查        
        if product_mode == "lite" and key in ["chat_model","code_model", 
                                     "index_filter_model", "generate_rerank_model", 
                                     "rank_times_same_model", 
                                     "emb_model", "vl_model", "designer_model", "sd_model", 
                                     "voice2text_model", 
                                     "commit_model","model"]:
            if not llms_utils.get_model_info(converted_value,product_mode):
                raise ConfigValidationError(
                    get_message_with_format("model_not_found", model=converted_value)
                )

        return converted_value

    @staticmethod
    def validate_boolean(value: str) -> bool:
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        raise ConfigValidationError(
            get_message_with_format("invalid_boolean_value", value=value)
        )

    @classmethod
    def get_config_docs(cls) -> str:
        """生成配置项文档"""
        docs = ["可用配置项："]
        for key, spec in cls.CONFIG_SPEC.items():
            desc = [
                f"- {key}: {spec['description']}",
                f"  类型: {spec['type'].__name__}",
                f"  默认值: {spec['default']}"
            ]
            if "allowed" in spec:
                desc.append(f"  允许值: {', '.join(spec['allowed'])}")
            if "min" in spec and "max" in spec:
                desc.append(f"  取值范围: {spec['min']}~{spec['max']}")
            docs.append("\n".join(desc))
        return "\n\n".join(docs)