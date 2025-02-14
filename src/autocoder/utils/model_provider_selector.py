from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog
from prompt_toolkit.validation import Validator, ValidationError
from rich.console import Console
from typing import Optional, Dict, Any, List
from autocoder.common.printer import Printer
import re
from pydantic import BaseModel

class ProviderInfo(BaseModel):
    name: str
    endpoint: str
    r1_model: str
    v3_model: str
    api_key: str


PROVIDER_INFO_LIST = [
    ProviderInfo(
        name="Volcano",
        endpoint="https://ark.cn-beijing.volces.com/api/v3",   
        r1_model="",
        v3_model="",
        api_key="",
    ), 
    ProviderInfo(
        name="SiliconFlow",
        endpoint="https://api.siliconflow.cn/v1",        
        r1_model="Pro/deepseek-ai/DeepSeek-R1",
        v3_model="Pro/deepseek-ai/DeepSeek-V3",
        api_key="",
    ),
    ProviderInfo(
        name="DeepSeek",
        endpoint="https://api.deepseek.com/v1",
        r1_model="deepseek-reasoner",
        v3_model="deepseek-chat",
        api_key="",
    ),
]

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

    def to_models_json(self, provider_info: ProviderInfo) -> List[Dict[str, Any]]:
        """
        Convert provider info to models.json format.
        """
        return {
            
        }
        
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
                ("siliconflow", self.printer.get_message_from_key("model_provider_guiji")),
                ("deepseek", self.printer.get_message_from_key("model_provider_deepseek"))
            ]
        ).run()
        
        if result is None:
            return None
        
        provider_info = PROVIDER_INFO_LIST[result]        
        
        if result == "volcano":
            # Get R1 endpoint
            r1_endpoint = input_dialog(
                title=self.printer.get_message_from_key("model_provider_api_key_title"),
                text=self.printer.get_message_from_key("model_provider_volcano_r1_text"),
                validator=VolcanoEndpointValidator()
            ).run()
            
            if r1_endpoint is None:
                return None
            
            provider_info.r1_model = r1_endpoint
            
            # Get V3 endpoint
            v3_endpoint = input_dialog(
                title=self.printer.get_message_from_key("model_provider_api_key_title"),
                text=self.printer.get_message_from_key("model_provider_volcano_v3_text"),
                validator=VolcanoEndpointValidator()
            ).run()
            
            if v3_endpoint is None:
                return None
                
            provider_info.v3_model = v3_endpoint
        
        # Get API key for all providers
        api_key = input_dialog(
            title=self.printer.get_message_from_key("model_provider_api_key_title"),
            text=self.printer.get_message_from_key(f"model_provider_{result}_api_key_text"),
            password=True
        ).run()
        
        if api_key is None:
            return None
            
        provider_info.api_key = api_key
        
        self.printer.print_panel(
            self.printer.get_message_from_key("model_provider_selected"),
            text_options={"justify": "left"},
            panel_options={
                "title": self.printer.get_message_from_key("model_provider_success_title"),
                "border_style": "green"
            }
        )
        
        return provider_info