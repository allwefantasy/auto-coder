
import pytest
import tempfile
import shutil
import os
from unittest.mock import Mock

from autocoder.common.v2.agent.agentic_edit_tools.todo_write_tool_resolver import TodoWriteToolResolver
from autocoder.common.v2.agent.agentic_edit_types import TodoWriteTool
from autocoder.common import AutoCoderArgs


class TestTodoWriteToolResolver:
    """测试 TodoWriteToolResolver 类的功能"""

    def setup_method(self):
        """每个测试方法执行前的设置"""
        self.temp_dir = tempfile.mkdtemp()
        self.args = AutoCoderArgs()
        self.args.source_dir = self.temp_dir

    def teardown_method(self):
        """每个测试方法执行后的清理"""
        shutil.rmtree(self.temp_dir)

    def test_create_todo_list_with_task_tags(self):
        """测试使用 <task> 标签创建 todo 列表"""
        content = """<task>Analyze the existing codebase structure</task>
        <task>Design the new feature architecture</task>
        <task>Implement the core functionality</task>"""
        
        tool = TodoWriteTool(action="create", content=content, priority="high")
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is True
        assert "Created 3 new todo items" in result.content
        assert "Analyze the existing codebase structure" in result.content
        assert "Design the new feature architecture" in result.content
        assert "Implement the core functionality" in result.content

    def test_create_todo_list_traditional_format(self):
        """测试使用传统格式创建 todo 列表"""
        content = """1. 分析现有代码库结构
2. 设计新功能架构
3. 实现核心功能"""
        
        tool = TodoWriteTool(action="create", content=content, priority="medium")
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is True
        assert "Created 3 new todo items" in result.content
        assert "分析现有代码库结构" in result.content
        assert "设计新功能架构" in result.content
        assert "实现核心功能" in result.content

    def test_create_todo_list_mixed_format(self):
        """测试混合格式（包含 <task> 标签和其他内容）"""
        content = """这是一个项目任务列表：
        <task>设置开发环境</task>
        <task>创建项目骨架</task>
        其他说明文字
        <task>编写初始代码</task>"""
        
        tool = TodoWriteTool(action="create", content=content)
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is True
        assert "Created 3 new todo items" in result.content
        assert "设置开发环境" in result.content
        assert "创建项目骨架" in result.content
        assert "编写初始代码" in result.content

    def test_create_todo_list_empty_task_tags(self):
        """测试空的 <task> 标签"""
        content = """<task>有效任务</task>
        <task></task>
        <task>   </task>
        <task>另一个有效任务</task>"""
        
        tool = TodoWriteTool(action="create", content=content)
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is True
        assert "Created 2 new todo items" in result.content
        assert "有效任务" in result.content
        assert "另一个有效任务" in result.content

    def test_add_task_with_task_tag(self):
        """测试使用 <task> 标签添加单个任务"""
        # 首先创建基础列表
        initial_tool = TodoWriteTool(action="create", content="1. 初始任务")
        initial_resolver = TodoWriteToolResolver(agent=None, tool=initial_tool, args=self.args)
        initial_result = initial_resolver.resolve()
        assert initial_result.success is True
        
        # 添加新任务
        add_content = "<task>使用标签格式添加的新任务</task>"
        add_tool = TodoWriteTool(action="add_task", content=add_content, priority="high")
        add_resolver = TodoWriteToolResolver(agent=None, tool=add_tool, args=self.args)
        
        result = add_resolver.resolve()
        
        assert result.success is True
        assert "使用标签格式添加的新任务" in result.content

    def test_add_task_traditional_format(self):
        """测试使用传统格式添加单个任务"""
        # 首先创建基础列表
        initial_tool = TodoWriteTool(action="create", content="1. 初始任务")
        initial_resolver = TodoWriteToolResolver(agent=None, tool=initial_tool, args=self.args)
        initial_result = initial_resolver.resolve()
        assert initial_result.success is True
        
        # 添加新任务
        add_content = "传统格式添加的任务"
        add_tool = TodoWriteTool(action="add_task", content=add_content, priority="medium")
        add_resolver = TodoWriteToolResolver(agent=None, tool=add_tool, args=self.args)
        
        result = add_resolver.resolve()
        
        assert result.success is True
        assert "传统格式添加的任务" in result.content

    def test_add_task_multiple_task_tags_takes_first(self):
        """测试添加任务时包含多个 <task> 标签（只取第一个）"""
        # 首先创建基础列表
        initial_tool = TodoWriteTool(action="create", content="1. 初始任务")
        initial_resolver = TodoWriteToolResolver(agent=None, tool=initial_tool, args=self.args)
        initial_result = initial_resolver.resolve()
        assert initial_result.success is True
        
        # 添加新任务
        add_content = """<task>第一个任务</task>
        <task>第二个任务</task>
        <task>第三个任务</task>"""
        add_tool = TodoWriteTool(action="add_task", content=add_content)
        add_resolver = TodoWriteToolResolver(agent=None, tool=add_tool, args=self.args)
        
        result = add_resolver.resolve()
        
        assert result.success is True
        assert "第一个任务" in result.content
        assert "第二个任务" not in result.content
        assert "第三个任务" not in result.content

    def test_create_todo_list_no_content(self):
        """测试创建 todo 列表时没有内容"""
        tool = TodoWriteTool(action="create", content="")
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is False
        assert "Content is required" in result.message

    def test_add_task_no_content(self):
        """测试添加任务时没有内容"""
        tool = TodoWriteTool(action="add_task", content="")
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is False
        assert "Content is required" in result.message

    def test_multiline_task_content(self):
        """测试多行任务内容"""
        content = """<task>这是一个多行的任务
        包含详细的描述
        和具体的步骤</task>"""
        
        tool = TodoWriteTool(action="create", content=content)
        resolver = TodoWriteToolResolver(agent=None, tool=tool, args=self.args)
        
        result = resolver.resolve()
        
        assert result.success is True
        assert "这是一个多行的任务" in result.content

