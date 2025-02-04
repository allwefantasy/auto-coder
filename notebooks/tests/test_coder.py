import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="", # 如何获取API Key：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
    base_url="https://qianfan.baidubce.com/v2",
)

completion = client.chat.completions.create(
    model="deepseek-r1", 
    messages=[        
        {'role': 'user', 'content': '你是谁？'}
        ]
)
print(completion.choices[0].message.content)
import time
from typing import Generator, Tuple, Dict, Any
from autocoder.utils.auto_coder_utils.chat_stream_out import multi_stream_out


def slow_stream() -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """慢速流（1秒/块）"""
    phases = [
        "🚀 正在初始化空间站连接...\n",
        "📡 接收深空传感器数据（进度 30%）...\n",
        "🧪 分析外星样本化学成分...\n",
        "⚠️ 检测到异常重力波动！\n",
        "✅ 系统就绪，可安全着陆\n"
    ]
    for idx, text in enumerate(phases):
        time.sleep(1.2)  # 较慢的间隔
        meta = {
            "progress": f"{20 * (idx + 1)}%",
            "priority": "high" if idx == 3 else "normal"
        }
        yield text, meta


def fast_stream() -> Generator[Tuple[str, Dict[str, Any]], None, None]:
    """快速流（0.3秒/块）"""
    steps = [
        "🛰️ 卫星定位校准中...\n",
        "🌍 接收地球遥测数据包（12.7MB）\n",
        "📊 生成行星表面拓扑图\n",
        "🎯 计算最优着陆坐标\n",
        "🛬 启动自动着陆程序\n"
    ]
    for step in steps:
        time.sleep(0.3)  # 更快的刷新
        meta = {"source": "nav-system", "version": "2.3.1"}
        yield step, meta


if __name__ == "__main__":
    # 同时运行两个不同速度的流
    streams = [
        slow_stream(),
        fast_stream()
    ]

    # 启动包含最终结果的平行布局输出
    print("\n=== 🪐 深空着陆系统状态监控 ===")
    results = multi_stream_out(
        stream_generators=streams,
        layout_type="vertical",  # 尝试改为 horizontal 查看横向布局
    )

    # 打印最终汇总数据
    print("\n=== 任务最终报告 ===")
    for i, (content, meta) in enumerate(results):
        print(f"🔭 流 #{i + 1} 最终输出:")
        print(f"{'-' * 40}\n{content}\n")
        print(f"元数据: {meta or '无'}\n{'-' * 40}\n")