"""
示例代码，展示如何使用 CompletionContent 类表示事件正常完成的情况。
"""

import time
from autocoder.events import (
    get_event_manager, EventType, 
    create_completion
)
from loguru import logger


def demo_event_completion():
    """
    演示如何使用 CompletionContent 报告任务完成情况
    """
    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    logger.info("开始演示 CompletionContent 使用示例...")
    
    # 获取事件管理器
    event_manager = get_event_manager()
    
    # 模拟一个长时间运行的任务
    logger.info("开始执行任务...")
    
    # 模拟任务的各个阶段
    stages = ["初始化", "数据加载", "数据处理", "结果验证", "完成"]
    
    for i, stage in enumerate(stages):
        # 模拟处理时间
        time.sleep(0.5)
        
        logger.info(f"任务阶段 {i+1}/{len(stages)}: {stage}")
        
        # 如果不是最后一个阶段，则报告进度
        if i < len(stages) - 1:
            # 使用 ResultContent 报告中间进度
            progress = (i + 1) / len(stages) * 100
            event_manager.write_result({
                "stage": stage,
                "progress": f"{progress:.1f}%",
                "status": "in_progress"
            })
    
    # 任务完成，使用 CompletionContent 报告完成情况
    result = {
        "processed_items": 150,
        "success_rate": 98.5,
        "warnings": 3,
        "execution_time": 2.5
    }
    
    details = {
        "operation": "data_processing",
        "timestamp_start": time.time() - 2.5,
        "timestamp_end": time.time(),
        "process_id": 12345
    }
    
    # 创建完成内容
    completion_content = create_completion(
        success_code="OP_SUCCESS",
        success_message="数据处理操作已成功完成",
        result=result,
        details=details
    )
    
    # 写入完成事件
    event_manager.write_result(completion_content.to_dict())
    
    logger.info(f"任务已完成，详细信息: {completion_content.to_json()}")
    logger.info("CompletionContent 使用示例结束")


if __name__ == "__main__":
    demo_event_completion() 