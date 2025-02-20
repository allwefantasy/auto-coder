from rich.console import Console
from autocoder.common.stats_panel import StatsPanel

# 创建控制台实例
console = Console()

# 创建StatsPanel实例
stats_panel = StatsPanel(console)

# 生成并显示统计面板
stats_panel.generate(
    model_names="gpt-4-turbo",
    duration=12.34,
    sampling_count=5,
    input_tokens=1200,
    output_tokens=800,
    input_cost=0.012,
    output_cost=0.008,
    speed=45.6
)
