import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from autocoder.common import AutoCoderArgs
from loguru import logger


class RAGConfig(BaseModel):
    """RAG 配置项模型"""
    name: str
    server_name: str  # 实际的服务器地址，如 http://127.0.0.1:8107/v1
    api_key: Optional[str] = None
    description: Optional[str] = None


class RAGManager:
    """RAG 管理器，用于读取和管理 RAG 服务器配置"""
    
    def __init__(self, args: AutoCoderArgs):
        self.args = args
        self.configs: List[RAGConfig] = []
        self._load_configs()
    
    def _load_configs(self):
        """加载 RAG 配置，优先从项目配置，然后从全局配置"""
        # 优先读取项目级别配置
        project_config_path = os.path.join(
            self.args.source_dir, 
            ".auto-coder", 
            "auto-coder.web", 
            "rags", 
            "rags.json"
        )
        
        if os.path.exists(project_config_path):
            logger.info(f"正在加载项目级别 RAG 配置: {project_config_path}")
            self._load_project_config(project_config_path)
        else:
            logger.info("未找到项目级别 RAG 配置，尝试加载全局配置")
            # 读取全局配置
            global_config_path = os.path.expanduser("~/.auto-coder/keys/rags.json")
            if os.path.exists(global_config_path):
                logger.info(f"正在加载全局 RAG 配置: {global_config_path}")
                self._load_global_config(global_config_path)
            else:
                logger.warning("未找到任何 RAG 配置文件")
    
    def _load_project_config(self, config_path: str):
        """加载项目级别的 RAG 配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            if "data" in config_data and isinstance(config_data["data"], list):
                for item in config_data["data"]:
                    try:
                        rag_config = RAGConfig(
                            name=item.get("name", ""),
                            server_name=item.get("base_url", ""),
                            api_key=item.get("api_key"),
                            description=item.get("description")
                        )
                        self.configs.append(rag_config)
                        logger.info(f"已加载 RAG 配置: {rag_config.name} -> {rag_config.server_name}")
                    except Exception as e:
                        logger.error(f"解析项目级别 RAG 配置项时出错: {e}, 配置项: {item}")
            else:
                logger.error(f"项目级别 RAG 配置格式错误，缺少 'data' 字段或 'data' 不是列表")
                
        except json.JSONDecodeError as e:
            logger.error(f"项目级别 RAG 配置文件 JSON 格式错误: {e}")
        except Exception as e:
            logger.error(f"读取项目级别 RAG 配置文件时出错: {e}")
    
    def _load_global_config(self, config_path: str):
        """加载全局级别的 RAG 配置"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            for key, item in config_data.items():
                try:
                    # 构造 server_name: http://host:port/v1
                    host = item.get("host", "127.0.0.1")
                    port = item.get("port", 8080)
                    server_name = f"http://{host}:{port}/v1"
                    
                    rag_config = RAGConfig(
                        name=item.get("name", key),
                        server_name=server_name,
                        api_key=None,  # 全局配置中没有 api_key
                        description=item.get("description", f"{key} RAG 服务")
                    )
                    self.configs.append(rag_config)
                    logger.info(f"已加载 RAG 配置: {rag_config.name} -> {rag_config.server_name}")
                except Exception as e:
                    logger.error(f"解析全局 RAG 配置项时出错: {e}, 配置项: {item}")
                    
        except json.JSONDecodeError as e:
            logger.error(f"全局 RAG 配置文件 JSON 格式错误: {e}")
        except Exception as e:
            logger.error(f"读取全局 RAG 配置文件时出错: {e}")
    
    def get_all_configs(self) -> List[RAGConfig]:
        """获取所有 RAG 配置"""
        return self.configs
    
    def get_config_by_name(self, name: str) -> Optional[RAGConfig]:
        """根据名称获取特定的 RAG 配置"""
        for config in self.configs:
            if config.name == name:
                return config
        return None
    
    def get_server_names(self) -> List[str]:
        """获取所有服务器名称列表"""
        return [config.server_name for config in self.configs]
    
    def get_config_info(self) -> str:
        """获取格式化的配置信息，用于显示"""
        if not self.configs:
            return "未找到可用的 RAG 服务器配置"
        
        info_lines = []
        info_lines.append("可用的 RAG 服务器配置")
        
        for i, config in enumerate(self.configs, 1):
            info_lines.append(f"\n{i}. 配置名称: {config.name}")
            info_lines.append(f"   服务器地址: {config.server_name}")
            
            if config.description:
                info_lines.append(f"   描述信息: {config.description}")
            else:
                info_lines.append(f"   描述信息: 无")                           
                
            if i < len(self.configs):
                info_lines.append("-" * 30)
                
        return "\n".join(info_lines)
    
    def has_configs(self) -> bool:
        """检查是否有可用的配置"""
        return len(self.configs) > 0 