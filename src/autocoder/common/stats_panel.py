from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
import math

class StatsPanel:
    def __init__(self, console: Console = None):
        self.console = console if console else Console()

    def _format_speed_bar(self, speed: float) -> Text:
        """生成速度可视化进度条"""
        if speed < 30:
            color = "red"
            level = "低"
        elif 30 <= speed < 60:
            color = "yellow"
            level = "中"
        else:
            color = "green"
            level = "高"

        bar_length = min(int(speed), 100)
        bar = Text("▮" * bar_length, style=color)
        bar.append(f" {speed:.1f} tokens/s ({level})", style="bold white")
        return bar

    def generate(
        self,
        model_names: str,
        duration: float,
        sampling_count: int,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        speed: float,
    ) -> None:
        """生成并显示统计面板"""
        # 构建带颜色的主标题
        title = Text("代码生成统计报告", style="bold cyan")
        title.stylize("underline", 0, 6)

        # 构建各统计模块
        modules = [
            Panel(
                Text(f"🧠 模型: {model_names}\n"
                     f"⏱ 总耗时: {duration:.2f}s\n"
                     f"🔢 采样数: {sampling_count}",
                     style="bright_cyan"),
                title="[bold]基础信息[/]",
                border_style="blue"
            ),
            Panel(
                Text(f"📥 输入token: {input_tokens}\n"
                     f"📤 输出token: {output_tokens}\n"
                     f"🧮 总数: {input_tokens + output_tokens}",
                     style="bright_green"),
                title="[bold]Token统计[/]",
                border_style="green"
            ),
            Panel(
                Text(f"💵 输入成本: ${input_cost:.4f}\n"
                     f"💸 输出成本: ${output_cost:.4f}\n"
                     f"💰 总成本: ${input_cost + output_cost:.4f}",
                     style="gold1"),
                title="[bold]成本分析[/]",
                border_style="yellow"
            )
        ]

        # 构建速度可视化面板
        speed_panel = Panel(
            Text.assemble(
                ("性能速度\n", "bold underline"),
                self._format_speed_bar(speed),
                "\n\n等级说明:\n",
                ("▮▮▮ 低 (<30)  ", "red"), 
                ("▮▮▮▮▮ 中 (30-60)  ", "yellow"), 
                ("▮▮▮▮▮▮▮ 高 (>60)", "green")
            ),
            title="[bold]速度分析[/]",
            border_style="magenta",
            padding=(1, 2)
        )

        # 组合所有内容
        grid = Columns([*modules, speed_panel], equal=True, expand=True)
        full_panel = Panel(grid, title=title, padding=(1, 3), border_style="bright_blue")

        self.console.print(full_panel)
