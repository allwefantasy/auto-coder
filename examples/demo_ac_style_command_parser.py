
import os
import sys
from loguru import logger

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入被测模块
from src.autocoder.common.ac_style_command_parser.parser import (
    CommandParser,
    parse_query,
    has_command,
    get_command_args,
    get_command_kwargs
)


def main():
    logger.info("--- 开始演示 CommandParser 模块 ---")

    # 创建解析器实例
    parser = CommandParser()
    logger.info("CommandParser 实例已创建")

    # 演示用例列表
    demo_queries = [
        # 基础用例
        "/help",
        "/search python",
        "/search type=file ext=py",
        "/search python type=file ext=py",
        
        # 多命令用例
        "/search python /filter type=file",
        "/search python /filter type=file /limit count=10",
        
        # 引号处理
        '/search "hello world"',
        "/search query='complex query' type=file",
        '/search "function definition" type=python',
        
        # 路径处理
        "/search /path/to/file.py",
        "/search /home/user/project/src/main.py type=file",
        
        # 复杂真实场景
        '/search "function definition" /filter type=python ext=py /exclude path="/test/" /limit count=10',
        '/find pattern=".*\\.py$" /sort by=name order=asc',
        
        # 边界情况
        "",
        "no commands here",
        "//invalid /./also_invalid",
    ]

    logger.info(f"准备演示 {len(demo_queries)} 个查询示例")
    
    for i, query in enumerate(demo_queries, 1):
        logger.info(f"\n--- 示例 {i}: '{query}' ---")
        
        if not query.strip():
            logger.info("空查询字符串")
        
        # 使用 parse 方法解析完整查询
        try:
            result = parser.parse(query)
            if result:
                logger.success(f"解析成功，找到 {len(result)} 个命令:")
                for cmd_name, cmd_info in result.items():
                    logger.info(f"  命令: {cmd_name}")
                    logger.info(f"    位置参数: {cmd_info['args']}")
                    logger.info(f"    键值参数: {cmd_info['kwargs']}")
            else:
                logger.warning("未找到任何命令")
        except Exception as e:
            logger.error(f"解析失败: {e}")

    # 演示便捷函数
    logger.info("\n--- 演示便捷函数 ---")
    
    test_query = '/search "python function" type=file /filter ext=py /limit count=5'
    logger.info(f"测试查询: {test_query}")
    
    # 使用 parse_query 便捷函数
    logger.info("\n1. 使用 parse_query 便捷函数:")
    result = parse_query(test_query)
    logger.info(f"结果: {result}")
    
    # 使用 has_command 检查命令存在性
    logger.info("\n2. 使用 has_command 检查命令:")
    commands_to_check = ['search', 'filter', 'limit', 'nonexistent']
    for cmd in commands_to_check:
        exists = has_command(test_query, cmd)
        logger.info(f"  命令 '{cmd}' 存在: {exists}")
    
    # 使用 get_command_args 获取位置参数
    logger.info("\n3. 使用 get_command_args 获取位置参数:")
    for cmd in ['search', 'filter', 'limit']:
        args = get_command_args(test_query, cmd)
        logger.info(f"  命令 '{cmd}' 的位置参数: {args}")
    
    # 使用 get_command_kwargs 获取键值参数
    logger.info("\n4. 使用 get_command_kwargs 获取键值参数:")
    for cmd in ['search', 'filter', 'limit']:
        kwargs = get_command_kwargs(test_query, cmd)
        logger.info(f"  命令 '{cmd}' 的键值参数: {kwargs}")

    # 演示实际应用场景
    logger.info("\n--- 实际应用场景演示 ---")
    
    def simulate_search_system(query: str):
        """模拟一个基于命令的搜索系统"""
        logger.info(f"处理搜索查询: {query}")
        
        # 解析查询
        commands = parse_query(query)
        
        if not commands:
            logger.warning("没有找到有效命令")
            return
        
        # 处理搜索命令
        if has_command(query, 'search'):
            search_args = get_command_args(query, 'search')
            search_kwargs = get_command_kwargs(query, 'search')
            logger.info(f"执行搜索: 关键词={search_args}, 参数={search_kwargs}")
        
        # 处理过滤命令
        if has_command(query, 'filter'):
            filter_kwargs = get_command_kwargs(query, 'filter')
            logger.info(f"应用过滤器: {filter_kwargs}")
        
        # 处理排除命令
        if has_command(query, 'exclude'):
            exclude_kwargs = get_command_kwargs(query, 'exclude')
            logger.info(f"排除条件: {exclude_kwargs}")
        
        # 处理限制命令
        if has_command(query, 'limit'):
            limit_kwargs = get_command_kwargs(query, 'limit')
            logger.info(f"结果限制: {limit_kwargs}")
        
        logger.success("搜索查询处理完成")
    
    # 测试搜索系统
    test_queries = [
        '/search "python function" type=code',
        '/search python /filter ext=py /limit count=10',
        '/search "class definition" /filter type=python /exclude path="/test/" /limit count=5'
    ]
    
    for query in test_queries:
        logger.info(f"\n测试查询: {query}")
        simulate_search_system(query)

    logger.info("\n--- CommandParser 模块演示结束 ---")


if __name__ == "__main__":
    main()

