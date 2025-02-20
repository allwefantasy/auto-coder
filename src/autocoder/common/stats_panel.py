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
         """生成并显示统计面板"""
         # 构建带颜色的主标题
         title = Text("代码生成统计报告", style="bold cyan")
         title.stylize("underline", 0, 6)

         # 构建各统计模块
         modules = [
             Panel(
                 Text.assemble(
                     ("🧠 模型: ", "bold"),
                     model_names + "\n",
                     ("⏱ 总耗时: ", "bold"),
                     self._format_progress_bar(int(duration), 100, f"{duration:.2f}s", "blue") + "\n",
                     ("🔢 采样数: ", "bold"),
                     self._format_progress_bar(sampling_count, 100, str(sampling_count), "cyan")
                 ),
                 title="[bold]基础信息[/]",
                 border_style="blue"
             ),
             Panel(
                 Text.assemble(
                     ("📥 输入token: ", "bold"),
                     self._format_progress_bar(input_tokens, 2000, str(input_tokens), "green") + "\n",
                     ("📤 输出token: ", "bold"),
                     self._format_progress_bar(output_tokens, 2000, str(output_tokens), "bright_green") + "\n",
                     ("🧮 总数: ", "bold"),
                     self._format_progress_bar(input_tokens + output_tokens, 4000, str(input_tokens + output_tokens), "dark_green")
                 ),
                 title="[bold]Token统计[/]",
                 border_style="green"
             ),
             Panel(
                 Text.assemble(
                     ("💵 输入成本: ", "bold"),
                     self._format_progress_bar(int(input_cost * 1000), 100, f"${input_cost:.4f}", "yellow") + "\n",
                     ("💸 输出成本: ", "bold"),
                     self._format_progress_bar(int(output_cost * 1000), 100, f"${output_cost:.4f}", "gold1") + "\n",
                     ("💰 总成本: ", "bold"),
                     self._format_progress_bar(int((input_cost + output_cost) * 1000), 200, f"${input_cost + output_cost:.4f}", "orange3")
                 ),
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
