







from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
import math

class StatsPanel:
    def __init__(self, console: Console = None):
        self.console = console if console else Console()

    def _format_speed_bar(self, speed: float) -> Text:
        """生成速度可视化进度条（保持原30-60区间）"""
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

         # 处理耗时颜色逻辑（新增15-30-60区间）
         duration_color = "green"
         if 15 <= duration < 30:
             duration_color = "yellow"
         elif duration >= 30:
             duration_color = "red"

         # 处理成本颜色逻辑（新增0.5-1区间）
         def get_cost_color(cost: float) -> str:
             if cost < 0.5: return "green"
             elif 0.5 <= cost < 1: return "yellow"
             else: return "red"

         # 紧凑网格布局
         grid = [
             Panel(
                 Text.assemble(
                     ("🤖 模型: ", "bold"), model_names + "\n",
                     self._format_mini_progress(duration, 60.0, duration_color),  # 耗时max=60
                     (" ⏱", duration_color), f" {duration:.1f}s │ ",
                     self._format_mini_progress(sampling_count, 100, "blue"),
                     (" 🔢", "blue"), f" {sampling_count}\n",
                     ("📥", "green"), " ", 
                     self._format_mini_progress(input_tokens, 65536.0, "green"),  # token分母改为65536
                     f" {input_tokens} ({input_tokens/65536*100:.2f}%) │ ",  # 新增百分比显示
                     ("📤", "bright_green"), " ", 
                     self._format_mini_progress(output_tokens, 65536.0, "bright_green"),
                     f" {output_tokens} ({output_tokens/65536*100:.2f}%)"  # 新增百分比显示
                 ),
                 border_style="cyan",
                 padding=(0, 2)
             ),
             Panel(
                 Text.assemble(
                     ("💵 成本: ", "bold"), 
                     self._format_mini_progress(input_cost, 1.0, get_cost_color(input_cost)),  # 成本max=1
                     (" IN", get_cost_color(input_cost)), f" {input_cost:.3f}\n",
                     ("💸 ", "bold"), 
                     self._format_mini_progress(output_cost, 1.0, get_cost_color(output_cost)),
                     (" OUT", get_cost_color(output_cost)), f" {output_cost:.3f}\n",
                     self._format_speed_bar(speed)
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
    

    def _format_mini_progress(self, value: float, max_value: float, color: str) -> Text:
        """紧凑型进度条（支持浮点数）"""
        progress = min(value / max_value, 1.0)
        filled = "▮" * int(progress * 10)
        empty = "▯" * (10 - len(filled))
        return Text(filled + empty, style=color)
