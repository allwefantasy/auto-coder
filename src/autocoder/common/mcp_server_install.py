import json
import sys
import os
import time
from typing import Dict, Any, Tuple, List
from loguru import logger
import asyncio

from autocoder.common.mcp_hub import McpHub, MCP_BUILD_IN_SERVERS
from autocoder.common.mcp_server_types import McpResponse, McpInstallRequest, InstallResult, ServerConfig, McpExternalServer
from autocoder.chat_auto_coder_lang import get_message_with_format


class McpServerInstaller:
    """Class responsible for installing and configuring MCP servers"""
    
    def __init__(self):
        pass
    
    def install_python_package(self, package_name: str) -> None:
        """Install a Python package using pip"""
        try:
            import importlib
            importlib.import_module(package_name.replace("-", "_"))
        except ImportError:
            import subprocess
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True)
            except subprocess.CalledProcessError:
                print(f"\n\033[93mFailed to automatically install {package_name}. Please manually install it using:\n")
                print(f"    pip install {package_name}\n")
                print(f"We have already updated the server configuration in ~/.autocoder/mcp/settings.json.\n")
                print(f"After installation, you can restart the auto-coder.chat using the server.\033[0m\n")

    def install_node_package(self, package_name: str) -> None:
        """Install a Node.js package using npm"""
        import subprocess
        try:
            subprocess.run(["npx", package_name, "--version"], check=True)
        except:
            try:
                subprocess.run(["npm", "install", "-y", "-g", package_name], check=True)
            except subprocess.CalledProcessError:
                print(f"\n\033[93mFailed to automatically install {package_name}. Please manually install it using:\n")
                print(f"    npm install -g {package_name}\n")
                print(f"We have already updated the server configuration in ~/.autocoder/mcp/settings.json.\n")
                print(f"After installation, you can restart the auto-coder.chat using the server.\033[0m\n")

    def deep_merge_dicts(self, dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
        """
        深度合并两个字典，包括嵌套的字典
        dict1是基础字典，dict2是优先字典（当有冲突时保留dict2的值）
        """
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 如果两个字典都包含相同的键，并且两个值都是字典，则递归合并
                result[key] = self.deep_merge_dicts(result[key], value)
            else:
                # 否则，使用dict2的值覆盖或添加到结果
                result[key] = value
        return result

    def get_mcp_external_servers(self) -> List[McpExternalServer]:
        """Get external MCP servers list from GitHub"""
        cache_dir = os.path.join(".auto-coder", "tmp")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "mcp_external_servers.json")

        # Check cache first
        if os.path.exists(cache_file):
            cache_time = os.path.getmtime(cache_file)
            if time.time() - cache_time < 3600:  # 1 hour cache
                with open(cache_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                    return [McpExternalServer(**item) for item in raw_data]

        # Fetch from GitHub
        url = "https://raw.githubusercontent.com/michaellatman/mcp-get/refs/heads/main/packages/package-list.json"
        try:
            import requests
            response = requests.get(url)
            if response.status_code == 200:
                raw_data = response.json()
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(raw_data, f)
                return [McpExternalServer(**item) for item in raw_data]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch external MCP servers: {e}")
            return []

    def parse_command_line_args(self, server_name_or_config: str) -> Tuple[str, Dict[str, Any]]:
        """Parse command-line style arguments into name and config"""
        name = ""
        config = {}
        args = server_name_or_config.strip().split()
        i = 0
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            elif args[i] == "--command" and i + 1 < len(args):
                config["command"] = args[i + 1]
                i += 2
            elif args[i] == "--args":
                config["args"] = []
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    config["args"].append(args[i])
                    i += 1
            elif args[i] == "--env":
                config["env"] = {}
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    if "=" in args[i]:
                        key, value = args[i].split("=", 1)
                        config["env"][key] = value
                    i += 1
            else:
                i += 1

        template_config = {}

        if name in MCP_BUILD_IN_SERVERS:
            template_config = MCP_BUILD_IN_SERVERS[name]
        else:
            # 查找外部server
            external_servers = self.get_mcp_external_servers()
            for s in external_servers:
                if s.name == name:
                    if s.runtime == "python":
                        # self.install_python_package(name)
                        template_config = {
                            "command": "python",
                            "args": [
                                "-m", name.replace("-", "_")
                            ],
                        }
                    elif s.runtime == "node":
                        # self.install_node_package(name)
                        template_config = {
                            "command": "npx",
                            "args": [
                                "-y",
                                "-g",
                                name
                            ]
                        }
                    break

        # 深度合并两个配置，以用户配置为主
        config = self.deep_merge_dicts(template_config, config)

        if not config.get("args") and (name.startswith("@") or config.get("command") in ["npx", "npm"]):
            config["args"] = ["-y", "-g", name]

        ## 如果有模板，则无需再次安装，处理模板的时候会自动安装
        # if not template_config:
        #     # Install package if needed
        #     if name.startswith("@") or config.get("command") in ["npx", "npm"]:
        #         self.install_node_package(name)
        #     else:
        #         self.install_python_package(name)

        return name, config

    def parse_json_config(self, server_name_or_config: str) -> Tuple[str, Dict[str, Any]]:
        """Parse JSON configuration into name and config"""
        raw_config = json.loads(server_name_or_config)
        # 用户给了一个完整的配置
        if "mcpServers" in raw_config:
            raw_config = raw_config["mcpServers"]

        # 取第一个server 配置
        config = list(raw_config.values())[0]
        name = list(raw_config.keys())[0]
        # if name.startswith("@") or config["command"] in ["npx", "npm"]:
        #     for item in config["args"]:
        #         if name in item:
        #             self.install_node_package(item)
        # else:
        #     self.install_python_package(name)

        return name, config
    
    def process_market_install_item(self, market_item) -> Tuple[str, Dict[str, Any]]:
        """Process a MarketplaceMCPServerItem into name and config"""
        name = market_item.name
        config = {
            "command": market_item.command,
            "args": market_item.args,
            "env": market_item.env
        }
        
        # Install package if needed
        # if name.startswith("@") or market_item.command in ["npx", "npm"]:
        #     for item in market_item.args:
        #         if name in item:
        #             self.install_node_package(item)
        # elif market_item.command not in ["python", "node"]:
        #     self.install_python_package(name)
            
        return name, config

    async def install_server(self, request: McpInstallRequest, hub: McpHub) -> McpResponse:
        """Install an MCP server with module dependency check"""
        name = ""
        config = {}
        try:
            # Check if market_install_item is provided
            logger.info(f"Installing MCP server: {request.market_install_item}")
            if request.market_install_item:
                name, config = self.process_market_install_item(request.market_install_item)
                display_result = request.market_install_item.name
            else:
                server_name_or_config = request.server_name_or_config
                display_result = server_name_or_config

                # Try different parsing methods
                if server_name_or_config.strip().startswith("--"):
                    # Command-line style arguments
                    name, config = self.parse_command_line_args(server_name_or_config)
                else:
                    try:
                        # Try parsing as JSON
                        name, config = self.parse_json_config(server_name_or_config)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON config: {server_name_or_config}")
                        pass

            if not name:
                raise ValueError(
                    "MCP server name is not available in MCP_BUILD_IN_SERVERS or external servers")

            logger.info(f"Installing MCP server: {name} with config: {config}")
            if not config:
                raise ValueError(f"MCP server {name} config is not available")

            is_success = await hub.add_server_config(name, config)
            if is_success:
                return McpResponse(
                    result=get_message_with_format("mcp_install_success", result=display_result),
                    raw_result=InstallResult(
                        success=True,
                        server_name=name,
                        config=ServerConfig(**config)
                    )
                )
            else:
                return McpResponse(
                    result="", 
                    error=get_message_with_format("mcp_install_error", error="Failed to establish connection"),
                    raw_result=InstallResult(
                        success=False,
                        server_name=name,
                        config=ServerConfig(**config),
                        error="Failed to establish connection"
                    )
                )
        except Exception as e:
            return McpResponse(
                result="", 
                error=get_message_with_format("mcp_install_error", error=str(e)),
                raw_result=InstallResult(
                    success=False,
                    error=str(e)
                )
            ) 