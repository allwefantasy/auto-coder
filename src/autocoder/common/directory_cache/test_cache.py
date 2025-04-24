import pytest
import os
import tempfile
import shutil
import asyncio
from unittest.mock import patch, MagicMock

# 导入被测模块
from autocoder.common.directory_cache.cache import DirectoryCache

# 测试环境辅助函数
def create_test_environment(base_dir, structure):
    """创建测试所需的文件/目录结构"""
    for path, content in structure.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)

# Pytest Fixture: 临时目录
@pytest.fixture(scope="function")
def temp_test_dir():
    """提供一个临时的、测试后自动清理的目录"""
    temp_dir = tempfile.mkdtemp()
    print(f"创建测试临时目录: {temp_dir}")
    yield temp_dir
    print(f"清理测试临时目录: {temp_dir}")
    shutil.rmtree(temp_dir)

# Pytest Fixture: 重置单例
@pytest.fixture(autouse=True)
def reset_singleton():
    """每次测试前重置DirectoryCache单例"""
    DirectoryCache._instance = None
    yield
    DirectoryCache._instance = None

# Pytest Fixture: 文件监视器模拟
@pytest.fixture
def mock_file_monitor():
    """模拟文件监视器"""
    mock_monitor = MagicMock()
    mock_monitor.register = MagicMock()
    mock_monitor.is_running = MagicMock(return_value=False)
    mock_monitor.start = MagicMock()
    
    with patch('autocoder.common.directory_cache.cache.get_file_monitor', return_value=mock_monitor):
        yield mock_monitor

# --- 测试用例 ---

@pytest.mark.asyncio
async def test_initialization(temp_test_dir, mock_file_monitor):
    """测试DirectoryCache的初始化和单例模式"""
    # 创建测试文件结构
    create_test_environment(temp_test_dir, {
        "file1.txt": "测试内容1",
        "subdir/file2.txt": "测试内容2",
        ".gitignore": "*.ignored"
    })
    create_test_environment(temp_test_dir, {
        "file3.ignored": "这个文件应该被忽略"
    })
    
    # 获取实例
    cache = DirectoryCache.get_instance(temp_test_dir)
    
    # 验证单例模式
    assert DirectoryCache.get_instance() is cache
    assert cache.root == os.path.abspath(temp_test_dir)
    
    # 验证文件缓存构建
    assert len(cache.files_set) == 3  # file1.txt, subdir/file2.txt, .gitignore
    assert os.path.join(temp_test_dir, "file1.txt") in [os.path.normpath(f) for f in cache.files_set]
    assert os.path.join(temp_test_dir, "subdir/file2.txt") in [os.path.normpath(f) for f in cache.files_set]
    
    # 验证监视器注册
    mock_file_monitor.register.assert_called_once()
    mock_file_monitor.start.assert_called_once()

@pytest.mark.asyncio
async def test_query_all_files(temp_test_dir, mock_file_monitor):
    """测试查询所有文件"""
    # 创建测试文件结构
    create_test_environment(temp_test_dir, {
        "file1.py": "def test(): pass",
        "file2.txt": "text content",
        "subdir/file3.py": "class Test: pass"
    })
    
    # 获取实例并查询所有文件
    cache = DirectoryCache.get_instance(temp_test_dir)
    result = await cache.query(["*"])
    
    # 验证结果
    assert len(result) == 3
    assert sorted([os.path.basename(f) for f in result]) == ["file1.py", "file2.txt", "file3.py"]

@pytest.mark.asyncio
async def test_query_with_pattern(temp_test_dir, mock_file_monitor):
    """测试使用模式查询文件"""
    # 创建测试文件结构
    create_test_environment(temp_test_dir, {
        "file1.py": "def test(): pass",
        "file2.txt": "text content",
        "subdir/file3.py": "class Test: pass",
        "another.doc": "document"
    })
    
    # 获取实例
    cache = DirectoryCache.get_instance(temp_test_dir)
    
    # 测试不同的查询模式
    py_files = await cache.query(["*.py"])
    assert len(py_files) == 2
    assert all(f.endswith('.py') for f in py_files)
    
    txt_files = await cache.query(["*.txt"])
    assert len(txt_files) == 1
    assert txt_files[0].endswith('file2.txt')
    
    # 测试多模式查询
    mixed_files = await cache.query(["*.py", "*.txt"])
    assert len(mixed_files) == 3
    assert len([f for f in mixed_files if f.endswith('.py')]) == 2
    assert len([f for f in mixed_files if f.endswith('.txt')]) == 1

@pytest.mark.asyncio
async def test_file_change_events(temp_test_dir, mock_file_monitor):
    """测试文件变更事件处理"""
    from watchfiles import Change
    
    # 创建测试文件结构
    create_test_environment(temp_test_dir, {
        "file1.txt": "初始内容"
    })
    
    # 获取实例
    cache = DirectoryCache.get_instance(temp_test_dir)
    
    # 初始状态
    file_path = os.path.join(temp_test_dir, "file1.txt")
    abs_file_path = os.path.abspath(file_path)
    assert abs_file_path in cache.files_set
    
    # 测试删除事件
    await cache._on_change(Change.deleted, abs_file_path)
    assert abs_file_path not in cache.files_set
    
    # 测试添加事件
    await cache._on_change(Change.added, abs_file_path)
    assert abs_file_path in cache.files_set
    
    # 测试修改事件 (不应改变集合)
    initial_set_size = len(cache.files_set)
    await cache._on_change(Change.modified, abs_file_path)
    assert len(cache.files_set) == initial_set_size
    assert abs_file_path in cache.files_set
    
    # 测试新文件
    new_file_path = os.path.join(temp_test_dir, "newfile.txt")
    abs_new_file_path = os.path.abspath(new_file_path)
    await cache._on_change(Change.added, abs_new_file_path)
    assert abs_new_file_path in cache.files_set

@pytest.mark.asyncio
async def test_reinitialization_with_different_root(temp_test_dir, mock_file_monitor):
    """测试使用不同根目录重新初始化缓存"""
    # 创建第一个测试目录
    first_dir = os.path.join(temp_test_dir, "first")
    os.makedirs(first_dir)
    create_test_environment(first_dir, {"test.txt": "first directory"})
    
    # 初始化缓存
    cache1 = DirectoryCache.get_instance(first_dir)
    assert cache1.root == os.path.abspath(first_dir)
    
    # 创建第二个测试目录
    second_dir = os.path.join(temp_test_dir, "second")
    os.makedirs(second_dir)
    create_test_environment(second_dir, {"other.txt": "second directory"})
    
    # 使用新目录重新初始化
    cache2 = DirectoryCache.get_instance(second_dir)
    assert cache2.root == os.path.abspath(second_dir)
    
    # 验证文件集合已更新
    all_files = await cache2.query(["*"])
    assert len(all_files) == 1
    assert all_files[0].endswith('other.txt') 