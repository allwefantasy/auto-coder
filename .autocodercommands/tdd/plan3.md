我想开发一个 Auto-Coder Code SDK, 放在 src/autocoder/sdk 目录下，支持如下使用命令行例子：

```python
# Run a single prompt and exit (print mode)
$ auto-coder.run -p "Write a function to calculate Fibonacci numbers"

# Using a pipe to provide stdin
$ echo "Explain this code" | auto-coder.run -p

# Output in JSON format with metadata
$ auto-coder.run -p "Generate a hello world function" --output-format json

# Stream JSON output as it arrives
$ auto-coder.run -p "Build a React component" --output-format stream-json


# Continue the most recent conversation
$ auto-coder.run --continue

# Continue and provide a new prompt
$ auto-coder.run --continue "Now refactor this for better performance"

# Resume a specific conversation by session ID
$ auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000

# Resume in print mode (non-interactive)
$ auto-coder.run -p --resume 550e8400-e29b-41d4-a716-446655440000 "Update the tests"

# Continue in print mode (non-interactive)
$ auto-coder.run -p --continue "Add error handling"

$ echo '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Explain this code"}]}}' | auto-coder.run -p --output-format=stream-json --input-format=stream-json --verbose

```

下面是在python代码中使用

```python
import anyio
from autocoder.sdk import query, AutoCodeOptions, Message

async def main():
    messages: list[Message] = []
    
    async for message in query(
        prompt="Write a haiku about foo.py",
        options=ClaudeCodeOptions(max_turns=3)
    ):
        messages.append(message)
    
    print(messages)

anyio.run(main)


from autocoder.sdk import query, AutoCodeOptions
from pathlib import Path

options = AutoCodeOptions(
    max_turns=3,
    system_prompt="You are a helpful assistant",
    cwd=Path("/path/to/project"),  # Can be string or Path
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode="acceptEdits"
)

async for message in query(prompt="Hello", options=options):
    print(message)
```

先做一个完整的需求设计，放在 docs/jobs/design.md 文件中。
design.md 文件必须包含以下四个部分，每个部分都要有详细的内容。

---

### 1. 接口使用说明

**设计要求：**
- 分析用户需求，提取核心功能点
- 设计简洁易用的API接口
- 提供完整的使用示例代码
- 展示用户最常见的使用场景

**设计思路：**
1. 理解用户要解决的核心问题
2. 设计符合用户心智模型的API
3. 优先考虑易用性和直观性
4. 提供清晰的使用示例

**输出格式：**
```python
# 导入和初始化示例
from your_package import YourMainClass

# 基础使用示例
client = YourMainClass(
    # 必要的配置参数
    config_param="value"
)

# 核心功能使用示例1
result1 = client.main_function(
    param1="value1",
    param2="value2"
)

# 核心功能使用示例2  
result2 = client.another_function(
    different_param="value"
)

# 高级功能使用示例
advanced_result = client.advanced_function(
    complex_param={
        "nested": "structure"
    },
    stream=True
)

# 处理结果的典型方式
for item in advanced_result:
    print(item)
```

---

### 2. 单元测试设计

**设计要求：**
- 基于第1部分的接口设计，为每个功能点设计测试用例
- 包含正常流程测试、异常情况测试、边界条件测试
- 使用Given-When-Then格式描述测试场景
- 合理使用mock避免外部依赖

**设计思路：**
1. 为每个公开接口设计对应的测试类
2. 覆盖所有可能的使用场景和错误情况
3. 测试用例要独立、可重复、快速执行
4. 重点测试接口行为而非实现细节

**输出格式：**
```python
import pytest
from unittest.mock import Mock, patch
from your_package import YourMainClass

class TestYourMainClass:
    
    @pytest.fixture
    def client(self):
        """测试客户端fixture
        Given: 需要一个配置好的客户端实例
        When: 使用有效配置创建客户端
        Then: 返回可用的客户端实例
        """
        return YourMainClass(config_param="test-value")
    
    def test_initialization_success(self):
        """测试成功初始化
        Given: 有效的配置参数
        When: 创建客户端实例
        Then: 客户端应该正确初始化，配置参数应该被设置
        """
        # 测试实现
    
    def test_main_function_success(self, client):
        """测试主要功能成功执行
        Given: 有效的客户端和正确的参数
        When: 调用主要功能方法
        Then: 应该返回预期的结果
        """
        # 测试实现
    
    def test_main_function_invalid_params(self, client):
        """测试无效参数处理
        Given: 有效的客户端但无效的参数
        When: 调用主要功能方法
        Then: 应该抛出参数验证错误
        """
        # 测试实现
    
    def test_error_handling(self, client):
        """测试错误处理
        Given: 模拟的错误条件
        When: 执行操作遇到错误
        Then: 应该抛出相应的异常类型
        """
        # 测试实现
    
    def test_edge_cases(self, client):
        """测试边界条件
        Given: 边界值输入
        When: 执行相关操作
        Then: 应该正确处理边界情况
        """
        # 测试实现
```

