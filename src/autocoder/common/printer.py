from rich.console import Console

class Printer:
    def __init__(self):
        self.console = Console()

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