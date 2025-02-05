from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from typing import Optional,Dict,Any
from byzerllm.utils import format_str_jinja2
from autocoder.common.auto_coder_lang import get_message
from autocoder.chat_auto_coder_lang import get_message as get_chat_message

class Printer:
    def __init__(self,console:Optional[Console]=None):
        if console is None:
            self.console = Console()
        else:
            self.console = console

    def get_message_from_key(self, msg_key: str):
        try:
            return get_message(msg_key)
        except Exception as e:
            return get_chat_message(msg_key)

    def get_message_from_key_with_format(self, msg_key: str, **kwargs):
        try:
            return format_str_jinja2(self.get_message_from_key(msg_key), **kwargs)
        except Exception as e:
            return format_str_jinja2(self.get_chat_message_from_key(msg_key), **kwargs)

    def print_in_terminal(self, msg_key: str, style: str = None,**kwargs):     
        try:
            if style:
                self.console.print(format_str_jinja2(self.get_message_from_key(msg_key),**kwargs), style=style)
            else:
                self.console.print(format_str_jinja2(self.get_message_from_key(msg_key),**kwargs))
        except Exception as e:
            print(self.get_message_from_key(msg_key))

    
    def print_str_in_terminal(self, content: str, style: str = None):     
        try:
            if style:
                self.console.print(content, style=style)
            else:
                self.console.print(content)
        except Exception as e:
            print(content)   

    def print_panel(self, content: str, text_options:Dict[str,Any], panel_options:Dict[str,Any]):
        panel = Panel(Text(content, **text_options), **panel_options)
        self.console.print(panel)                  
        
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.text import Text
from typing import Dict, Any, Optional, Union
from autocoder.chat_auto_coder_lang import get_message, get_message_with_format

class Printer:
    """
    A utility class for consistent message printing using Rich library.
    Supports message localization and rich text formatting.
    """
    
    def __init__(self):
        self.console = Console()
        
    def get_message_from_key(self, key: str) -> str:
        """
        Get localized message from key.
        
        Args:
            key: Message key to look up
        
        Returns:
            str: Localized message
        """
        return get_message(key)
    
    def print_in_terminal(self, msg_key: str, style: str = "default", **kwargs):
        """
        Print a localized message with specified style.
        
        Args:
            msg_key: Message key to look up
            style: Rich style to apply (e.g. "red", "green", "yellow")
            **kwargs: Format arguments for the message
        """
        msg = get_message_with_format(msg_key, **kwargs) if kwargs else get_message(msg_key)
        if style == "default":
            self.console.print(msg)
        else:
            self.console.print(f"[{style}]{msg}[/{style}]")
            
    def print_str_in_terminal(self, msg: str, style: str = "default"):
        """
        Print a raw string message with specified style.
        
        Args:
            msg: Message to print
            style: Rich style to apply
        """
        if style == "default":
            self.console.print(msg)
        else:
            self.console.print(f"[{style}]{msg}[/{style}]")
            
    def print_panel(self, 
                    text: Union[str, Markdown, Text], 
                    text_options: Optional[Dict[str, Any]] = None,
                    panel_options: Optional[Dict[str, Any]] = None):
        """
        Print content in a styled panel.
        
        Args:
            text: Content to display (can be str, Markdown or Text)
            text_options: Options for text formatting
            panel_options: Options for panel styling
        """
        text_options = text_options or {}
        panel_options = panel_options or {}
        
        # Format text if it's a string
        if isinstance(text, str):
            text = Text(text, **text_options)
            
        # Create and print panel
        panel = Panel(text, **panel_options)
        self.console.print(panel)