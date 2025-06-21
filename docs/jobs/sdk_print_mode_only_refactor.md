
# Auto-Coder SDK 重构：仅保留 Print Mode 模式

## 概述

本文档详细说明了对 `src/autocoder/sdk` 模块的重构计划，目标是简化 SDK 架构，仅保留 print_mode 作为默认模式，移除 session mode，同时继续支持 --continue 和 --resume 等参数以实现会话复用功能。

## 当前架构分析

### 现有模式

当前 SDK 支持两种运行模式：

1. **Print Mode** (`-p` 或 `--print`)：单次运行模式，执行一次查询后退出
2. **Session Mode**：多轮对话模式，支持交互式会话管理

### 现有会话参数

- `--continue` / `-c`：继续最近的对话
- `--resume SESSION_ID` / `-r`：恢复特定会话
- 会话管理通过 `SessionManager` 和 `Session` 类实现

### 问题分析

1. **复杂性过高**：两种模式增加了代码复杂性和维护成本
2. **功能重叠**：Print Mode 通过 --continue 和 --resume 已经可以实现会话复用
3. **用户困惑**：两种模式可能让用户不知道该选择哪种方式

## 重构目标

### 主要目标

1. **简化架构**：移除 Session Mode，仅保留 Print Mode 作为默认且唯一模式
2. **保持功能**：继续支持 --continue 和 --resume 参数实现会话复用
3. **向下兼容**：确保现有的 CLI 调用方式仍然有效
4. **代码清理**：移除不必要的会话管理代码

### 功能保留

- ✅ Print Mode 作为默认模式
- ✅ --continue 参数支持
- ✅ --resume SESSION_ID 参数支持  
- ✅ 所有其他 CLI 参数（--model, --max-turns, --verbose 等）
- ✅ Python API 接口
- ✅ 流式输出支持
- ✅ 终端渲染功能

### 功能移除

- ❌ Session Mode (`SessionModeHandler`)
- ❌ 交互式会话管理
- ❌ 复杂的会话持久化逻辑
- ❌ 会话导入/导出功能

## 详细修改计划

### 1. CLI 主入口修改 (`cli/main.py`)

#### 当前实现问题
```python
# 当前有两个互斥的模式选择
mode_group = parser.add_mutually_exclusive_group()
mode_group.add_argument("-p", "--print", dest="print_mode", action="store_true")
mode_group.add_argument("-c", "--continue", dest="continue_session", action="store_true")
mode_group.add_argument("-r", "--resume", dest="resume_session", metavar="SESSION_ID")
```

#### 修改方案
```python
# 移除模式选择，--continue 和 --resume 作为独立参数
parser.add_argument("-c", "--continue", dest="continue_session", action="store_true",
                   help="继续最近的对话")
parser.add_argument("-r", "--resume", dest="resume_session", metavar="SESSION_ID",
                   help="恢复特定会话")
```

#### 逻辑简化
```python
def run(self, options: CLIOptions, cwd: Optional[str] = None) -> CLIResult:
    """运行CLI命令 - 统一使用 Print Mode"""
    try:
        options.validate()
        # 移除模式判断，直接使用 PrintModeHandler
        return self.handle_print_mode(options, cwd)
    except Exception as e:
        return CLIResult(success=False, error=str(e))
```

### 2. CLI 选项修改 (`cli/options.py`)

#### 移除字段
```python
@dataclass
class CLIOptions:
    # 移除 print_mode 字段，因为现在只有一种模式
    # print_mode: bool = False  # 删除此行
    
    # 保留会话相关参数
    continue_session: bool = False
    resume_session: Optional[str] = None
    
    # 其他字段保持不变
    prompt: Optional[str] = None
    input_format: str = "text"
    output_format: str = "text"
    verbose: bool = False
    max_turns: int = 3
    system_prompt: Optional[str] = None
    allowed_tools: list = field(default_factory=list)
    permission_mode: str = "manual"
    model: Optional[str] = None
```

