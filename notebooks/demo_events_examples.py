"""
Examples showing how to use the events module.

这个脚本演示了如何使用事件系统进行系统间通信，特别是演示了ASK_USER事件如何实现阻塞等待用户输入。

新增功能：
- 回调机制：当收到用户响应时，可以触发自定义回调函数，用于执行额外的逻辑
- 在ask_user方法中通过callback参数传入回调函数

使用方法:
    python demo_events_examples.py [demo_type]

    demo_type 可以是:
    - basic: 基本演示
    - stream: 流数据演示
    - pydantic: Pydantic模型演示
"""

import os
import time
import threading
from typing import Dict, Any, List, Optional

from autocoder.events.event_manager import EventManager
from autocoder.events.event_types import Event, EventType
from autocoder.events.event_content import (
    StreamContent, ResultContent, AskUserContent, UserResponseContent,
    ContentType, StreamState, CodeContent, MarkdownContent,
    create_stream_thinking, create_stream_content, create_result,
    create_ask_user, create_user_response
)




def pydantic_models_demo(manager) -> None:
    """
    Demo showing how to use the predefined Pydantic models for event content.
    
    Args:
        event_file: Path to the event file
    """
    
    # 写入结果数据 - 使用ResultContent模型
    result_content = create_result(
        content="Starting Pydantic models demo",
        metadata={"demo_type": "pydantic", "version": "1.0"}
    )
    manager.write_result(result_content.to_dict())
    
    print("Demo 1: Stream with thinking and content states")
    # 思考过程 - 使用StreamContent模型
    for i in range(3):
        thinking = create_stream_thinking(
            content=f"思考中...分析步骤 {i}",
            sequence=i
        )
        manager.write_stream(thinking.to_dict())
        time.sleep(0.3)
    
    # 正式内容 - 使用StreamContent模型
    for i in range(2):
        content = create_stream_content(
            content=f"这是正式内容 {i+1}",
            sequence=i+3  # 延续序列号
        )
        manager.write_stream(content.to_dict())
        time.sleep(0.3)
    
    print("Demo 2: Code content")
    # 代码内容 - 使用CodeContent模型
    code = CodeContent(
        state=StreamState.CONTENT,
        content="def hello():\n    print('Hello, world!')",
        language="python",
        sequence=5
    )
    manager.write_stream(code.to_dict())
    time.sleep(0.5)
    
    print("Demo 3: Markdown content")
    # Markdown内容 - 使用MarkdownContent模型
    markdown = MarkdownContent(
        state=StreamState.CONTENT,
        content="# 标题\n这是一段**Markdown**内容\n\n- 列表项1\n- 列表项2",
        sequence=6
    )
    manager.write_stream(markdown.to_dict())
    time.sleep(0.5)
    
    print("Demo 4: Ask user with options")
    # 询问用户 - 使用AskUserContent模型
    # 使用真实的ask_user方法，这会阻塞直到收到响应
    print("\nPydantic Demo: 发送询问用户消息，系统将阻塞直到收到回复...\n")
    
    # 定义一个回调函数，用于处理用户响应
    def on_user_response(response: str) -> None:
        print(f"\n{'='*50}")
        print(f"CALLBACK TRIGGERED: 收到用户响应: '{response}'")
        print(f"可以在这里执行任何自定义逻辑，如数据分析、日志记录等")
        print(f"{'='*50}")
    
    print(f"\n{'*'*60}")
    print("开始调用ask_user，这将阻塞直到收到用户响应")
    print(f"{'*'*60}")
    
    # 使用try-except包装ask_user调用，捕获可能的异常
    try:
        user_response_str = manager.ask_user(
            prompt="您喜欢这个演示吗?",
            options=["非常喜欢", "一般", "不喜欢"],
            callback=on_user_response  # 传入回调函数
        )
        
        print(f"\n{'*'*60}")
        print(f"ask_user调用已返回，响应为: '{user_response_str}'")
        print(f"{'*'*60}")
        
        # 打印用户的响应 (这里仍然会执行，因为ask_user仍然会返回响应)
        print(f"\n{'#'*60}")
        print(f"Pydantic Demo: 收到用户回复: '{user_response_str}'，继续执行...")
        print(f"{'#'*60}")
    except Exception as e:
        print(f"\n{'!'*60}")
        print(f"ask_user调用出错: {e}")
        print(f"{'!'*60}")
        import traceback
        traceback.print_exc()
        user_response_str = "错误"
    
    # 完成
    final_result = create_result(
        content="Pydantic models demo completed",
        metadata={
            "total_models_shown": 5,
            "models": ["StreamContent", "CodeContent", "MarkdownContent", 
                        "AskUserContent", "UserResponseContent"],
            "user_response": user_response_str
        }
    )
    manager.write_result(final_result.to_dict())
    
        


