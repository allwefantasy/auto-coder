#!/usr/bin/env python3
"""
当前对话功能演示

演示如何使用PersistConversationManager的当前对话功能。
"""

import tempfile
import os
from autocoder.common.conversations import (
    PersistConversationManager,
    ConversationManagerConfig
)


def demo_current_conversation():
    """演示当前对话功能"""
    
    # 创建临时目录用于测试
    with tempfile.TemporaryDirectory() as temp_dir:
        config = ConversationManagerConfig(
            storage_path=os.path.join(temp_dir, "conversations")
        )
        
        manager = PersistConversationManager(config)
        
        print("=== 当前对话功能演示 ===\n")
        
        # 1. 创建几个对话
        print("1. 创建测试对话...")
        conv1_id = manager.create_conversation(
            name="Python学习",
            description="学习Python编程"
        )
        conv2_id = manager.create_conversation(
            name="AI讨论",
            description="人工智能技术讨论"
        )
        print(f"   创建对话1: {conv1_id}")
        print(f"   创建对话2: {conv2_id}")
        
        # 2. 测试当前对话为空的情况
        print("\n2. 检查初始状态...")
        current_id = manager.get_current_conversation_id()
        print(f"   当前对话ID: {current_id}")
        
        # 3. 设置当前对话
        print("\n3. 设置当前对话...")
        success = manager.set_current_conversation(conv1_id)
        print(f"   设置成功: {success}")
        
        current_id = manager.get_current_conversation_id()
        print(f"   当前对话ID: {current_id}")
        
        # 4. 获取当前对话详情
        print("\n4. 获取当前对话详情...")
        current_conv = manager.get_current_conversation()
        if current_conv:
            print(f"   当前对话名称: {current_conv['name']}")
            print(f"   当前对话描述: {current_conv['description']}")
            print(f"   消息数量: {len(current_conv.get('messages', []))}")
        
        # 5. 向当前对话添加消息
        print("\n5. 向当前对话添加消息...")
        msg1_id = manager.append_message_to_current(
            role="user",
            content="请介绍Python的基本语法"
        )
        print(f"   添加用户消息: {msg1_id}")
        
        msg2_id = manager.append_message_to_current(
            role="assistant",
            content="Python是一种简洁易学的编程语言...",
            metadata={"response_time": 1.5}
        )
        print(f"   添加助手消息: {msg2_id}")
        
        # 6. 验证消息已添加
        print("\n6. 验证消息已添加...")
        current_conv = manager.get_current_conversation()
        print(f"   更新后消息数量: {len(current_conv.get('messages', []))}")
        
        # 7. 切换到另一个对话
        print("\n7. 切换当前对话...")
        manager.set_current_conversation(conv2_id)
        current_conv = manager.get_current_conversation()
        print(f"   切换到: {current_conv['name']}")
        
        # 8. 向新的当前对话添加消息
        msg3_id = manager.append_message_to_current(
            role="user",
            content="AI的发展趋势如何？"
        )
        print(f"   添加消息到新对话: {msg3_id}")
        
        # 9. 测试统计信息
        print("\n8. 查看统计信息...")
        stats = manager.get_statistics()
        print(f"   总对话数: {stats['total_conversations']}")
        print(f"   当前对话ID: {stats['current_conversation_id']}")
        print(f"   已创建对话数: {stats['conversations_created']}")
        print(f"   已添加消息数: {stats['messages_added']}")
        
        # 10. 清除当前对话
        print("\n9. 清除当前对话...")
        success = manager.clear_current_conversation()
        print(f"   清除成功: {success}")
        
        current_id = manager.get_current_conversation_id()
        print(f"   当前对话ID: {current_id}")
        
        # 11. 测试错误处理
        print("\n10. 测试错误处理...")
        try:
            manager.append_message_to_current("user", "这应该失败")
        except Exception as e:
            print(f"   预期错误: {e}")
        
        try:
            manager.set_current_conversation("不存在的对话ID")
        except Exception as e:
            print(f"   预期错误: {type(e).__name__}")
        
        print("\n=== 演示完成 ===")


if __name__ == "__main__":
    demo_current_conversation() 