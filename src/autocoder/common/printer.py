from rich.console import Console
from typing import Optional
class Printer:
    def __init__(self,console:Optional[Console]=None):
        if console is None:
            self.console = Console()
        else:
            self.console = console

    def print_in_terminal(self, content: str, style: str = None):
        """Print content to terminal with optional rich styling
        
        Args:
            content: The text content to print
            style: Optional rich style string (e.g. "bold red")
        """
        if style:
            self.console.print(content, style=style)
        else:
            self.console.print(content)