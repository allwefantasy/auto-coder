import pytest
from typing import Dict, List, Any

# 导入被测模块
from autocoder.common.ac_style_command_parser.parser import (
    CommandParser,
    parse_query,
    has_command,
    get_command_args,
    get_command_kwargs
)


class TestCommandParser:
    """CommandParser 类的单元测试"""

    @pytest.fixture
    def parser(self):
        """创建 CommandParser 实例的 fixture"""
        return CommandParser()

    def test_init(self, parser):
        """测试 CommandParser 初始化"""
        assert parser.command_pattern == r'(?<!\S)/(\w+)(?!/|\.)'
        assert parser.key_value_pattern == r'(\w+)=(?:"([^"]*?)"|\'([^\']*?)\'|([^\s"\']+))(?:\s|$)'
        assert parser.path_pattern == r'/\w+(?:/[^/\s]+)+'

    def test_parse_empty_query(self, parser):
        """测试解析空查询字符串"""
        assert parser.parse("") == {}
        assert parser.parse("   ") == {}
        assert parser.parse(None) == {}

    def test_parse_single_command_no_args(self, parser):
        """测试解析单个命令无参数"""
        result = parser.parse("/help")
        expected = {
            'help': {
                'args': [],
                'kwargs': {}
            }
        }
        assert result == expected

    def test_parse_single_command_with_args(self, parser):
        """测试解析单个命令带位置参数"""
        result = parser.parse("/search python file")
        expected = {
            'search': {
                'args': ['python', 'file'],
                'kwargs': {}
            }
        }
        assert result == expected

    def test_parse_single_command_with_kwargs(self, parser):
        """测试解析单个命令带键值对参数"""
        result = parser.parse("/search type=file ext=py")
        expected = {
            'search': {
                'args': [],
                'kwargs': {'type': 'file', 'ext': 'py'}
            }
        }
        assert result == expected

    def test_parse_single_command_mixed_args(self, parser):
        """测试解析单个命令混合参数"""
        result = parser.parse("/search python type=file ext=py")
        expected = {
            'search': {
                'args': ['python'],
                'kwargs': {'type': 'file', 'ext': 'py'}
            }
        }
        assert result == expected

    def test_parse_multiple_commands(self, parser):
        """测试解析多个命令"""
        result = parser.parse("/search python /filter type=file")
        expected = {
            'search': {
                'args': ['python'],
                'kwargs': {}
            },
            'filter': {
                'args': [],
                'kwargs': {'type': 'file'}
            }
        }
        assert result == expected

    def test_parse_quoted_values_double_quotes(self, parser):
        """测试解析带双引号的值"""
        result = parser.parse('/search query="hello world" type=file')
        expected = {
            'search': {
                'args': [],
                'kwargs': {'query': 'hello world', 'type': 'file'}
            }
        }
        assert result == expected

    def test_parse_quoted_values_single_quotes(self, parser):
        """测试解析带单引号的值"""
        result = parser.parse("/search query='hello world' type=file")
        expected = {
            'search': {
                'args': [],
                'kwargs': {'query': 'hello world', 'type': 'file'}
            }
        }
        assert result == expected

    def test_parse_quoted_args(self, parser):
        """测试解析带引号的位置参数"""
        result = parser.parse('/search "hello world" \'another arg\'')
        expected = {
            'search': {
                'args': ['hello world', 'another arg'],
                'kwargs': {}
            }
        }
        assert result == expected

    def test_parse_path_not_as_command(self, parser):
        """测试路径不被识别为命令"""
        result = parser.parse("/search /path/to/file.py")
        expected = {
            'search': {
                'args': ['/path/to/file.py'],
                'kwargs': {}
            }
        }
        assert result == expected

    def test_parse_complex_path_handling(self, parser):
        """测试复杂路径处理"""
        result = parser.parse("/search /home/user/project/src/main.py type=file")
        expected = {
            'search': {
                'args': ['/home/user/project/src/main.py'],
                'kwargs': {'type': 'file'}
            }
        }
        assert result == expected

    def test_parse_no_commands(self, parser):
        """测试没有命令的字符串"""
        result = parser.parse("just some text without commands")
        assert result == {}

    def test_parse_invalid_command_format(self, parser):
        """测试无效的命令格式"""
        # 以/开头但后面跟/或.的不是命令
        result = parser.parse("//invalid /./also_invalid")
        assert result == {}

    def test_parse_command_specific_command_exists(self, parser):
        """测试解析特定存在的命令"""
        query = "/search python /filter type=file"
        result = parser.parse_command(query, "search")
        expected = {
            'args': ['python'],
            'kwargs': {}
        }
        assert result == expected

    def test_parse_command_specific_command_not_exists(self, parser):
        """测试解析特定不存在的命令"""
        query = "/search python /filter type=file"
        result = parser.parse_command(query, "nonexistent")
        assert result is None

    def test_parse_params_empty(self, parser):
        """测试解析空参数字符串"""
        args, kwargs = parser._parse_params("")
        assert args == []
        assert kwargs == {}

    def test_parse_params_only_args(self, parser):
        """测试解析仅位置参数"""
        args, kwargs = parser._parse_params("arg1 arg2 arg3")
        assert args == ['arg1', 'arg2', 'arg3']
        assert kwargs == {}

    def test_parse_params_only_kwargs(self, parser):
        """测试解析仅键值对参数"""
        args, kwargs = parser._parse_params("key1=value1 key2=value2")
        assert args == []
        assert kwargs == {'key1': 'value1', 'key2': 'value2'}

    def test_parse_params_mixed(self, parser):
        """测试解析混合参数"""
        args, kwargs = parser._parse_params("arg1 key1=value1 arg2")
        assert args == ['arg1', 'arg2']
        assert kwargs == {'key1': 'value1'}

    def test_parse_params_quoted_values(self, parser):
        """测试解析带引号的参数值"""
        args, kwargs = parser._parse_params('key1="value with spaces" key2=\'another value\'')
        assert args == []
        assert kwargs == {'key1': 'value with spaces', 'key2': 'another value'}

    def test_parse_params_quoted_args(self, parser):
        """测试解析带引号的位置参数"""
        args, kwargs = parser._parse_params('"arg with spaces" \'another arg\' normal_arg')
        assert args == ['arg with spaces', 'another arg', 'normal_arg']
        assert kwargs == {}