#### 验证逻辑更新
```python
def validate(self) -> None:
    """验证选项的有效性"""
    # 移除模式互斥验证，因为只有一种模式
    # 保留其他验证逻辑
    
    # 验证会话选项的互斥性
    if self.continue_session and self.resume_session:
        raise ValueError("continue_session和resume_session不能同时设置")
    
    # 其他验证保持不变...
```

### 3. 处理器重构 (`cli/handlers.py`)

#### 移除 SessionModeHandler
```python
# 删除整个 SessionModeHandler 类
# class SessionModeHandler(CommandHandler): # 删除此类
```

#### 增强 PrintModeHandler
```python
class PrintModeHandler(CommandHandler):
    """统一的命令处理器，支持单次运行和会话复用"""
    
    def handle(self) -> CLIResult:
        """处理命令，支持会话复用"""
        try:
            prompt = self._get_prompt()
            core_options = self._create_core_options()
            core = AutoCoderCore(core_options)

            # 根据会话参数构建完整的 prompt
            final_prompt = self._build_prompt_with_session_context(prompt)
            
            # 执行查询
            if self.options.output_format == "stream-json":
                result = asyncio.run(self._handle_stream(core, final_prompt))
            else:
                response = core.query_sync(final_prompt)
                result = self._format_response(response)
                
            return CLIResult(success=True, output=result)
            
        except Exception as e:
            return CLIResult(success=False, error=str(e))
    
    def _build_prompt_with_session_context(self, prompt: str) -> str:
        """根据会话参数构建完整的 prompt"""
        if self.options.continue_session:
            return f"/continue {prompt}" if prompt else "/continue"
        elif self.options.resume_session:
            return f"/resume {self.options.resume_session} {prompt}" if prompt else f"/resume {self.options.resume_session}"
        else:
            return f"/new {prompt}"
```

### 4. 核心模块调整 (`core/auto_coder_core.py`)

#### 移除会话管理器依赖
```python
class AutoCoderCore:
    """AutoCoder核心封装类 - 简化版"""
    
    def __init__(self, options: AutoCodeOptions):
        self.options = options
        cwd_str = str(options.cwd) if options.cwd is not None else os.getcwd()
        self.bridge = AutoCoderBridge(cwd_str, options)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._console = Console()
        self._accumulated_token_usage = {...}
    
    # 移除 get_session_manager 方法
    # def get_session_manager(self): # 删除此方法
    
    # 保留其他核心方法
    async def query_stream(self, prompt: str, show_terminal: bool = True) -> AsyncIterator[Message]:
        """异步流式查询"""
        # 实现保持不变
        
    def query_sync(self, prompt: str, show_terminal: bool = True) -> str:
        """同步查询"""
        # 实现保持不变
```

### 5. 会话模块简化

#### 保留基础会话类 (`session/session.py`)
```python
class Session:
    """简化的会话类，仅用于 Python API"""
    
    def __init__(self, session_id: str = None, options: AutoCodeOptions = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.options = options or AutoCodeOptions()
        self._core = AutoCoderCore(self.options)
    
    async def query(self, prompt: str) -> str:
        """异步查询 - 通过核心模块实现"""
        final_prompt = f"/id {self.session_id} {prompt}"
        return await self._core.query_sync(final_prompt)
    
    def query_sync(self, prompt: str) -> str:
        """同步查询 - 通过核心模块实现"""
        final_prompt = f"/id {self.session_id} {prompt}"
        return self._core.query_sync(final_prompt)
    
    def get_history(self) -> List[Message]:
        """获取对话历史 - 简化实现"""
        # 从底层系统获取历史记录
        return []
```

#### 简化会话管理器 (`session/session_manager.py`)
```python
class SessionManager:
    """简化的会话管理器"""
    
    def __init__(self, storage_path: str = None):
        self.storage_path = storage_path or os.getcwd()
    
    def create_session(self, options: AutoCodeOptions = None) -> Session:
        """创建新会话"""
        if options is None:
            options = AutoCodeOptions(cwd=self.storage_path)
        return Session(options=options)
    
    # 移除复杂的会话管理方法
    # def get_session(self, session_id: str) -> Session: # 删除
    # def get_latest_session(self) -> Optional[Session]: # 删除
    # def list_sessions(self) -> List[SessionInfo]: # 删除
    # 等等...
```

