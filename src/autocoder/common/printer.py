from rich.console import Console
from typing import Optional
from byzerllm.utils import format_str_jinja2
from autocoder.common.auto_coder_lang import get_message
class Printer:
    def __init__(self,console:Optional[Console]=None):
        if console is None:
            self.console = Console()
        else:
            self.console = console

    def print_in_terminal(self, key: str, style: str = None,**kwargs):
        """Print content to terminal with optional rich styling
        
        Args:
            content: The text content to print
            style: Optional rich style string (e.g. "bold red")
        """
        if style:
            self.console.print(format_str_jinja2(get_message(key),**kwargs), style=style)
        else:
            self.console.print(format_str_jinja2(get_message(key),**kwargs))
