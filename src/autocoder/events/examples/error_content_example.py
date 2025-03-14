"""
示例代码，展示如何使用 create_error 函数创建错误内容。
"""

import time
from autocoder.events import (
    get_event_manager, EventType, 
    create_error, create_completion
)
from loguru import logger


def demo_error_handling():
    """
    演示如何使用 ErrorContent 报告错误情况
    """
    # 配置日志
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level="INFO")
    
    logger.info("开始演示 ErrorContent 使用示例...")
    
    # 获取事件管理器
    event_manager = get_event_manager()
    
    # 模拟一个任务处理过程
    logger.info("开始模拟任务处理...")
    
    try:
        # 模拟正常处理的部分
        logger.info("正在处理数据...")
        time.sleep(1)
        
        # 模拟遇到错误情况
        logger.info("模拟遇到错误场景...")
        
        # 假设我们需要处理一些数据，但发现数据格式有问题
        if True:  # 模拟条件判断，总是触发错误
            # 创建错误详情
            details = {
                "operation": "data_validation",
                "input_data": {"size": 1024, "format": "json"},
                "expected_schema": "user_profile",
                "error_location": "line 42",
                "timestamp": time.time()
            }
            
            # 使用 create_error 函数创建错误内容
            error_content = create_error(
                error_code="DATA_VALIDATION_ERROR",
                error_message="数据格式验证失败，缺少必要字段",
                details=details
            )
            
            # 写入错误事件
            event_manager.write_result(error_content.to_dict())
            
            logger.error(f"任务失败: {error_content.error_message}")
            raise ValueError("数据验证失败")
            
    except Exception as e:
        logger.error(f"处理异常: {str(e)}")
        
        # 可以根据不同的异常类型创建不同的错误内容
        if isinstance(e, ValueError):
            # 已经创建了错误内容，无需再次创建
            pass
        else:
            # 处理未预期的异常
            unexpected_error = create_error(
                error_code="UNEXPECTED_ERROR",
                error_message=f"遇到意外错误: {str(e)}",
                details={"exception_type": e.__class__.__name__}
            )
            
            # 写入错误事件
            event_manager.write_result(unexpected_error.to_dict())
    else:
        # 如果没有异常，报告成功完成
        completion = create_completion(
            success_code="TASK_COMPLETED",
            success_message="任务已成功完成",
            result={"items_processed": 100}
        )
        
        # 写入完成事件
        event_manager.write_result(completion.to_dict())
        
        logger.info("任务成功完成")
    finally:
        logger.info("清理资源...")
        time.sleep(0.5)
        logger.info("ErrorContent 使用示例结束")


if __name__ == "__main__":
    demo_error_handling() 