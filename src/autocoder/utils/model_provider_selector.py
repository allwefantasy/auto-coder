from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog
from prompt_toolkit.validation import Validator, ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional, Dict, Any
from autocoder.common.printer import Printer
import re

class VolcanoEndpointValidator(Validator):
    def validate(self, document):
        text = document.text
        pattern = r'^ep-\d{14}-[a-z0-9]{5}$'
        if not re.match(pattern, text):
            raise ValidationError(
                message='Invalid endpoint format. Should be like: ep-20250204215011-vzbsg',
                cursor_position=len(text)
            )

class ModelProviderSelector:
    def __init__(self):
        self.printer = Printer()
        self.console = Console()
        
    def select_provider(self) -> Optional[Dict[str, Any]]:
        """
        Let user select a model provider and input necessary credentials.
        Returns a dictionary with provider info or None if cancelled.
        """
        result = radiolist_dialog(
            title=self.printer.get_message_from_key("model_provider_select_title"),
            text=self.printer.get_message_from_key("model_provider_select_text"),
            values=[
                ("volcano", self.printer.get_message_from_key("model_provider_volcano")),
                ("guiji", self.printer.get_message_from_key("model_provider_guiji")),
                ("deepseek", self.printer.get_message_from_key("model_provider_deepseek"))
            ]
        ).run()
        
        if result is None:
            return None
            
        provider_info = {
            "provider": result,
            "base_url": "",
            "api_key": ""
        }
        
        if result == "volcano":
            # Get Volcano endpoint
            endpoint = input_dialog(
                title=self.printer.get_message_from_key("model_provider_volcano_endpoint_title"),
                text=self.printer.get_message_from_key("model_provider_volcano_endpoint_text"),
                validator=VolcanoEndpointValidator()
            ).run()
            
            if endpoint is None:
                return None
                
            provider_info["endpoint"] = endpoint
            provider_info["base_url"] = f"https://{endpoint}.volcengineapi.com"
            
        elif result == "guiji":
            provider_info["base_url"] = "https://api.guiji.ai"
            
        elif result == "deepseek":
            provider_info["base_url"] = "https://api.deepseek.com/v1"
            
        # Get API key for all providers
        api_key = input_dialog(
            title=self.printer.get_message_from_key("model_provider_api_key_title"),
            text=self.printer.get_message_from_key(f"model_provider_{result}_api_key_text"),
            password=True
        ).run()
        
        if api_key is None:
            return None
            
        provider_info["api_key"] = api_key
        
        self.printer.print_panel(
            self.printer.get_message_from_key("model_provider_selected"),
            text_options={"justify": "left"},
            panel_options={
                "title": self.printer.get_message_from_key("model_provider_success_title"),
                "border_style": "green"
            }
        )
        
        return provider_info