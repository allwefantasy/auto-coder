




from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live

from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    DefaultValue,
    RequestOption,
)


class AutoToolAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args
        self.console = Console()

    def run(self):
        """执行 auto_tool 命令的主要逻辑"""
        from autocoder.agent.auto_tool import AutoTool

        auto_tool = AutoTool(self.args, self.llm)
        v = auto_tool.run(self.args.query)
        
        if self.args.request_id:
            request_queue.add_request(
                self.args.request_id,
                RequestValue(
                    value=DefaultValue(value=v), status=RequestOption.COMPLETED
                ),
            )
        
        markdown_content = v

        with Live(
            Panel("", title="Response", border_style="green", expand=False),
            refresh_per_second=4,
            auto_refresh=True,
            vertical_overflow="visible",
            console=Console(force_terminal=True, color_system="auto", height=None)
        ) as live:
            live.update(
                Panel(
                    Markdown(markdown_content),
                    title="Response",
                    border_style="green",
                    expand=False,
                )
            )




