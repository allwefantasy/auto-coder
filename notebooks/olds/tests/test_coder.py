import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="xxxx", 
    base_url="http://127.0.0.1:8102/v1",
)

completion = client.chat.completions.create(
    model="doubao_v3_chat", 
    messages=[        
        {'role': 'user', 'content': '祝海林是谁？'}
        ]
)
print(completion.choices[0].message.content)


# import time
# from typing import Generator, Tuple, Dict, Any
# from autocoder.utils.auto_coder_utils.multi_stream_out_v2 import multi_stream_out
# from byzerllm.utils.types import SingleOutputMeta


# def slow_stream() -> Generator[Tuple[str, Dict[str, Any]], None, None]:
#     """慢速流（1秒/块）"""
#     phases = [
#         ("🚀 正在初始化空间站连接...\n", SingleOutputMeta(input_tokens_count=1, generated_tokens_count=1, reasoning_content="初始化", finish_reason="")),
#         ("📡 接收深空传感器数据（进度 30%）...\n", SingleOutputMeta(input_tokens_count=2, generated_tokens_count=2, reasoning_content="接收数据", finish_reason="")),
#         ("🧪 分析外星样本化学成分...\n", SingleOutputMeta(input_tokens_count=3, generated_tokens_count=3, reasoning_content="分析成分", finish_reason="")),
#         ("⚠️ 检测到异常重力波动！\n", SingleOutputMeta(input_tokens_count=4, generated_tokens_count=4, reasoning_content="检测异常", finish_reason="")),
#         ("✅ 系统就绪，可安全着陆\n", SingleOutputMeta(input_tokens_count=5, generated_tokens_count=5, reasoning_content="准备着陆", finish_reason=""))
#     ]
#     for (text, meta) in phases:
#         time.sleep(1.2)  # 较慢的间隔        
#         yield text, meta    


# def fast_stream() -> Generator[Tuple[str, Dict[str, Any]], None, None]:
#     """快速流（0.3秒/块）"""
#     steps = [
#         ("🛰️ 卫星定位校准中...\n", SingleOutputMeta(input_tokens_count=6, generated_tokens_count=6, reasoning_content="校准定位", finish_reason="")),
#         ("🌍 接收地球遥测数据包（12.7MB）\n", SingleOutputMeta(input_tokens_count=7, generated_tokens_count=7, reasoning_content="接收遥测", finish_reason="")),
#         ("📊 生成行星表面拓扑图\n", SingleOutputMeta(input_tokens_count=8, generated_tokens_count=8, reasoning_content="生成拓扑图", finish_reason="")),
#         ("🎯 计算最优着陆坐标\n", SingleOutputMeta(input_tokens_count=9, generated_tokens_count=9, reasoning_content="计算坐标", finish_reason="")),
#         ("🛬 启动自动着陆程序\n", SingleOutputMeta(input_tokens_count=10, generated_tokens_count=10, reasoning_content="启动着陆", finish_reason=""))
#     ]
#     for (step, meta) in steps:
#         time.sleep(0.3)  # 更快的刷新        
#         yield step, meta


# if __name__ == "__main__":
#     # 同时运行两个不同速度的流
#     streams = [
#         slow_stream(),
#         fast_stream()
#     ]

#     # 启动包含最终结果的平行布局输出
#     print("\n=== 🪐 深空着陆系统状态监控 ===")
#     results = multi_stream_out(
#         stream_generators=streams,
#         titles=["慢速流监控", "快速流监控"],
#         layout="horizontal",  # 尝试改为 horizontal 查看横向布局
#     )

#     # 打印最终汇总数据
#     # print("\n=== 任务最终报告 ===")
#     # for i, (content, meta) in enumerate(results):
#     #     print(f"🔭 流 #{i + 1} 最终输出:")
#     #     print(f"{'-' * 40}\n{content}\n")
#     #     print(f"元数据: {meta or '无'}\n{'-' * 40}\n")