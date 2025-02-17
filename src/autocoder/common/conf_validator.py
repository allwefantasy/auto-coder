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
        "rank_times_same_model": {
            "type": int,
            "min": 1,
            "max": 3,
            "default": 1,
            "description": "同模型重排序次数(1-3)"
        },
        "skip_filter_index": {
            "type": bool,
            "default": False,
            "description": "是否跳过根据query自动查找上下文"
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
        "human_as_model": {
            "type": bool,
            "default": False,
            "description": "是否使用人类作为模型"
        },
        "silence": {
            "type": bool,
            "default": True,
            "description": "是否静默模式(减少输出)"
        },
        "skip_confirm": {
            "type": bool,
            "default": True,
            "description": "是否跳过确认提示"
        },
        "include_project_structure": {
            "type": bool,
            "default": True,
            "description": "是否包含项目结构信息"
        },
        "max_tokens": {
            "type": int,
            "min": 1000,
            "max": 100000,
            "default": 32000,
            "description": "最大token限制(1000-100000)"
        },
        "temperature": {
            "type": float,
            "min": 0.0,
            "max": 2.0,
            "default": 0.7,
            "description": "生成温度(0.0-2.0)"
        },
        "top_p": {
            "type": float,
            "min": 0.0,
            "max": 1.0,
            "default": 1.0,
            "description": "采样概率阈值(0.0-1.0)"
        },
        "presence_penalty": {
            "type": float,
            "min": -2.0,
            "max": 2.0,
            "default": 0.0,
            "description": "存在惩罚(-2.0-2.0)"
        },
        "frequency_penalty": {
            "type": float,
            "min": -2.0,
            "max": 2.0,
            "default": 0.0,
            "description": "频率惩罚(-2.0-2.0)"
        },
        "max_retries": {
            "type": int,
            "min": 0,
            "max": 10,
            "default": 3,
            "description": "最大重试次数(0-10)"
        },
        "timeout": {
            "type": int,
            "min": 1,
            "max": 600,
            "default": 60,
            "description": "请求超时时间(1-600秒)"
        },
        "max_workers": {
            "type": int,
            "min": 1,
            "max": 100,
            "default": 10,
            "description": "最大工作线程数(1-100)"
        },
        "log_level": {
            "type": str,
            "allowed": ["debug", "info", "warning", "error", "critical"],
            "default": "info",
            "description": "日志级别(debug/info/warning/error/critical)"
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
            "description": "默认模型"
        },
        "chat_model": {
            "type": str,
            "default": "r1_chat",
            "description": "聊天模型"
        },
        "code_model": {
            "type": str,
            "default": "v3_chat",
            "description": "代码生成模型"
        },
        "index_filter_model": {
            "type": str,
            "default": "r1_chat",
            "description": "索引过滤模型"
        },
        "generate_rerank_model": {
            "type": str,
            "default": "r1_chat",
            "description": "生成重排序模型"
        },
        "prompt_review": {
            "type": str,
            "default": "",
            "description": "代码审查提示模板"
        },
        "prompt_summary": {
            "type": str,
            "default": "",
            "description": "代码总结提示模板"
        },
        "prompt_optimize": {
            "type": str,
            "default": "",
            "description": "代码优化提示模板"
        },
        "prompt_refactor": {
            "type": str,
            "default": "",
            "description": "代码重构提示模板"
        }
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