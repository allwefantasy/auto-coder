from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from prompt_toolkit.completion import Completer, Completion, NestedCompleter, PathCompleter, FuzzyCompleter
from prompt_toolkit.document import Document
import os
from collections import defaultdict
import re
from enum import Enum
import pydantic
from autocoder.index.symbols_utils import extract_symbols, SymbolType

class CompletionType(Enum):
    COMMAND = "command"
    FILE = "file"
    GROUP = "group" 
    SYMBOL = "symbol"
    TAG = "tag"
    SUB_COMMAND = "sub_command"

@dataclass
class CompletionContext:
    """上下文信息,用于补全时的动态数据"""
    current_files: List[str] = field(default_factory=list)
    project_root: str = ""
    all_files: List[str] = field(default_factory=list) 
    all_file_names: List[str] = field(default_factory=list)
    all_dir_names: List[str] = field(default_factory=list)
    symbols: List[Dict] = field(default_factory=list)
    groups: Dict[str, List[str]] = field(default_factory=dict)
    current_groups: List[str] = field(default_factory=list)

@dataclass 
class CompletionItem:
    """补全项"""
    text: str
    display: Optional[str] = None
    type: CompletionType = CompletionType.COMMAND
    start_position: int = 0

class Tag(pydantic.BaseModel):
    """标签解析结果"""
    start_tag: str
    content: str  
    end_tag: str

class CommandParser:
    """命令解析器,负责解析命令文本"""
    
    def __init__(self, text: str, command: str):
        self.text = text
        self.pos = -1
        self.len = len(text)
        self.command = command
        self.current_word_start = 0
        self.current_word_end = 0
        self.is_complete = False
        self.sub_commands: List[str] = []
        self.tags: List[Tag] = []
        
    def peek(self) -> Optional[str]:
        """查看下一个字符"""
        if self.pos + 1 < self.len:
            return self.text[self.pos + 1]
        return None
        
    def peek2(self) -> Optional[str]:
        """查看后两个字符"""
        if self.pos + 2 < self.len:
            return self.text[self.pos + 2]
        return None
        
    def next(self) -> Optional[str]:
        """移动到下一个字符"""
        if self.pos < self.len - 1:
            self.pos += 1
            return self.text[self.pos]
        return None
        
    def is_blank(self) -> bool:
        """判断是否是空白字符"""
        return self.peek() in {' ', '\t', '\n', '\r'}
        
    def consume_blanks(self):
        """跳过空白字符"""
        while self.peek() and self.is_blank():
            self.next()
            
    def current_word(self) -> str:
        """获取当前单词"""
        return self.text[self.current_word_start:self.current_word_end]
    
    def is_sub_command(self) -> bool:
        """判断是否是子命令"""
        backup = self.pos
        try:
            self.consume_blanks()
            if self.peek() == '/':
                cmd = ''
                while self.peek() and not self.is_blank():
                    cmd += self.next()
                return cmd.count('/') == 1
            return False
        finally:
            self.pos = backup
            
    def consume_sub_command(self) -> str:
        """消费一个子命令"""
        self.consume_blanks()
        self.current_word_start = self.pos + 1
        cmd = ''
        while self.peek() and not self.is_blank():
            cmd += self.next()
        self.current_word_end = self.pos + 1
        
        if not self.peek():
            self.is_complete = True
            
        if cmd:
            self.sub_commands.append(cmd)
            
        return cmd
    
    def is_start_tag(self) -> bool:
        """判断是否是开始标签"""
        backup = self.pos
        try:
            if self.peek() == '<' and self.peek2() != '/':
                while self.peek() and self.peek() != '>' and not self.is_blank():
                    self.next()
                return self.peek() == '>'
            return False
        finally:
            self.pos = backup
            
    def consume_tag(self):
        """消费一个标签"""
        # 解析开始标签
        start_tag = ''
        self.current_word_start = self.pos + 1
        while self.peek() and self.peek() != '>' and not self.is_blank():
            start_tag += self.next()
        if self.peek() == '>':
            start_tag += self.next()
        self.current_word_end = self.pos + 1
        
        # 解析内容
        content = ''
        self.current_word_start = self.pos + 1
        while self.peek() and not (self.peek() == '<' and self.peek2() == '/'):
            content += self.next()
        self.current_word_end = self.pos + 1
        
        # 解析结束标签
        end_tag = ''
        self.current_word_start = self.pos + 1
        if self.peek() == '<' and self.peek2() == '/':
            while self.peek() and self.peek() != '>' and not self.is_blank():
                end_tag += self.next()
            if self.peek() == '>':
                end_tag += self.next()
        self.current_word_end = self.pos + 1
        
        tag = Tag(start_tag=start_tag, content=content, end_tag=end_tag)
        self.tags.append(tag)
        
        if not self.peek():
            self.is_complete = True
            
    def consume_word(self):
        """消费普通单词"""
        word = ''
        self.current_word_start = self.pos + 1
        while self.peek() and not self.is_blank():
            word += self.next()
        self.current_word_end = self.pos + 1
        
        if not self.peek():
            self.is_complete = True
            
        return word

