#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
对话管理器演示示例

此示例演示了如何使用全局对话管理器进行基本的对话管理操作：
1. 获取全局管理器实例
2. 创建新对话
3. 添加消息
4. 查看对话详情
5. 列出所有对话
"""

import json
import os
import sys

from autocoder.common.conversations.get_conversation_manager import (
    get_conversation_manager,
    get_conversation_manager_config,
    reset_conversation_manager
)
from autocoder.common.conversations import ConversationManagerConfig


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'='*50}")
    print(f" {title}")
    print(f"{'='*50}")


def print_json(data, title: str = ""):
    """格式化打印JSON数据"""
    if title:
        print(f"\n{title}:")
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    """主演示函数"""
    print_section("对话管理器演示开始")
    
    # 1. 获取全局管理器实例
    print_section("1. 获取全局管理器实例")
    
    # 使用默认配置
    print("使用默认配置获取管理器...")
    manager = get_conversation_manager()
    
    # 获取当前配置信息
    config = get_conversation_manager_config()
    print(f"存储路径: {config.storage_path}")
    print(f"最大缓存大小: {config.max_cache_size}")
    print(f"备份启用: {config.backup_enabled}")
    
    # 2. 创建新对话
    print_section("2. 创建新对话")
    
    # 创建简单对话
    print("创建第一个对话...")
    conversation_id_1 = manager.create_conversation(
        name="Python编程助手",
        description="关于Python编程的讨论"
    )
    print(f"创建的对话ID: {conversation_id_1}")
    
    # 创建带初始消息和元数据的对话
    print("\n创建第二个对话（包含初始消息和元数据）...")
    conversation_id_2 = manager.create_conversation(
        name="代码审查讨论",
        description="项目代码审查和优化建议",
        initial_messages=[
            {
                "role": "user",
                "content": "请帮我审查这个Python函数的实现"
            },
            {
                "role": "assistant",
                "content": "好的，请提供您需要审查的代码，我会仔细检查并给出建议。"
            }
        ],
        metadata={
            "project": "auto-coder",
            "type": "code_review",
            "priority": "high"
        }
    )
    print(f"创建的对话ID: {conversation_id_2}")
    
    # 3. 向对话添加消息
    print_section("3. 向对话添加消息")
    
    # 向第一个对话添加消息
    print("向第一个对话添加消息...")
    message_id_1 = manager.append_message(
        conversation_id=conversation_id_1,
        role="user",
        content="请解释Python中的装饰器是什么？",
        metadata={"timestamp": "2024-01-01 10:00:00"}
    )
    print(f"添加的消息ID: {message_id_1}")
    
    message_id_2 = manager.append_message(
        conversation_id=conversation_id_1,
        role="assistant",
        content="装饰器是Python中的一个强大特性，允许你修改或扩展函数的行为而不改变其定义。装饰器本质上是一个函数，它接受另一个函数作为参数并返回一个新函数。",
        metadata={"response_time": 1.5, "model": "gpt-4"}
    )
    print(f"助手回复消息ID: {message_id_2}")
    
    # 批量添加消息到第二个对话
    print("\n向第二个对话批量添加消息...")
    message_ids = manager.append_messages(
        conversation_id=conversation_id_2,
        messages=[
            {
                "role": "user",
                "content": """
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)
""",
                "metadata": {"code_type": "function"}
            },
            {
                "role": "assistant",
                "content": """
这个函数的逻辑是正确的，但有一些改进建议：

1. 添加空列表检查，避免除零错误
2. 添加类型提示
3. 添加文档字符串
4. 可以使用内置的sum()函数简化代码

改进后的代码：
```python
def calculate_average(numbers: list[float]) -> float:
    \"\"\"计算数字列表的平均值\"\"\"
    if not numbers:
        raise ValueError("输入列表不能为空")
    return sum(numbers) / len(numbers)
```
""",
                "metadata": {"suggestion_type": "code_improvement"}
            }
        ]
    )
    print(f"批量添加的消息IDs: {message_ids}")
    
    # 4. 查看对话详情
    print_section("4. 查看对话详情")
    
    # 获取第一个对话的详情
    conversation_1 = manager.get_conversation(conversation_id_1)
    print_json(conversation_1, "第一个对话详情")
    
    # 获取第一个对话的消息
    messages_1 = manager.get_messages(conversation_id_1)
    print_json(messages_1, "第一个对话的消息")
    
    # 获取第二个对话的详情
    conversation_2 = manager.get_conversation(conversation_id_2)
    print_json(conversation_2, "第二个对话详情")
    
    # 5. 列出所有对话
    print_section("5. 列出所有对话")
    
    # 获取所有对话
    all_conversations = manager.list_conversations()
    print(f"总对话数量: {len(all_conversations)}")
    
    for i, conv in enumerate(all_conversations, 1):
        print(f"\n对话 {i}:")
        print(f"  ID: {conv['conversation_id']}")
        print(f"  名称: {conv['name']}")
        print(f"  描述: {conv['description']}")
        print(f"  创建时间: {conv['created_at']}")
        print(f"  更新时间: {conv['updated_at']}")
        # 计算消息数量
        message_count = len(conv.get('messages', []))
        print(f"  消息数量: {message_count}")
        if conv.get('metadata'):
            print(f"  元数据: {conv['metadata']}")
    
    # 6. 搜索对话
    print_section("6. 搜索功能演示")
    
    # 搜索包含"Python"的对话
    search_results = manager.search_conversations("Python")
    print(f"搜索'Python'的结果数量: {len(search_results)}")
    for result in search_results:
        conv = result['conversation']
        score = result['score']
        print(f"  - {conv['name']}: {conv['description']} (相关度: {score:.2f})")
    
    # 在特定对话中搜索消息
    message_search = manager.search_messages(conversation_id_1, "装饰器")
    print(f"\n在对话中搜索'装饰器'的消息数量: {len(message_search)}")
    for result in message_search:
        msg = result['message']
        score = result['score']
        print(f"  - {msg['role']}: {msg['content'][:50]}... (相关度: {score:.2f})")
    
    # 7. 获取统计信息
    print_section("7. 系统统计信息")
    
    stats = manager.get_statistics()
    print_json(stats, "系统统计")
    
    # 8. 健康检查
    print_section("8. 系统健康检查")
    
    health = manager.health_check()
    print_json(health, "健康状态")
    
    print_section("演示完成")
    print("对话数据已保存到:", config.storage_path)
    print("您可以重新运行此脚本来查看持久化的数据。")


def demo_custom_config():
    """演示使用自定义配置"""
    print_section("自定义配置演示")
    
    # 重置管理器以使用新配置
    custom_config = ConversationManagerConfig(
        storage_path="./demo_conversations",
        max_cache_size=50,
        backup_enabled=False
    )
    
    print("重置管理器并使用自定义配置...")
    reset_conversation_manager(custom_config)
    
    # 获取新的管理器实例
    manager = get_conversation_manager()
    config = get_conversation_manager_config()
    
    print(f"新的存储路径: {config.storage_path}")
    print(f"新的缓存大小: {config.max_cache_size}")
    print(f"备份启用: {config.backup_enabled}")
    
    # 创建一个测试对话
    conv_id = manager.create_conversation(
        name="自定义配置测试",
        description="使用自定义配置创建的对话"
    )
    
    conversation = manager.get_conversation(conv_id)
    print_json(conversation, "使用自定义配置创建的对话")


if __name__ == "__main__":
    try:
        # 主演示
        main()
        
        # 可选：演示自定义配置（取消注释以启用）
        # demo_custom_config()
        
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*50)
    print(" 演示结束")
    print("="*50) 