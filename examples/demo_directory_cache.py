import os
import shutil
import asyncio
from loguru import logger

# 导入DirectoryCache模块
from autocoder.common.directory_cache.cache import DirectoryCache
# 导入监视器模块（用于演示）
from autocoder.common.file_monitor.monitor import get_file_monitor

async def main():
    logger.info("--- 开始演示 DirectoryCache ---")

    # 1. 准备演示环境
    base_dir = "sample_directory_cache_demo"
    if os.path.exists(base_dir):
        shutil.rmtree(base_dir)
    os.makedirs(os.path.join(base_dir, "subdir"), exist_ok=True)
    
    # 创建示例文件
    with open(os.path.join(base_dir, "file1.txt"), "w") as f:
        f.write("示例文本文件内容")
    with open(os.path.join(base_dir, "file2.py"), "w") as f:
        f.write("print('Hello from Python')")
    with open(os.path.join(base_dir, "subdir", "file3.md"), "w") as f:
        f.write("# Markdown 文件\n这是一个markdown文件")
        
    logger.info(f"创建演示环境于: {base_dir}")

    # 2. 初始化 DirectoryCache
    logger.info("初始化 DirectoryCache...")
    cache = DirectoryCache.get_instance(base_dir)
    logger.info(f"缓存已初始化，根目录: {cache.root}")

    # 3. 查询所有文件
    logger.info("查询所有文件...")
    all_files = await cache.query(["*"])
    logger.info(f"共找到 {len(all_files)} 个文件:")
    for idx, file in enumerate(all_files):
        logger.info(f"  {idx+1}. {os.path.relpath(file, base_dir)}")

    # 4. 使用模式查询
    logger.info("\n使用不同模式查询文件...")
    
    # 查询Python文件
    py_files = await cache.query(["*.py"])
    logger.info(f"Python文件 (*.py): {len(py_files)} 个")
    for file in py_files:
        logger.info(f"  - {os.path.relpath(file, base_dir)}")
    
    # 查询Markdown文件
    md_files = await cache.query(["*.md"])
    logger.info(f"Markdown文件 (*.md): {len(md_files)} 个")
    for file in md_files:
        logger.info(f"  - {os.path.relpath(file, base_dir)}")
    
    # 查询子目录中的文件
    subdir_files = await cache.query(["subdir/*"])
    logger.info(f"子目录文件 (subdir/*): {len(subdir_files)} 个")
    for file in subdir_files:
        logger.info(f"  - {os.path.relpath(file, base_dir)}")

    # 5. 演示文件变更
    logger.info("\n演示文件变更...")
    
    # 创建新文件
    new_file_path = os.path.join(base_dir, "new_file.txt")
    with open(new_file_path, "w") as f:
        f.write("这是新创建的文件")
    logger.info(f"创建新文件: {os.path.basename(new_file_path)}")
    
    # 等待文件监视器检测变更
    logger.info("等待文件监视器检测变更 (3秒)...")
    await asyncio.sleep(3)
    
    # 重新查询所有文件，验证新文件已添加到缓存
    all_files_after = await cache.query(["*"])
    logger.info(f"变更后共有 {len(all_files_after)} 个文件:")
    for idx, file in enumerate(all_files_after):
        logger.info(f"  {idx+1}. {os.path.relpath(file, base_dir)}")
    
    # 验证是否新增了文件
    new_files = set(all_files_after) - set(all_files)
    if new_files:
        logger.info(f"检测到 {len(new_files)} 个新文件:")
        for file in new_files:
            logger.info(f"  + {os.path.relpath(file, base_dir)}")
    else:
        logger.warning("未检测到新文件，这可能是因为文件监视器未及时更新缓存。")
        logger.info("手动模拟文件添加事件...")
        from watchfiles import Change
        await cache._on_change(Change.added, os.path.abspath(new_file_path))
        
        # 再次查询验证
        final_files = await cache.query(["*"])
        logger.info(f"手动更新后共有 {len(final_files)} 个文件")

    # 6. 删除文件并观察变化
    logger.info("\n演示文件删除...")
    file_to_delete = os.path.join(base_dir, "file1.txt")
    os.remove(file_to_delete)
    logger.info(f"删除文件: {os.path.basename(file_to_delete)}")
    
    # 等待文件监视器检测变更
    logger.info("等待文件监视器检测变更 (3秒)...")
    await asyncio.sleep(3)
    
    # 手动模拟文件删除事件
    logger.info("手动模拟文件删除事件...")
    await cache._on_change(Change.deleted, os.path.abspath(file_to_delete))
    
    # 查询验证
    remaining_files = await cache.query(["*"])
    logger.info(f"删除后共有 {len(remaining_files)} 个文件:")
    for idx, file in enumerate(remaining_files):
        logger.info(f"  {idx+1}. {os.path.relpath(file, base_dir)}")

    # 7. 清理环境
    logger.info("\n清理演示环境...")
    shutil.rmtree(base_dir)
    logger.info(f"已删除演示目录: {base_dir}")

    logger.info("--- DirectoryCache 演示结束 ---")

if __name__ == "__main__":
    # 设置日志格式
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
    )
    
    # 运行异步主函数
    asyncio.run(main()) 