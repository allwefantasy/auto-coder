from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.styles import Style
from rich.console import Console
from typing import Optional, Dict, Any, List
from autocoder.common.printer import Printer
import re
from pydantic import BaseModel

from autocoder.models import process_api_key_path

class ProviderInfo(BaseModel):
    name: str
    endpoint: str
    r1_model: str
    v3_model: str
    api_key: str
    r1_input_price: float
    r1_output_price: float
    v3_input_price: float
    v3_output_price: float    


PROVIDER_INFO_LIST = [
    ProviderInfo(
        name="volcano",
        endpoint="https://ark.cn-beijing.volces.com/api/v3",   
        r1_model="deepseek-r1-250120",
        v3_model="deepseek-v3-250324",
        api_key="",
        r1_input_price=2.0,
        r1_output_price=8.0,
        v3_input_price=1.0,
        v3_output_price=4.0,
    ), 
    ProviderInfo(
        name="siliconflow",
        endpoint="https://api.siliconflow.cn/v1",        
        r1_model="Pro/deepseek-ai/DeepSeek-R1",
        v3_model="Pro/deepseek-ai/DeepSeek-V3",
        api_key="",
        r1_input_price=2.0,
        r1_output_price=4.0,
        v3_input_price=4.0,
        v3_output_price=16.0,
    ),
    ProviderInfo(
        name="deepseek",
        endpoint="https://api.deepseek.com/v1",
        r1_model="deepseek-reasoner",
        v3_model="deepseek-chat",
        api_key="",
        r1_input_price=4.0,
        r1_output_price=16.0,
        v3_input_price=2.0,
        v3_output_price=8.0,
    ),
    ProviderInfo(
        name="openrouter",
        endpoint="https://openrouter.ai/api/v1",
        r1_model="deepseek/deepseek-r1",
        v3_model="deepseek/deepseek-chat-v3-0324",
        api_key="",
        r1_input_price=0.0,
        r1_output_price=0.0,
        v3_input_price=0.0,
        v3_output_price=0.0,
    )
]

dialog_style = Style.from_dict({
            'dialog':                'bg:#2b2b2b',
            'dialog frame.label':    'bg:#2b2b2b #ffffff',
            'dialog.body':          'bg:#2b2b2b #ffffff',
            'dialog shadow':        'bg:#1f1f1f',
            'button':               'bg:#2b2b2b #808080',
            'button.focused':       'bg:#1e1e1e #ffd700 bold',
            'checkbox':             '#e6e6e6',
            'checkbox-selected':    '#0078d4',
            'radio-selected':       'bg:#0078d4 #ffffff',
            'dialog frame.border':  '#0078d4',
            'radio':                'bg:#2b2b2b #808080',
            'radio.focused':        'bg:#1e1e1e #ffd700 bold'
        })

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
        Returns a list of model configurations matching the format in models.py default_models_list.
        
        Args:
            provider_info: ProviderInfo object containing provider details
            
        Returns:
            List[Dict[str, Any]]: List of model configurations
        """
        models = []
        
        # Add R1 model (for reasoning/design/review)
        if provider_info.r1_model:
            models.append({
                "name": f"r1_chat",
                "description": f"{provider_info.name} R1 is for design/review",
                "model_name": provider_info.r1_model,
                "model_type": "saas/openai",
                "base_url": provider_info.endpoint,
                "api_key": provider_info.api_key,
                "api_key_path": f"r1_chat",
                "is_reasoning": True,
                "input_price": provider_info.r1_input_price,
                "output_price": provider_info.r1_output_price,
                "average_speed": 0.0
            })
            
        # Add V3 model (for coding)
        if provider_info.v3_model:
            models.append({
                "name": f"v3_chat",
                "description": f"{provider_info.name} Chat is for coding",
                "model_name": provider_info.v3_model,
                "model_type": "saas/openai",
                "base_url": provider_info.endpoint,
                "api_key": provider_info.api_key,
                "api_key_path": f"v3_chat",
                "is_reasoning": False,
                "input_price": provider_info.v3_input_price,
                "output_price": provider_info.v3_output_price,
                "average_speed": 0.0
            })
            
        return models
        
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
                ("siliconflow", self.printer.get_message_from_key("model_provider_siliconflow")),
                ("deepseek", self.printer.get_message_from_key("model_provider_deepseek")),
                ("openrouter", self.printer.get_message_from_key("model_provider_openrouter"))
            ],
            style=dialog_style
        ).run()
        
        if result is None:
            return None

    
        provider_info = None
        for provider in PROVIDER_INFO_LIST:
            if provider.name == result:
                provider_info = provider
                break
        
        # if result == "volcano":
        #     # Get R1 endpoint
        #     r1_endpoint = input_dialog(
        #         title=self.printer.get_message_from_key("model_provider_api_key_title"),
        #         text=self.printer.get_message_from_key("model_provider_volcano_r1_text"),
        #         validator=VolcanoEndpointValidator(),
        #         style=dialog_style
        #     ).run()
            
        #     if r1_endpoint is None:
        #         return None
            
        #     provider_info.r1_model = r1_endpoint
            
        #     # Get V3 endpoint
        #     v3_endpoint = input_dialog(
        #         title=self.printer.get_message_from_key("model_provider_api_key_title"),
        #         text=self.printer.get_message_from_key("model_provider_volcano_v3_text"),
        #         validator=VolcanoEndpointValidator(),
        #         style=dialog_style
        #     ).run()
            
        #     if v3_endpoint is None:
        #         return None
                
        #     provider_info.v3_model = v3_endpoint
        
        # Get API key for all providers
        api_key = input_dialog(
            title=self.printer.get_message_from_key("model_provider_api_key_title"),
            text=self.printer.get_message_from_key(f"model_provider_{result}_api_key_text"),
            password=True,
            style=dialog_style
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