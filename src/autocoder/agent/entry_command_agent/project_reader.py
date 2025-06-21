

import os
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live

from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.common.printer import Printer
from autocoder.utils.llms import get_llm_names


class ProjectReaderAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args
        self.console = Console()

    def run(self):
        """执行 project_reader 命令的主要逻辑"""
        target_llm = self.llm.get_sub_client("planner_model")
        if not target_llm:
            target_llm = self.llm
        
        model_filter = ModelPathFilter.from_model_object(target_llm, self.args)
        if model_filter.has_rules():
            printer = Printer()
            msg = printer.get_message_from_key_with_format(
                "model_has_access_restrictions",                                            
                model_name=",".join(get_llm_names(target_llm))
            )
            raise ValueError(msg)

        from autocoder.agent.project_reader import ProjectReader

        project_reader = ProjectReader(self.args, self.llm)
        v = project_reader.run(self.args.query)            
        
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

