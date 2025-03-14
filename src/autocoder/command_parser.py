from typing import Dict, List, Tuple, Any, Optional
import re


class CommandParser:
    """
    命令解析器，用于解析命令行格式的查询字符串。
    支持以下格式：
    1. /command arg1 arg2
    2. /command key1=value1 key2=value2
    3. /command arg1 key1=value1
    4. /command1 arg1 /command2 arg2
    5. /command1 /command2 arg2
    6. /command1 /command2 key=value
    7. /command key="value with spaces"
    8. /command key='value with spaces'
    
    注意：路径参数（如/path/to/file）不会被识别为命令。
    """

    def __init__(self):
        # 匹配命令的正则表达式 - 必须是以/开头，后跟单词字符，且不能后跟/或.
        # (?<!\S) 确保命令前是字符串开头或空白字符
        self.command_pattern = r'(?<!\S)/(\w+)(?!/|\.)'
        # 匹配键值对参数的正则表达式，支持带引号的值
        self.key_value_pattern = r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|([^\s"\']+))(?:\s|$)'
        # 匹配路径模式的正则表达式
        self.path_pattern = r'/\w+(?:/[^/\s]+)+'

    def parse(self, query: str) -> Dict[str, Any]:
        """
        解析命令行格式的查询字符串，返回命令和参数的字典。
        
        参数:
            query: 命令行格式的查询字符串
            
        返回:
            Dict[str, Any]: 命令和参数的字典，格式为：
                {
                    'command1': {
                        'args': ['arg1', 'arg2'],
                        'kwargs': {'key1': 'value1', 'key2': 'value with spaces'}
                    },
                    'command2': {
                        'args': [],
                        'kwargs': {'key': 'value'}
                    }
                }
        """
        if not query or not query.strip():
            return {}

        # 预处理：标记路径参数，避免被识别为命令
        processed_query = query
        path_matches = re.finditer(self.path_pattern, query)
        placeholders = {}
        
        for i, match in enumerate(path_matches):
            path = match.group(0)
            placeholder = f"__PATH_PLACEHOLDER_{i}__"
            placeholders[placeholder] = path
            processed_query = processed_query.replace(path, placeholder, 1)

        # 找出所有命令
        commands = re.findall(self.command_pattern, processed_query)
        if not commands:
            return {}

        # 将查询字符串按命令分割
        parts = re.split(self.command_pattern, processed_query)
        # 第一个元素是空字符串或之前的非命令内容，保留它
        first_part = parts[0]
        parts = parts[1:]

        result = {}
        
        # 处理每个命令和它的参数
        for i in range(0, len(parts), 2):
            command = parts[i]
            
            # 获取此命令的参数部分
            params_str = parts[i+1].strip() if i+1 < len(parts) else ""
            
            # 恢复路径参数的原始值
            for placeholder, path in placeholders.items():
                params_str = params_str.replace(placeholder, path)
            
            # 解析参数
            args, kwargs = self._parse_params(params_str)
            
            result[command] = {
                'args': args,
                'kwargs': kwargs
            }
            
        return result

    def _parse_params(self, params_str: str) -> Tuple[List[str], Dict[str, str]]:
        """
        解析参数字符串，区分位置参数和键值对参数。
        支持带引号(双引号或单引号)的值，引号内可以包含空格。
        
        参数:
            params_str: 参数字符串
            
        返回:
            Tuple[List[str], Dict[str, str]]: 位置参数列表和键值对参数字典
        """
        args = []
        kwargs = {}
        
        if not params_str:
            return args, kwargs
        
        # 找出所有键值对
        key_value_pairs = re.findall(self.key_value_pattern, params_str)
        
        # 如果有键值对，处理它们
        if key_value_pairs:
            for match in key_value_pairs:
                key = match[0]
                # 值可能在三个捕获组中的一个，取非空的那个
                value = match[1] or match[2] or match[3]
                kwargs[key] = value.strip()
                
            # 替换带引号的键值对
            processed_params_str = params_str
            for match in re.finditer(self.key_value_pattern, params_str):
                full_match = match.group(0)
                processed_params_str = processed_params_str.replace(full_match, "", 1).strip()
            
            # 现在 processed_params_str 中应该只剩下位置参数
            
            # 处理带引号的位置参数
            quote_pattern = r'(?:"([^"]*?)"|\'([^\']*?)\')'
            quoted_args = re.findall(quote_pattern, processed_params_str)
            for quoted_arg in quoted_args:
                # 取非空的那个捕获组
                arg = quoted_arg[0] or quoted_arg[1]
                args.append(arg)
                # 从参数字符串中移除这个带引号的参数
                quoted_pattern = f'"{arg}"' if quoted_arg[0] else f"'{arg}'"
                processed_params_str = processed_params_str.replace(quoted_pattern, "", 1).strip()
            
            # 分割剩余的位置参数（不带引号的）
            remaining_args = [arg.strip() for arg in processed_params_str.split() if arg.strip()]
            args.extend(remaining_args)
        else:
            # 如果没有键值对，处理所有参数作为位置参数
            
            # 处理带引号的位置参数
            quote_pattern = r'(?:"([^"]*?)"|\'([^\']*?)\')'
            quoted_args = re.findall(quote_pattern, params_str)
            processed_params_str = params_str
            
            for quoted_arg in quoted_args:
                # 取非空的那个捕获组
                arg = quoted_arg[0] or quoted_arg[1]
                args.append(arg)
                # 从参数字符串中移除这个带引号的参数
                quoted_pattern = f'"{arg}"' if quoted_arg[0] else f"'{arg}'"
                processed_params_str = processed_params_str.replace(quoted_pattern, "", 1).strip()
            
            # 分割剩余的位置参数（不带引号的）
            remaining_args = [arg.strip() for arg in processed_params_str.split() if arg.strip()]
            args.extend(remaining_args)
        
        return args, kwargs
    
    def parse_command(self, query: str, command: str) -> Optional[Dict[str, Any]]:
        """
        解析特定命令的参数。
        
        参数:
            query: 命令行格式的查询字符串
            command: 要解析的命令名
            
        返回:
            Optional[Dict[str, Any]]: 如果找到命令，返回其参数；否则返回None
        """
        commands = self.parse(query)
        return commands.get(command)


def parse_query(query: str) -> Dict[str, Any]:
    """
    解析命令行格式的查询字符串的便捷函数。
    
    参数:
        query: 命令行格式的查询字符串
        
    返回:
        Dict[str, Any]: 命令和参数的字典
    """
    parser = CommandParser()
    return parser.parse(query)


def has_command(query: str, command: str) -> bool:
    """
    检查查询字符串中是否包含特定命令。
    
    参数:
        query: 命令行格式的查询字符串
        command: 要检查的命令名
        
    返回:
        bool: 如果包含命令返回True，否则返回False
    """
    parser = CommandParser()
    commands = parser.parse(query)
    return command in commands


def get_command_args(query: str, command: str) -> List[str]:
    """
    获取特定命令的位置参数。
    
    参数:
        query: 命令行格式的查询字符串
        command: 要获取参数的命令名
        
    返回:
        List[str]: 命令的位置参数列表，如果命令不存在返回空列表
    """
    parser = CommandParser()
    command_info = parser.parse_command(query, command)
    if command_info:
        return command_info['args']
    return []


def get_command_kwargs(query: str, command: str) -> Dict[str, str]:
    """
    获取特定命令的键值对参数。
    
    参数:
        query: 命令行格式的查询字符串
        command: 要获取参数的命令名
        
    返回:
        Dict[str, str]: 命令的键值对参数字典，如果命令不存在返回空字典
    """
    parser = CommandParser()
    command_info = parser.parse_command(query, command)
    if command_info:
        return command_info['kwargs']
    return {}


# 示例用法
if __name__ == "__main__":
    # 测试各种格式的查询
    test_queries = [
        "/learn hello world /commit 123456",
        "/learn /commit 123456",
        "/learn /commit commit_id=123456",
        "/learn msg=hello /commit commit_id=123456",
        "/learn hello key=value /commit",
        # 带引号的值
        '/learn msg="hello world" /commit message="Fix bug #123"',
        "/learn 'quoted arg' key='value with spaces' /commit",
        # 路径参数测试
        "/learn /path/to/file.txt",
        "/commit message='Added /path/to/file.txt'",
        "Check /path/to/file.txt and also /another/path/file.md",
        "/clone /path/to/repo /checkout branch",
        "Use the file at /usr/local/bin/python with /learn"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        result = parse_query(query)
        print(f"Parsed: {result}")
        
        if has_command(query, "commit"):
            args = get_command_args(query, "commit")
            kwargs = get_command_kwargs(query, "commit")
            print(f"Commit args: {args}")
            print(f"Commit kwargs: {kwargs}") 