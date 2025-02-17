from pydantic import ValidationError
from typing import Any, Dict, Optional
from autocoder.common import models
from autocoder.common.auto_coder_lang import get_message,get_message_with_format
from autocoder.common import AutoCoderArgs

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
        # 其他配置项...
    }

    @classmethod
    def validate(cls, key: str, value: Any) -> Any:
        # 获取字段元数据
        field_info = AutoCoderArgs.model_fields.get(key)
        if not field_info:
            raise ConfigValidationError(
                get_message("unknown_config_key", key=key)
            )

        # 类型转换和验证
        try:
            # 布尔类型特殊处理
            if field_info.annotation == bool:
                return cls.validate_boolean(value)
            # 其他类型转换
            converted_value = field_info.annotation(value)
        except ValueError:
            raise ConfigValidationError(
                get_message(f"invalid_{field_info.annotation.__name__.lower()}_value", value=value)
            )

        # 范围检查
        if hasattr(field_info, 'ge') and converted_value < field_info.ge:
            raise ConfigValidationError(
                get_message("value_out_of_range", 
                          value=converted_value,
                          min=field_info.ge,
                          max=field_info.le)
            )
        
        # 模型存在性检查
        if key == "model":
            if not models.check_model_exists(converted_value):
                raise ConfigValidationError(
                    get_message("model_not_found", model=converted_value)
                )

        return converted_value

    @staticmethod
    def validate_boolean(value: str) -> bool:
        if value.lower() in ("true", "1", "yes"):
            return True
        if value.lower() in ("false", "0", "no"):
            return False
        raise ConfigValidationError(
            get_message("invalid_boolean_value", value=value)
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