### 6. Python API 保持兼容 (`__init__.py`)

#### 保持现有 API 接口
```python
# 保持所有现有的公共 API
from .core import AutoCoderCore
from .models import AutoCodeOptions, Message
from .session import Session
from .exceptions import *

# 保持现有的便捷函数
def query_sync(prompt: str, options: AutoCodeOptions = None) -> str:
    """同步查询便捷函数"""
    if options is None:
        options = AutoCodeOptions()
    core = AutoCoderCore(options)
    return core.query_sync(f"/new {prompt}")

async def query(prompt: str, options: AutoCodeOptions = None) -> AsyncIterator[Message]:
    """异步查询便捷函数"""
    if options is None:
        options = AutoCodeOptions()
    core = AutoCoderCore(options)
    async for message in core.query_stream(f"/new {prompt}"):
        yield message
```

## 实现步骤

### 第一阶段：CLI 重构
1. 修改 `cli/main.py` 中的参数解析逻辑
2. 更新 `cli/options.py` 中的选项定义
3. 重构 `cli/handlers.py`，移除 SessionModeHandler
4. 增强 PrintModeHandler 以支持会话复用

### 第二阶段：核心模块清理
1. 简化 `core/auto_coder_core.py`
2. 移除不必要的会话管理依赖
3. 保持核心查询功能不变

### 第三阶段：会话模块简化
1. 简化 `session/session.py`
2. 精简 `session/session_manager.py`
3. 保持 Python API 兼容性

### 第四阶段：测试和验证
1. 验证所有 CLI 参数正常工作
2. 确保 --continue 和 --resume 功能正常
3. 验证 Python API 向下兼容
4. 更新文档和示例

## 兼容性考虑

### CLI 兼容性
```bash
# 这些调用方式将继续工作
auto-coder.run -p "Write a function" --model gpt-4
auto-coder.run --continue "继续修改"
auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000 "新的请求"

# 这些调用方式将不再工作（但可以提供友好的错误信息）
auto-coder.run  # 没有 -p 参数的会话模式
```

### Python API 兼容性
```python
# 这些 API 调用将继续工作
from autocoder.sdk import query_sync, query, Session, AutoCodeOptions

# 同步查询
response = query_sync("Write a function")

# 异步查询
async for message in query("Explain code"):
    print(message.content)

# 会话使用
session = Session()
response = session.query_sync("Hello")
```

## 风险评估

### 低风险
- CLI 参数重构：主要是移除互斥组，风险较低
- 核心查询功能：保持不变，风险很低
- Python API：保持兼容，风险很低

### 中等风险
- 会话管理简化：可能影响复杂的会话使用场景
- 处理器重构：需要仔细测试各种参数组合

### 缓解措施
1. 保持详细的测试覆盖
2. 提供清晰的迁移指南
3. 在重构过程中保持向下兼容
4. 分阶段实施，每个阶段充分测试

## 预期收益

### 代码简化
- 移除约 30% 的会话管理代码
- 简化 CLI 参数解析逻辑
- 减少维护复杂性

### 用户体验改善
- 统一的使用方式，减少学习成本
- 更清晰的参数语义
- 保持所有核心功能

### 维护性提升
- 更简单的代码结构
- 更少的边界情况
- 更容易添加新功能

## 总结

这次重构将显著简化 Auto-Coder SDK 的架构，同时保持所有核心功能和向下兼容性。通过移除冗余的 Session Mode，我们可以提供更清晰、更易用的接口，同时减少维护负担。

重构后的 SDK 将更加专注于其核心价值：提供简单、强大的 Auto-Coder 功能访问接口，无论是通过 CLI 还是 Python API。
