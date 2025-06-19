#!/usr/bin/env python3
"""
当前对话持久化功能演示

演示当前对话设置在应用重启后的持久化恢复功能。
"""

import os
import tempfile
from autocoder.common.conversations import (
    PersistConversationManager,
    ConversationManagerConfig
)


def test_persistence():
    """测试当前对话的持久化功能"""
    
    # 使用固定的临时目录路径
    test_dir = "/tmp/auto_coder_persistence_test"
    
    print("=== 当前对话持久化功能演示 ===\n")
    
    # 第一阶段：创建对话并设置当前对话
    print("第一阶段：创建管理器并设置当前对话")
    config = ConversationManagerConfig(storage_path=test_dir)
    manager1 = PersistConversationManager(config)
    
    # 创建对话
    conv_id = manager1.create_conversation(
        name="持久化测试对话",
        description="测试当前对话的持久化功能"
    )
    print(f"   创建对话: {conv_id}")
    
    # 设置为当前对话
    manager1.set_current_conversation(conv_id)
    print(f"   设置当前对话: {conv_id}")
    
    # 添加一些消息
    manager1.append_message_to_current("user", "第一条消息")
    manager1.append_message_to_current("assistant", "第一条回复")
    
    current_conv = manager1.get_current_conversation()
    print(f"   消息数量: {len(current_conv['messages'])}")
    
    # 显示配置文件位置
    config_file = os.path.join(test_dir, "index", "config.json")
    print(f"   配置文件位置: {config_file}")
    
    # 检查配置文件是否存在
    if os.path.exists(config_file):
        print("   ✅ 配置文件已创建")
        import json
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        print(f"   配置内容: {config_data}")
    else:
        print("   ❌ 配置文件未创建")
    
    # 模拟应用关闭
    print("\n模拟应用关闭...")
    del manager1
    
    # 第二阶段：重新创建管理器，测试持久化恢复
    print("\n第二阶段：重新创建管理器，测试持久化恢复")
    manager2 = PersistConversationManager(config)
    
    # 检查当前对话是否恢复
    restored_id = manager2.get_current_conversation_id()
    print(f"   恢复的当前对话ID: {restored_id}")
    
    if restored_id == conv_id:
        print("   ✅ 当前对话ID恢复成功")
        
        # 获取恢复的对话详情
        restored_conv = manager2.get_current_conversation()
        if restored_conv:
            print(f"   恢复的对话名称: {restored_conv['name']}")
            print(f"   恢复的消息数量: {len(restored_conv['messages'])}")
            
            # 继续向恢复的当前对话添加消息
            manager2.append_message_to_current("user", "应用重启后的消息")
            updated_conv = manager2.get_current_conversation()
            print(f"   添加消息后数量: {len(updated_conv['messages'])}")
            
            print("   ✅ 持久化功能完全正常")
        else:
            print("   ❌ 无法获取恢复的对话详情")
    else:
        print("   ❌ 当前对话ID恢复失败")
    
    # 第三阶段：测试清除和重新设置
    print("\n第三阶段：测试清除和重新设置")
    manager2.clear_current_conversation()
    print("   清除当前对话")
    
    # 再次检查配置文件
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        print(f"   清除后配置内容: {config_data}")
    
    # 第四阶段：再次创建管理器验证清除效果
    print("\n第四阶段：验证清除效果")
    manager3 = PersistConversationManager(config)
    final_current_id = manager3.get_current_conversation_id()
    print(f"   最终当前对话ID: {final_current_id}")
    
    if final_current_id is None:
        print("   ✅ 清除功能正常")
    else:
        print("   ❌ 清除功能异常")
    
    # 清理测试目录
    print(f"\n清理测试目录: {test_dir}")
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("   ✅ 清理完成")
    
    print("\n=== 持久化测试完成 ===")


if __name__ == "__main__":
    test_persistence() 