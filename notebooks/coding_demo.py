from pathlib import Path
from typing import List, Dict, Any
import byzerllm
from autocoder.utils.llms import get_single_llm
from autocoder.common import AutoCoderArgs
from autocoder.auto_coder_runner import coding
from autocoder.utils.queue_communicate import queue_communicate
import threading
import time

def create_test_files() -> List[str]:
    """创建测试文件并返回文件路径列表"""
    files = []
    for i in range(4):
        file_path = f"file{i}.py"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"def test_function_{i}():\n    pass\n")
        files.append(file_path)
    return files

def event_listener(request_id: str):
    """监听事件并打印"""
    while True:
        event = queue_communicate.get_event(request_id)
        if event:
            print(f"Received event: {event.event_type} - {event.data}")
        time.sleep(0.1)

def main():
    # 创建测试文件
    create_test_files()
    
    # 模拟 AutoCoderArgs
    args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=30,
        query="Test query"
    )

    # 获取 LLM 实例
    llm = get_single_llm("v3_chat", product_mode="lite")

    # 生成唯一的 request_id
    request_id = "test_request_id"
    
    # 启动事件监听线程
    listener_thread = threading.Thread(target=event_listener, args=(request_id,))
    listener_thread.daemon = True
    listener_thread.start()

    # 设置 request_id
    args.request_id = request_id

    # 在新线程中调用 coding 方法
    coding_thread = threading.Thread(target=coding, args=("Test query",))
    coding_thread.start()
    coding_thread.join()

if __name__ == "__main__":
    main()