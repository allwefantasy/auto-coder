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

    def _format_progress_bar(self, value: int, max_value: int, label: str, color: str) -> Text:
        """生成通用进度条"""
        progress = min(value / max_value, 1.0)
        bar_length = int(progress * 20)
        bar = Text("▮" * bar_length, style=color)
        bar.append(f" {value} ({label})", style="bold white")
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
         """新版紧凑布局"""
         # 复合标题（带图标和关键数据）
         title = Text.assemble(
             "📊 ", ("代码生成统计", "bold cyan underline"),
             " │ ⚡", (f"{speed:.1f}t/s ", "bold green"),
             "│ 💰", (f"${input_cost + output_cost:.4f}", "bold yellow")
         )

         # 紧凑网格布局
         grid = [
             Panel(
                 Text.assemble(
                     ("🤖 模型: ", "bold"), model_names + "\n",
                     self._format_mini_progress(int(duration), 100, "cyan"),
                     (" ⏱", "cyan"), f" {duration:.1f}s │ ",
                     self._format_mini_progress(sampling_count, 100, "blue"),
                     (" 🔢", "blue"), f" {sampling_count}\n",
                     ("📥", "green"), " ", self._format_mini_progress(input_tokens, 2000, "green"),
                     f" {input_tokens} │ ",
                     ("📤", "bright_green"), " ", self._format_mini_progress(output_tokens, 2000, "bright_green"),
                     f" {output_tokens}"
                 ),
                 border_style="cyan",
                 padding=(0, 2)
             ),
             Panel(
                 Text.assemble(
                     ("💵 成本: ", "bold"), 
                     self._format_mini_progress(int(input_cost*1000), 100, "yellow"),
                     (" IN", "yellow"), f" ${input_cost:.3f}\n",
                     ("💸 ", "bold"), 
                     self._format_mini_progress(int(output_cost*1000), 100, "gold1"),
                     (" OUT", "gold1"), f" ${output_cost:.3f}\n",
                     self._format_speed_bar(speed)  # 复用原速度条
                 ),
                 border_style="yellow",
                 padding=(0, 1)
             )
         ]

         # 组合布局
         main_panel = Panel(
             Columns(grid, equal=True, expand=True),
             title=title,
             border_style="bright_blue",
             padding=(1, 2)
         )

         self.console.print(main_panel)
    def _format_mini_progress(self, value: int, max_value: int, color: str) -> Text:
        """紧凑型进度条"""
        progress = min(value / max_value, 1.0)
        filled = "▮" * int(progress * 10)  # 缩短进度条长度
        empty = "▯" * (10 - len(filled))
        return Text(filled + empty, style=color)