class SmartCommandCompleter(Completer):
    """智能命令补全器"""
    
    def __init__(self, context: CompletionContext):
        self.ctx = context
        self._command_map = self._build_command_map()
        
    def _build_command_map(self) -> Dict[str, Dict]:
        """构建命令映射"""
        return {
            "/add_files": {
                "/group": {
                    "/add": {},
                    "/drop": {},
                    "/reset": {},
                    "/set": {}
                },
                "/refresh": {}
            },
            "/remove_files": {},
            "/list_files": {},
            "/conf": {},
            "/coding": {
                "/apply": {},
                "/next": {}
            },
            "/chat": {
                "/new": {},
                "/save": {},
                "/copy": {},
                "/mcp": {},
                "/rag": {},
                "/review": {},
                "/no_context": {}
            },
            "/ask": {},
            "/commit": {},
            "/revert": {},
            "/index/query": {},
            "/index/build": {},
            "/exclude_dirs": {},
            "/help": {},
            "/shell": {},
            "/voice_input": {},
            "/exit": {},
            "/summon": {},
            "/mode": {},
            "/lib": {
                "/add": {},
                "/remove": {},
                "/list": {},
                "/set-proxy": {},
                "/refresh": {},
                "/get": {}
            },
            "/design": {
                "/svg": {},
                "/sd": {},
                "/logo": {}
            },
            "/mcp": {
                "/add": {},
                "/remove": {},
                "/list": {},
                "/list_running": {},
                "/refresh": {}
            },
            "/models": {
                "/add": {},
                "/add_model": {},
                "/remove": {},
                "/list": {},
                "/speed": {},
                "/speed-test": {},
                "/input_price": {},
                "/output_price": {}
            }
        }
        
    def get_completions(self, document: Document, complete_event):
        """获取补全建议"""
        text = document.text_before_cursor
        
        # 空输入时,补全所有主命令
        if not text.strip():
            for cmd in self._command_map:
                yield Completion(cmd, start_position=0)
            return
            
        # 解析命令
        for cmd in self._command_map:
            if text.startswith(cmd):
                parser = CommandParser(text[len(cmd):], cmd)
                yield from self._complete_command(parser)
                return
                
        # 补全主命令
        for cmd in self._command_map:
            if cmd.startswith(text):
                yield Completion(cmd, start_position=-len(text))
                
    def _complete_command(self, parser: CommandParser):
        """补全具体命令"""
        if parser.command == "/add_files":
            yield from self._complete_add_files(parser)
        elif parser.command == "/remove_files":    
            yield from self._complete_remove_files(parser)
        elif parser.command == "/coding":
            yield from self._complete_coding(parser)
        elif parser.command == "/chat":
            yield from self._complete_chat(parser)
        elif parser.command == "/lib":
            yield from self._complete_lib(parser)
        elif parser.command == "/mcp":
            yield from self._complete_mcp(parser)
        elif parser.command == "/models":
            yield from self._complete_models(parser)
        elif parser.command == "/conf":
            yield from self._complete_conf(parser)
            
    def _get_sub_commands(self, parser: CommandParser) -> List[str]:
        """获取可用的子命令"""
        current = self._command_map[parser.command]
        for cmd in parser.sub_commands[:-1]:
            if cmd in current:
                current = current[cmd]
        return list(current.keys())
        
    def _complete_add_files(self, parser: CommandParser):
        """补全 add_files 命令"""
        while not parser.is_complete:
            if parser.is_sub_command():
                cmd = parser.consume_sub_command()
                if parser.is_complete:
                    # 补全子命令
                    word = parser.current_word()
                    for sub_cmd in self._get_sub_commands(parser):
                        if sub_cmd.startswith(word):
                            yield CompletionItem(
                                text=sub_cmd,
                                type=CompletionType.SUB_COMMAND,
                                start_position=-len(word)
                            )
                    
                    # 补全组名
                    if parser.sub_commands and parser.sub_commands[-1] == "/group":
                        if "," in word:
                            word = word.split(",")[-1]
                        for group in self.ctx.groups:
                            if group.startswith(word):
                                yield CompletionItem(
                                    text=group,
                                    type=CompletionType.GROUP,
                                    start_position=-len(word)
                                )
            else:
                word = parser.consume_word()
                if parser.is_complete:
                    # 补全文件
                    if word.startswith("."):
                        for f in self.ctx.all_files:
                            rel_path = os.path.relpath(f, self.ctx.project_root)
                            if rel_path.startswith(word):
                                yield CompletionItem(
                                    text=rel_path,
                                    type=CompletionType.FILE,
                                    start_position=-len(word)
                                )
                    else:
                        # 匹配文件名
                        for name in self.ctx.all_file_names:
                            if name.startswith(word):
                                yield CompletionItem(
                                    text=name,
                                    type=CompletionType.FILE,
                                    start_position=-len(word)
                                )
                        # 匹配完整路径        
                        for f in self.ctx.all_files:
                            if word in f:
                                yield CompletionItem(
                                    text=f,
                                    type=CompletionType.FILE,
                                    start_position=-len(word)
                                )
                                
    def _complete_remove_files(self, parser: CommandParser):
        """补全 remove_files 命令"""
        while not parser.is_complete:
            word = parser.consume_word()
            if parser.is_complete:
                if not word:
                    # 补全 /all
                    yield CompletionItem(
                        text="/all",
                        type=CompletionType.SUB_COMMAND,
                        start_position=0
                    )
                    # 补全当前文件
                    for f in self.ctx.current_files:
                        yield CompletionItem(
                            text=f,
                            type=CompletionType.FILE,
                            start_position=0
                        )
                else:
                    # 补全 /all
                    if "/all".startswith(word):
                        yield CompletionItem(
                            text="/all",
                            type=CompletionType.SUB_COMMAND,
                            start_position=-len(word)
                        )
                    # 补全当前文件    
                    for f in self.ctx.current_files:
                        if word in f:
                            yield CompletionItem(
                                text=f,
                                type=CompletionType.FILE,
                                start_position=-len(word)
                            )
                            
    def _complete_coding(self, parser: CommandParser):
        """补全 coding 命令"""
        while not parser.is_complete:
            if parser.is_sub_command():
                cmd = parser.consume_sub_command()
                if parser.is_complete:
                    word = parser.current_word()
                    for sub_cmd in self._get_sub_commands(parser):
                        if sub_cmd.startswith(word):
                            yield CompletionItem(
                                text=sub_cmd,
                                type=CompletionType.SUB_COMMAND,
                                start_position=-len(word)
                            )
            elif parser.is_start_tag():
                parser.consume_tag()
                if parser.is_complete:
                    # 补全标签
                    tag = parser.tags[-1]
                    if tag.start_tag == "<img>" and not tag.end_tag:
                        # 补全图片路径
                        word = tag.content.strip()
                        parent = os.path.dirname(word)
                        basename = os.path.basename(word)
                        search_dir = parent if parent else "."
                        
                        for root, dirs, files in os.walk(search_dir):
                            if root != search_dir:
                                continue
                                
                            # 补全子目录    
                            for d in dirs:
                                full_path = os.path.join(root, d)
                                if full_path.startswith(word):
                                    rel_path = os.path.relpath(full_path, search_dir)
                                    yield CompletionItem(
                                        text=rel_path,
                                        type=CompletionType.FILE,
                                        start_position=-len(basename)
                                    )
                                    
                            # 补全图片文件        
                            for f in files:
                                if f.lower().endswith(('.png','.jpg','.jpeg','.gif')):
                                    if f.startswith(basename):
                                        full_path = os.path.join(root, f)
                                        rel_path = os.path.relpath(full_path, search_dir)
                                        yield CompletionItem(
                                            text=rel_path,
                                            type=CompletionType.FILE,
                                            start_position=-len(basename)
                                        )
            else:
                word = parser.consume_word()
                if parser.is_complete:
                    if word.startswith("@"):
                        # 补全文件引用
                        name = word[1:]
                        target_set: Set[str] = set()
                        
                        # 优先补全当前文件
                        for f in self.ctx.current_files:
                            base = os.path.basename(f)
                            if name in base:
                                target_set.add(base)
                                path_parts = f.split(os.sep)
                                display = os.sep.join(path_parts[-3:]) if len(path_parts) > 3 else f
                                rel_path = os.path.relpath(f, self.ctx.project_root)
                                yield CompletionItem(
                                    text=rel_path,
                                    display=f"{display} (in active files)",
                                    type=CompletionType.FILE,
                                    start_position=-len(name)
                                )
                                
                        # 补全其他文件        
                        for name in self.ctx.all_file_names:
                            if name.startswith(name) and name not in target_set:
                                target_set.add(name)
                                path_parts = name.split(os.sep)
                                display = os.sep.join(path_parts[-3:]) if len(path_parts) > 3 else name
                                yield CompletionItem(
                                    text=name,
                                    display=display,
                                    type=CompletionType.FILE,
                                    start_position=-len(name)
                                )
                                
                        for f in self.ctx.all_files:
                            if name in f and f not in target_set:
                                path_parts = f.split(os.sep)
                                display = os.sep.join(path_parts[-3:]) if len(path_parts) > 3 else f
                                rel_path = os.path.relpath(f, self.ctx.project_root)
                                yield CompletionItem(
                                    text=rel_path,
                                    display=display,
                                    type=CompletionType.FILE,
                                    start_position=-len(name)
                                )
                                
                    elif word.startswith("@@"):
                        # 补全符号引用
                        name = word[2:]
                        for symbol in self.ctx.symbols:
                            if name in symbol["symbol_name"]:
                                file_name = symbol["file_name"]
                                path_parts = file_name.split(os.sep)
                                display = os.sep.join(path_parts[-3:]) if len(path_parts) > 3 else symbol["symbol_name"]
                                rel_path = os.path.relpath(file_name, self.ctx.project_root)
                                yield CompletionItem(
                                    text=f"{symbol['symbol_name']}(location: {rel_path})",
                                    display=f"{symbol['symbol_name']} ({display}/{symbol['symbol_type']})",
                                    type=CompletionType.SYMBOL,
                                    start_position=-len(name)
                                )
                                
    def _complete_chat(self, parser: CommandParser):
        """补全 chat 命令"""
        while not parser.is_complete:
            if parser.is_sub_command():
                cmd = parser.consume_sub_command()
                if parser.is_complete:
                    word = parser.current_word()
                    for sub_cmd in self._get_sub_commands(parser):
                        if sub_cmd.startswith(word):
                            yield CompletionItem(
                                text=sub_cmd,
                                type=CompletionType.SUB_COMMAND,
                                start_position=-len(word)
                            )
            else:
                parser.consume_word()
                
    def _complete_lib(self, parser: CommandParser):
        """补全 lib 命令"""
        while not parser.is_complete:
            if parser.is_sub_command():
                cmd = parser.consume_sub_command()
                if parser.is_complete:
                    word = parser.current_word()
                    for sub_cmd in self._get_sub_commands(parser):
                        if sub_cmd.startswith(word):
                            yield CompletionItem(
                                text=sub_cmd,
                                type=CompletionType.SUB_COMMAND,
                                start_position=-len(word)
                            )
            else:
                parser.consume_word()
                
    def _complete_mcp(self, parser: CommandParser):
        """补全 mcp 命令"""
        while not parser.is_complete:
            if parser.is_sub_command():
                cmd = parser.consume_sub_command()
                if parser.is_complete:
                    word = parser.current_word()
                    for sub_cmd in self._get_sub_commands(parser):
                        if sub_cmd.startswith(word):
                            yield CompletionItem(
                                text=sub_cmd,
                                type=CompletionType.SUB_COMMAND,
                                start_position=-len(word)
                            )
            else:
                parser.consume_word()
                
    def _complete_models(self, parser: CommandParser):
        """补全 models 命令"""
        while not parser.is_complete:
            if parser.is_sub_command():
                cmd = parser.consume_sub_command()
                if parser.is_complete:
                    word = parser.current_word()
                    for sub_cmd in self._get_sub_commands(parser):
                        if sub_cmd.startswith(word):
                            yield CompletionItem(
                                text=sub_cmd,
                                type=CompletionType.SUB_COMMAND,
                                start_position=-len(word)
                            )
            else:
                parser.consume_word()
                
    def _complete_conf(self, parser: CommandParser):
        """补全 conf 命令"""
        while not parser.is_complete:
            word = parser.consume_word()
            if parser.is_complete:
                if not word:
                    # 补全 /drop
                    yield CompletionItem(
                        text="/drop",
                        type=CompletionType.SUB_COMMAND,
                        start_position=0
                    )
                else:
                    # 补全配置项
                    from autocoder.common import AutoCoderArgs
                    fields = AutoCoderArgs.model_fields.keys()
                    for field in fields:
                        if field.startswith(word):
                            yield CompletionItem(
                                text=f"{field}:",
                                type=CompletionType.COMMAND,
                                start_position=-len(word)
                            )