class TestUtilityFunctions:
    """测试便捷函数"""

    def test_parse_query_function(self):
        """测试 parse_query 便捷函数"""
        result = parse_query("/search python type=file")
        expected = {
            'search': {
                'args': ['python'],
                'kwargs': {'type': 'file'}
            }
        }
        assert result == expected

    def test_has_command_exists(self):
        """测试 has_command 函数 - 命令存在"""
        query = "/search python /filter type=file"
        assert has_command(query, "search") is True
        assert has_command(query, "filter") is True

    def test_has_command_not_exists(self):
        """测试 has_command 函数 - 命令不存在"""
        query = "/search python /filter type=file"
        assert has_command(query, "nonexistent") is False

    def test_get_command_args_exists(self):
        """测试 get_command_args 函数 - 命令存在"""
        query = "/search python file /filter type=file"
        result = get_command_args(query, "search")
        assert result == ['python', 'file']

    def test_get_command_args_not_exists(self):
        """测试 get_command_args 函数 - 命令不存在"""
        query = "/search python file"
        result = get_command_args(query, "nonexistent")
        assert result == []

    def test_get_command_kwargs_exists(self):
        """测试 get_command_kwargs 函数 - 命令存在"""
        query = "/search python type=file ext=py"
        result = get_command_kwargs(query, "search")
        assert result == {'type': 'file', 'ext': 'py'}

    def test_get_command_kwargs_not_exists(self):
        """测试 get_command_kwargs 函数 - 命令不存在"""
        query = "/search python type=file"
        result = get_command_kwargs(query, "nonexistent")
        assert result == {}


class TestEdgeCases:
    """测试边界情况和特殊场景"""

    @pytest.fixture
    def parser(self):
        """创建 CommandParser 实例的 fixture"""
        return CommandParser()

    def test_command_at_end_of_string(self, parser):
        """测试命令在字符串末尾"""
        result = parser.parse("some text /help")
        expected = {
            'help': {
                'args': [],
                'kwargs': {}
            }
        }
        assert result == expected

    def test_command_with_special_characters_in_values(self, parser):
        """测试值中包含特殊字符"""
        result = parser.parse('/search pattern=".*\\.py$" type=regex')
        expected = {
            'search': {
                'args': [],
                'kwargs': {'pattern': '.*\\.py$', 'type': 'regex'}
            }
        }
        assert result == expected

    def test_empty_quoted_values(self, parser):
        """测试空的引号值"""
        result = parser.parse('/search query="" type=\'\'')
        expected = {
            'search': {
                'args': [],
                'kwargs': {'query': '', 'type': ''}
            }
        }
        assert result == expected

    def test_consecutive_commands(self, parser):
        """测试连续的命令"""
        result = parser.parse("/cmd1 /cmd2 /cmd3")
        expected = {
            'cmd1': {'args': [], 'kwargs': {}},
            'cmd2': {'args': [], 'kwargs': {}},
            'cmd3': {'args': [], 'kwargs': {}}
        }
        assert result == expected

    def test_command_with_numbers_and_underscores(self, parser):
        """测试包含数字和下划线的命令名"""
        result = parser.parse("/search_v2 /cmd123 arg1")
        expected = {
            'search_v2': {'args': [], 'kwargs': {}},
            'cmd123': {'args': ['arg1'], 'kwargs': {}}
        }
        assert result == expected

    def test_mixed_quotes_in_same_command(self, parser):
        """测试同一命令中混合使用单引号和双引号"""
        result = parser.parse('/search "double quoted" \'single quoted\' normal')
        expected = {
            'search': {
                'args': ['double quoted', 'single quoted', 'normal'],
                'kwargs': {}
            }
        }
        assert result == expected

    def test_whitespace_handling(self, parser):
        """测试空白字符处理"""
        result = parser.parse("  /search   arg1    arg2   key=value  ")
        expected = {
            'search': {
                'args': ['arg1', 'arg2'],
                'kwargs': {'key': 'value'}
            }
        }
        assert result == expected

    def test_complex_real_world_example(self, parser):
        """测试复杂的真实世界示例"""
        query = '/search "function definition" /filter type=python ext=py /exclude path="/test/" /limit count=10'
        result = parser.parse(query)
        expected = {
            'search': {
                'args': ['function definition'],
                'kwargs': {}
            },
            'filter': {
                'args': [],
                'kwargs': {'type': 'python', 'ext': 'py'}
            },
            'exclude': {
                'args': [],
                'kwargs': {'path': '/test/'}
            },
            'limit': {
                'args': [],
                'kwargs': {'count': '10'}
            }
        }
        assert result == expected