def system_b_demo(manager) -> None:
    """
    Demo for System B (consumer).
    
    Args:
        event_file: Path to the event file
    """
    # 创建事件管理器        
    last_event_id = None
    print("System B: 开始监听事件...")                
    
    # 持续处理事件的标志
    running = True
    while running:                            
        # 读取一般事件
        try:
            events = manager.read_events(block=True)  # 不阻塞读取普通事件
            
            if events:
                for event in events:                        
                    if event.event_type != EventType.ASK_USER:
                        print(f"System B: 收到 {event.event_type.name} 事件: {event.content}")

                    if event.event_type == EventType.ASK_USER:
                        prompt = event.content.get("prompt", "")
                        options = event.content.get("options", [])
                        
                        # 从控制台获取用户输入
                        print(f"\n[问题] {prompt}")
                        if options:
                            print(f"选项: {', '.join(options)}")
                        
                        # 从命令行获取用户输入
                        valid_response = False
                        response = ""
                        while not valid_response:
                            response = input("\n请输入您的回答: ").strip()
                            if not options or response in options:
                                valid_response = True
                            else:
                                print(f"请输入有效的选项: {', '.join(options)}")
                        
                        print(f"您的回答: {response}")
                        
                        # 发送响应
                        manager.respond_to_user(event.event_id, response)
                        print(f"System B: 已发送响应 '{response}' 到事件 {event.event_id}")
                    
                    # 更新最后事件ID
                    last_event_id = event.event_id
                
                # 检查是否有完成事件
                if any(e.event_type == EventType.RESULT and 
                        (e.content.get("message") == "System A completed" or 
                        e.content.get("message") == "Stream data demo completed" or
                        e.content.get("content") == "Pydantic models demo completed" or
                        e.content.get("message") == "Advanced callback demo completed")
                        for e in events):
                    print("System B: 检测到演示完成事件，将退出监听")
                    running = False
        except Exception as e:
            print(f"System B: 处理一般事件时出错: {e}")
        
        # 短暂休眠，避免CPU占用过高
        time.sleep(0.05)  # 减少休眠时间，提高响应性
    



def run_demo() -> None:
    """
    Run a complete demo with both systems.
    
    Args:
        demo_type: Type of demo to run ("basic", "stream", "pydantic", or "callback")
    """
    # 创建临时事件文件
    event_file = os.path.join(os.path.dirname(__file__), "demo_events.jsonl")
    
    # 删除已存在的文件
    if os.path.exists(event_file):
        os.remove(event_file)
    
    print("=" * 60)
    print("事件系统演示")
    print("=" * 60)
    print("这个演示展示了System A和System B之间的通信。")
    print("System A: 生产者，发送事件，包括ASK_USER事件")
    print("System B: 消费者，读取事件，处理ASK_USER事件并获取用户输入")
    print("\n当System A发送ASK_USER事件时，它会被阻塞直到收到回复")
    print("System B会显示问题并等待您的输入，然后响应给System A")
    
    
    print("=" * 60)

    manager = EventManager.create(event_file)          
    
    # 在单独的线程中运行System B
    b_thread = threading.Thread(target=system_b_demo, args=(manager,))
    b_thread.daemon = True
    b_thread.start()
    

    
    # 根据demo类型运行相应的示例    
    pydantic_models_demo(manager)    
    
    # 等待System B完成
    print("等待System B完成...")
    b_thread.join(timeout=20.0)  # 增加超时时间到20秒
    
    print("\n" + "=" * 60)
    print("演示已完成")
    print("=" * 60)


if __name__ == "__main__":        
    run_demo() 