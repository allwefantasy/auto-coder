



import os
from rich.console import Console
from rich.panel import Panel

from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    DefaultValue,
    RequestOption,
)


class GenerateCommandAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args
        self.console = Console()

    def run(self):
        """执行 generate_command 命令的主要逻辑"""
        from autocoder.common.command_generator import generate_shell_script

        shell_script = generate_shell_script(self.args, self.llm)

        self.console.print(
            Panel(
                shell_script,
                title="Shell Script",
                border_style="magenta",
            )
        )

        with open(os.path.join(".auto-coder", "exchange.txt"), "w", encoding="utf-8") as f:
            f.write(shell_script)

        request_queue.add_request(
            self.args.request_id,
            RequestValue(
                value=DefaultValue(value=shell_script),
                status=RequestOption.COMPLETED,
            ),
        )