---

### 3. 业务代码实现设计

**设计要求：**
- 基于功能需求，设计清晰的模块划分和目录结构
- 明确各功能模块的职责分工和依赖关系
- 考虑代码的可维护性、可扩展性和测试友好性

**设计思路：**
1. 按功能职责划分模块，避免耦合
2. 设计清晰的目录结构，便于理解和维护
3. 明确模块间的依赖关系，避免循环依赖
4. 考虑未来扩展的可能性

**输出格式：**

**项目目录结构：**
```
your_package/
├── __init__.py                 # 包入口，导出主要接口
├── main_module.py              # 主要功能模块
├── config.py                   # 配置管理
├── exceptions.py               # 异常类定义
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── base.py                # 基础模型类
│   ├── request.py             # 请求模型
│   └── response.py            # 响应模型
├── core/                       # 核心功能模块
│   ├── __init__.py
│   ├── processor.py           # 核心处理逻辑
│   └── validator.py           # 数据验证
├── adapters/                   # 适配器层
│   ├── __init__.py
│   ├── external_api.py        # 外部API适配
│   └── storage.py             # 存储适配
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── helpers.py             # 辅助函数
│   └── constants.py           # 常量定义
└── tests/                      # 测试目录
    ├── __init__.py
    ├── conftest.py            # pytest配置
    ├── test_main.py           # 主要功能测试
    ├── test_models.py         # 模型测试
    └── test_core.py           # 核心功能测试
```

**核心模块划分：**

#### 1. 主要功能模块 (main_module.py)
**职责：**
- 提供对外的主要接口
- 协调各子模块的工作
- 处理用户输入和输出

#### 2. 异常处理模块 (exceptions.py)
**职责：**
- 定义所有自定义异常类
- 提供错误码和异常的映射关系
- 统一异常处理策略

#### 3. 数据模型模块 (models/)
**职责：**
- 定义数据结构和验证规则
- 提供数据序列化和反序列化方法
- 处理数据转换逻辑

#### 4. 核心功能模块 (core/)
**职责：**
- 实现核心业务逻辑
- 处理数据验证和转换
- 独立于外部依赖的纯业务逻辑

#### 5. 适配器模块 (adapters/)
**职责：**
- 处理外部系统集成
- 抽象外部依赖
- 提供统一的接口给核心模块

#### 6. 工具模块 (utils/)
**职责：**
- 提供通用的辅助函数
- 定义项目常量
- 处理通用的工具方法

#### 7. 配置模块 (config.py)
**职责：**
- 管理应用配置
- 支持环境变量和文件配置
- 提供配置验证功能

**模块依赖关系：**
```
main_module.py
├── core/ (核心功能)
│   ├── models/ (数据模型)
│   └── adapters/ (适配器)
├── config.py (配置)
├── exceptions.py (异常)
└── utils/ (工具函数)
```

---

### 4. 分阶段实现计划

**设计要求：**
- 将整个实现分解为多个独立的开发阶段
- 每个阶段都有明确的目标和可测试的交付物
- 每个阶段内部可以进一步分解为具体的开发步骤

**设计思路：**
1. 按依赖关系和重要性排序开发阶段
2. 每个阶段都要有可验证的输出
3. 优先实现核心功能，再完善周边特性
4. 确保每个阶段结束后系统仍然可用

**输出格式：**

以下以开发一个数据处理SDK为例，展示如何按阶段实现：

#### 阶段1：基础框架搭建
**目标：** 建立项目基础架构，完成YourMainClass的基本框架
**步骤：**
1. 创建项目目录结构（参考第3部分的目录结构）
2. 在`exceptions.py`中定义核心异常类：
   ```python
   class YourPackageError(Exception): pass
   class ValidationError(YourPackageError): pass
   class ProcessingError(YourPackageError): pass
   ```
3. 在`main_module.py`中创建YourMainClass的基本框架：
   ```python
   class YourMainClass:
       def __init__(self, config_param: str):
           self.config_param = config_param
       
       def main_function(self, param1: str, param2: str):
           # 框架代码，暂时返回None
           return None
       
       def another_function(self, different_param: str):
           # 框架代码，暂时返回None  
           return None
   ```
4. 在`config.py`中实现基础配置管理
5. 创建`tests/test_main.py`，编写基础初始化测试

**验收标准：**
- `from your_package import YourMainClass` 可以正常执行
- YourMainClass可以成功初始化
- 基础测试可以运行（即使功能未实现）
- 所有模块可以正常导入

