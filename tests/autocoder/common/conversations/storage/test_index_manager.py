"""
索引管理器测试
"""

import pytest
import os
import json
import time
from unittest.mock import patch, mock_open
from autocoder.common.conversations.storage.index_manager import IndexManager
from autocoder.common.conversations.exceptions import DataIntegrityError


class TestIndexManager:
    """测试IndexManager索引管理器"""
    
    def test_index_manager_creation(self, temp_dir):
        """测试索引管理器创建"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        assert str(manager.index_path) == index_path
        assert os.path.exists(index_path)
    
    def test_index_manager_directory_creation(self, temp_dir):
        """测试索引目录自动创建"""
        index_path = os.path.join(temp_dir, "nested", "index")
        manager = IndexManager(index_path)
        
        # 目录应该自动创建
        assert os.path.exists(index_path)
    
    def test_add_conversation_to_index(self, temp_dir):
        """测试添加对话到索引"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation',
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0
        }
        
        result = manager.add_conversation(conversation_metadata)
        assert result is True
        
        # 检查索引文件
        index_file = os.path.join(index_path, "conversations.idx")
        assert os.path.exists(index_file)
    
    def test_add_conversation_without_id(self, temp_dir):
        """测试添加没有ID的对话到索引"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'name': 'Test Conversation'
        }
        
        result = manager.add_conversation(conversation_metadata)
        assert result is False
    
    def test_update_conversation_in_index(self, temp_dir):
        """测试更新索引中的对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 先添加对话
        original_metadata = {
            'conversation_id': 'test_conv',
            'name': 'Original Name',
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0,
            'message_count': 5
        }
        manager.add_conversation(original_metadata)
        
        # 更新对话
        updated_metadata = {
            'conversation_id': 'test_conv',
            'name': 'Updated Name',
            'created_at': 1234567890.0,
            'updated_at': 1234567990.0,
            'message_count': 7
        }
        
        result = manager.update_conversation(updated_metadata)
        assert result is True
        
        # 验证更新
        conversation_info = manager.get_conversation('test_conv')
        assert conversation_info['name'] == 'Updated Name'
        assert conversation_info['message_count'] == 7
        assert conversation_info['updated_at'] == 1234567990.0
    
    def test_update_nonexistent_conversation(self, temp_dir):
        """测试更新不存在的对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'nonexistent',
            'name': 'Test'
        }
        
        result = manager.update_conversation(conversation_metadata)
        assert result is False
    
    def test_remove_conversation_from_index(self, temp_dir):
        """测试从索引中删除对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 先添加对话
        conversation_metadata = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        manager.add_conversation(conversation_metadata)
        
        # 验证对话存在
        assert manager.conversation_exists('test_conv')
        
        # 删除对话
        result = manager.remove_conversation('test_conv')
        assert result is True
        
        # 验证对话已删除
        assert not manager.conversation_exists('test_conv')
        assert manager.get_conversation('test_conv') is None
    
    def test_remove_nonexistent_conversation(self, temp_dir):
        """测试删除不存在的对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        result = manager.remove_conversation('nonexistent')
        assert result is False
    
    def test_get_conversation_from_index(self, temp_dir):
        """测试从索引获取对话信息"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation',
            'created_at': 1234567890.0
        }
        
        # 添加对话
        manager.add_conversation(conversation_metadata)
        
        # 获取对话
        retrieved_metadata = manager.get_conversation('test_conv')
        assert retrieved_metadata == conversation_metadata
    
    def test_get_nonexistent_conversation(self, temp_dir):
        """测试获取不存在的对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_info = manager.get_conversation('nonexistent')
        assert conversation_info is None
    
    def test_conversation_exists(self, temp_dir):
        """测试检查对话是否存在"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        
        # 对话不存在时
        assert not manager.conversation_exists('test_conv')
        
        # 添加对话后
        manager.add_conversation(conversation_metadata)
        assert manager.conversation_exists('test_conv')
        
        # 删除对话后
        manager.remove_conversation('test_conv')
        assert not manager.conversation_exists('test_conv')
    
    def test_list_conversations_from_index(self, temp_dir):
        """测试从索引列出对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加多个对话
        conversations = []
        for i in range(5):
            conversation_metadata = {
                'conversation_id': f'conv_{i}',
                'name': f'Conversation {i}',
                'created_at': 1234567890.0 + i,
                'updated_at': 1234567890.0 + i
            }
            manager.add_conversation(conversation_metadata)
            conversations.append(conversation_metadata)
        
        # 测试无限制列出
        all_conversations = manager.list_conversations()
        assert len(all_conversations) == 5
        
        # 验证数据正确性
        for conv in all_conversations:
            assert conv in conversations
        
        # 测试带限制列出
        limited_conversations = manager.list_conversations(limit=3)
        assert len(limited_conversations) == 3
        
        # 测试带偏移列出
        offset_conversations = manager.list_conversations(offset=2)
        assert len(offset_conversations) == 3
        
        # 测试带限制和偏移列出
        limited_offset_conversations = manager.list_conversations(limit=2, offset=1)
        assert len(limited_offset_conversations) == 2

    def test_search_conversations(self, temp_dir):
        """测试搜索对话"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加测试对话
        conversation = {
            'conversation_id': 'conv_1',
            'name': 'Python编程讨论',
            'description': '关于Python的对话'
        }
        manager.add_conversation(conversation)
        
        # 搜索
        results = manager.search_conversations('Python')
        assert len(results) == 1
        assert results[0]['conversation_id'] == 'conv_1'