#### 阶段2：核心功能实现
**目标：** 实现YourMainClass的主要功能接口
**步骤：**
1. 在`core/processor.py`中实现核心处理逻辑：
   ```python
   class DataProcessor:
       def process_data(self, data: dict) -> dict:
           # 实现具体的数据处理逻辑
           pass
   ```
2. 在`main_module.py`中实现main_function的具体逻辑：
   ```python
   def main_function(self, param1: str, param2: str):
       # 参数验证
       if not param1 or not param2:
           raise ValidationError("Parameters cannot be empty")
       
       # 调用核心处理逻辑
       processor = DataProcessor()
       result = processor.process_data({"p1": param1, "p2": param2})
       return result
   ```
3. 实现another_function的具体逻辑
4. 在`utils/validation.py`中添加参数验证工具
5. 编写对应的单元测试，确保基本功能可用

**验收标准：**
- YourMainClass的核心方法可以正常工作
- 参数验证正确，无效参数会抛出ValidationError
- 基本的使用场景测试通过
- 核心功能单元测试覆盖率达到80%以上

#### 阶段3：数据处理和模型完善
**目标：** 完善数据模型，增强YourMainClass的数据处理能力
**步骤：**
1. 在`models/request.py`中定义请求数据模型：
   ```python
   @dataclass
   class ProcessRequest:
       param1: str
       param2: str
       
       def validate(self):
           if not self.param1:
               raise ValidationError("param1 is required")
   ```
2. 在`models/response.py`中定义响应数据模型：
   ```python
   @dataclass  
   class ProcessResponse:
       result: dict
       status: str
       timestamp: datetime
   ```
3. 修改main_function使用数据模型：
   ```python
   def main_function(self, param1: str, param2: str) -> ProcessResponse:
       request = ProcessRequest(param1=param1, param2=param2)
       request.validate()
       
       result = self.processor.process_data(request)
       return ProcessResponse(
           result=result,
           status="success", 
           timestamp=datetime.now()
       )
   ```
4. 实现数据序列化和反序列化功能
5. 添加复杂数据结构处理能力
6. 编写数据模型相关测试

**验收标准：**
- 数据模型类型安全，验证规则完整
- YourMainClass返回结构化的响应对象
- 数据转换和序列化功能正常
- 边界条件和异常数据处理正确

#### 阶段4：外部集成和扩展功能
**目标：** 为YourMainClass添加高级功能和外部集成
**步骤：**
1. 在`adapters/external_api.py`中实现外部服务集成：
   ```python
   class ExternalAPIAdapter:
       def fetch_external_data(self, params: dict) -> dict:
           # 调用外部API获取数据
           pass
   ```
2. 为YourMainClass添加advanced_function：
   ```python
   def advanced_function(self, complex_param: dict, stream: bool = False):
       if stream:
           return self._process_stream(complex_param)
       else:
           return self._process_batch(complex_param)
   ```
3. 在`adapters/storage.py`中实现数据存储功能
4. 添加缓存机制提升性能
5. 实现流式处理功能（如果需要）
6. 编写集成测试和端到端测试

**验收标准：**
- YourMainClass的高级功能完整可用
- 外部API集成正常工作
- 流式处理功能稳定（如果有）
- 集成测试和端到端测试通过

#### 阶段5：优化和完善
**目标：** 优化YourMainClass性能，完善用户体验
**步骤：**
1. 性能分析和优化YourMainClass的关键方法
2. 在`utils/logging.py`中完善日志记录：
   ```python
   logger = logging.getLogger('your_package')
   
   def log_function_call(func_name: str, params: dict):
       logger.info(f"Calling {func_name} with params: {params}")
   ```
3. 为YourMainClass添加更多配置选项：
   ```python
   class YourMainClass:
       def __init__(self, config_param: str, timeout: int = 30, 
                    retry_count: int = 3, enable_cache: bool = True):
           # 支持更多配置选项
   ```
4. 完善错误处理和用户友好的错误信息
5. 编写完整的使用示例和最佳实践文档
6. 进行压力测试和性能测试

**验收标准：**
- YourMainClass性能满足预期要求
- 错误信息清晰友好，便于用户调试
- 配置选项丰富，支持不同使用场景
- 文档完整，用户可以快速上手
- 所有测试通过，代码质量达到发布标准

## 设计注意事项

1. **用户需求理解**：深入理解用户的真实需求，而不只是表面的功能要求
2. **接口设计优先**：优先设计好用户接口，再考虑内部实现
3. **测试驱动开发**：严格遵循TDD原则，先写测试再写实现
4. **模块化设计**：保持模块间的低耦合和高内聚
5. **通过用户接口测试来确保业务逻辑准确性**：严格通过对用户接口的测试来确认一个模块是正确实现。