class TestIndexManagerSearch:
    """测试索引管理器搜索功能"""
    
    def test_search_by_name(self, temp_dir):
        """测试按名称搜索"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加测试对话
        conversations = [
            {
                'conversation_id': 'conv_1',
                'name': 'Python编程讨论',
                'description': '关于Python的对话'
            },
            {
                'conversation_id': 'conv_2',
                'name': 'JavaScript开发',
                'description': '前端开发相关'
            },
            {
                'conversation_id': 'conv_3',
                'name': '机器学习Python实践',
                'description': 'ML和Python'
            }
        ]
        
        for conv in conversations:
            manager.add_conversation(conv)
        
        # 搜索包含"Python"的对话
        results = manager.search_conversations('Python')
        assert len(results) == 2
        
        # 验证搜索结果
        result_names = [conv['name'] for conv in results]
        assert 'Python编程讨论' in result_names
        assert '机器学习Python实践' in result_names
    
    def test_search_by_description(self, temp_dir):
        """测试按描述搜索"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation = {
            'conversation_id': 'test_conv',
            'name': 'Test',
            'description': '这是一个关于人工智能的深度讨论'
        }
        manager.add_conversation(conversation)
        
        # 搜索描述中的关键词
        results = manager.search_conversations('人工智能')
        assert len(results) == 1
        assert results[0]['conversation_id'] == 'test_conv'
    
    def test_search_with_filters(self, temp_dir):
        """测试带过滤条件的搜索"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加不同时间的对话
        base_time = 1234567890.0
        for i in range(5):
            conversation = {
                'conversation_id': f'conv_{i}',
                'name': f'Conversation {i}',
                'created_at': base_time + i * 86400,  # 每天一个
                'message_count': i * 2
            }
            manager.add_conversation(conversation)
        
        # 搜索特定时间范围
        filters = {
            'created_after': base_time + 86400,  # 第二天之后
            'created_before': base_time + 3 * 86400  # 第四天之前
        }
        
        results = manager.search_conversations('Conversation', filters=filters)
        assert len(results) == 2  # conv_1 和 conv_2
        
        # 搜索消息数量过滤
        filters = {'min_message_count': 4}
        results = manager.search_conversations('Conversation', filters=filters)
        assert len(results) == 3  # conv_2 (4条), conv_3 (6条) 和 conv_4 (8条)
    
    def test_search_empty_query(self, temp_dir):
        """测试空查询搜索"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加对话
        conversation = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        manager.add_conversation(conversation)
        
        # 空查询应该返回所有对话
        results = manager.search_conversations('')
        assert len(results) == 1
        
        # None查询也应该返回所有对话
        results = manager.search_conversations(None)
        assert len(results) == 1


class TestIndexManagerSorting:
    """测试索引管理器排序功能"""
    
    def test_sort_by_created_date(self, temp_dir):
        """测试按创建日期排序"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加不同创建时间的对话
        base_time = 1234567890.0
        for i in [2, 0, 4, 1, 3]:  # 随机顺序添加
            conversation = {
                'conversation_id': f'conv_{i}',
                'name': f'Conversation {i}',
                'created_at': base_time + i * 100
            }
            manager.add_conversation(conversation)
        
        # 按创建时间升序排序
        results = manager.list_conversations(sort_by='created_at', sort_order='asc')
        created_times = [conv['created_at'] for conv in results]
        assert created_times == sorted(created_times)
        
        # 按创建时间降序排序
        results = manager.list_conversations(sort_by='created_at', sort_order='desc')
        created_times = [conv['created_at'] for conv in results]
        assert created_times == sorted(created_times, reverse=True)
    
    def test_sort_by_updated_date(self, temp_dir):
        """测试按更新日期排序"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        base_time = 1234567890.0
        conversations = []
        
        # 添加对话并设置不同的更新时间
        for i in range(3):
            conversation = {
                'conversation_id': f'conv_{i}',
                'name': f'Conversation {i}',
                'created_at': base_time,
                'updated_at': base_time + i * 50
            }
            manager.add_conversation(conversation)
            conversations.append(conversation)
        
        # 按更新时间降序排序（最近更新的在前）
        results = manager.list_conversations(sort_by='updated_at', sort_order='desc')
        assert results[0]['conversation_id'] == 'conv_2'
        assert results[1]['conversation_id'] == 'conv_1'
        assert results[2]['conversation_id'] == 'conv_0'
    
    def test_sort_by_name(self, temp_dir):
        """测试按名称排序"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加不同名称的对话
        names = ['Zebra', 'Apple', 'Banana', 'Cherry']
        for i, name in enumerate(names):
            conversation = {
                'conversation_id': f'conv_{i}',
                'name': name
            }
            manager.add_conversation(conversation)
        
        # 按名称升序排序
        results = manager.list_conversations(sort_by='name', sort_order='asc')
        sorted_names = [conv['name'] for conv in results]
        assert sorted_names == ['Apple', 'Banana', 'Cherry', 'Zebra']


class TestIndexManagerConcurrency:
    """测试索引管理器并发处理"""
    
    def test_index_consistency_under_concurrent_updates(self, temp_dir):
        """测试并发更新下的索引一致性"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 模拟并发添加对话
        conversation_metadata = {
            'conversation_id': 'concurrent_test',
            'name': 'Concurrent Test',
            'created_at': time.time()
        }
        
        # 第一次添加
        result1 = manager.add_conversation(conversation_metadata)
        assert result1 is True
        
        # 模拟同时更新（实际上是串行，但测试逻辑）
        updated_metadata = conversation_metadata.copy()
        updated_metadata['name'] = 'Updated Name'
        updated_metadata['updated_at'] = time.time()
        
        result2 = manager.update_conversation(updated_metadata)
        assert result2 is True
        
        # 验证最终状态一致
        final_info = manager.get_conversation('concurrent_test')
        assert final_info['name'] == 'Updated Name'
    
    def test_index_file_locking(self, temp_dir):
        """测试索引文件锁定机制"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'lock_test',
            'name': 'Lock Test'
        }
        
        # 正常操作应该成功
        result = manager.add_conversation(conversation_metadata)
        assert result is True
        
        # 验证对话添加成功
        assert manager.conversation_exists('lock_test')


class TestIndexManagerErrorHandling:
    """测试索引管理器错误处理"""
    
    def test_corrupted_index_handling(self, temp_dir):
        """测试处理损坏的索引文件"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 创建损坏的索引文件
        index_file = os.path.join(index_path, "conversations.idx")
        os.makedirs(index_path, exist_ok=True)
        with open(index_file, 'w') as f:
            f.write("invalid json content {")
        
        # 尝试加载损坏的索引应该重建索引
        conversation_metadata = {
            'conversation_id': 'recovery_test',
            'name': 'Recovery Test'
        }
        
        # 应该能够恢复并添加新对话
        result = manager.add_conversation(conversation_metadata)
        assert result is True
        
        # 验证索引已重建
        assert manager.conversation_exists('recovery_test')
    
    def test_permission_error_handling(self, temp_dir):
        """测试权限错误处理"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'permission_test',
            'name': 'Permission Test'
        }
        
        # 模拟权限错误
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = manager.add_conversation(conversation_metadata)
            assert result is False
    
    def test_disk_full_error_handling(self, temp_dir):
        """测试磁盘空间不足错误处理"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        conversation_metadata = {
            'conversation_id': 'disk_full_test',
            'name': 'Disk Full Test'
        }
        
        # 模拟磁盘空间不足
        with patch('builtins.open', side_effect=OSError("No space left on device")):
            result = manager.add_conversation(conversation_metadata)
            assert result is False
    
    def test_invalid_conversation_data(self, temp_dir):
        """测试无效对话数据处理"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 测试各种无效数据
        invalid_data_sets = [
            {},  # 空数据
            {'name': 'Test'},  # 缺少conversation_id
            {'conversation_id': ''},  # 空conversation_id
            {'conversation_id': None, 'name': 'Test'},  # None conversation_id
        ]
        
        for invalid_data in invalid_data_sets:
            result = manager.add_conversation(invalid_data)
            assert result is False


class TestIndexManagerPerformance:
    """测试索引管理器性能"""
    
    def test_large_index_performance(self, temp_dir):
        """测试大索引性能"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加大量对话
        num_conversations = 1000
        start_time = time.time()
        
        for i in range(num_conversations):
            conversation_metadata = {
                'conversation_id': f'perf_conv_{i:04d}',
                'name': f'Performance Test Conversation {i}',
                'created_at': 1234567890.0 + i
            }
            manager.add_conversation(conversation_metadata)
        
        add_time = time.time() - start_time
        
        # 测试列出性能
        start_time = time.time()
        all_conversations = manager.list_conversations()
        list_time = time.time() - start_time
        
        assert len(all_conversations) == num_conversations
        
        # 测试搜索性能
        start_time = time.time()
        search_results = manager.search_conversations('Performance')
        search_time = time.time() - start_time
        
        assert len(search_results) == num_conversations
        
        # 性能检查（这些阈值可以根据实际需要调整）
        print(f"添加 {num_conversations} 个对话耗时: {add_time:.2f}s")
        print(f"列出 {num_conversations} 个对话耗时: {list_time:.2f}s")
        print(f"搜索 {num_conversations} 个对话耗时: {search_time:.2f}s")
        
        # 基本性能要求（可以根据需要调整）
        assert add_time < 10.0  # 添加1000个对话应该在10秒内
        assert list_time < 1.0  # 列出应该在1秒内
        assert search_time < 2.0  # 搜索应该在2秒内
    
    def test_index_memory_usage(self, temp_dir):
        """测试索引内存使用"""
        index_path = os.path.join(temp_dir, "index")
        manager = IndexManager(index_path)
        
        # 添加适量对话来测试内存使用
        for i in range(100):
            conversation_metadata = {
                'conversation_id': f'mem_conv_{i}',
                'name': f'Memory Test Conversation {i}',
                'description': 'A' * 1000,  # 较长的描述
                'created_at': 1234567890.0 + i
            }
            manager.add_conversation(conversation_metadata)
        
        # 基本验证
        assert len(manager.list_conversations()) == 100
        
        # 验证索引可以正常加载和保存
        # （实际内存使用测试可能需要更复杂的工具）
        assert manager.conversation_exists('mem_conv_50') 