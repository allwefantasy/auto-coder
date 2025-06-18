{{ query }}

先做一个完整的需求设计，放在 docs/jobs/design.md 文件中。
design.md 文件必须包含以下四个部分，每个部分都要有详细的内容：

### 1. 接口使用说明

**要求：**
比如用户想开发一个和大模型交互的SDK， 那么先设置这个SDK的使用范式。

**示例格式：**
```python
import os
from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ.get("OPENAI_API_KEY"),
)

response = client.responses.create(
    model="gpt-4o",
    instructions="You are a coding assistant that talks like a pirate.",
    input="How do I check if a Python object is an instance of a class?",
)

print(response.output_text)

completion = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "developer", "content": "Talk like a pirate."},
        {
            "role": "user",
            "content": "How do I check if a Python object is an instance of a class?",
        },
    ],
)

print(completion.choices[0].message.content)

prompt = "What is in this image?"
img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/2023_06_08_Raccoon1.jpg/1599px-2023_06_08_Raccoon1.jpg"

response = client.responses.create(
    model="gpt-4o-mini",
    input=[
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": prompt},
                {"type": "input_image", "image_url": f"{img_url}"},
            ],
        }
    ],
)

stream = client.responses.create(
    model="gpt-4o",
    input="Write a one-sentence bedtime story about a unicorn.",
    stream=True,
)

for event in stream:
    print(event)

```

### 2. 单元测试设计

**要求：**
- 基于第1部分的OpenAI Client接口和使用场景，设计完整的测试用例
- 包含正常流程测试、异常情况测试、边界条件测试
- 使用Given-When-Then格式描述测试场景
- 需要对网络请求进行mock，避免真实API调用

**示例格式：**
```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from openai import OpenAI
import os

class TestOpenAIClient:
    
    @pytest.fixture
    def client(self):
        """测试用的OpenAI客户端
        Given: 需要一个配置好的OpenAI客户端
        When: 使用环境变量中的API KEY创建客户端
        Then: 返回可用的客户端实例
        """
        return OpenAI(api_key="test-api-key")
    
    def test_client_initialization_with_api_key(self):
        """测试使用API Key初始化客户端
        Given: 有效的API Key
        When: 创建OpenAI客户端
        Then: 客户端应该正确初始化，api_key属性应该被设置
        """
        api_key = "test-api-key"
        client = OpenAI(api_key=api_key)
        assert client.api_key == api_key
    
    def test_client_initialization_from_env(self):
        """测试从环境变量初始化客户端
        Given: 环境变量中设置了OPENAI_API_KEY
        When: 不传递api_key参数创建客户端
        Then: 客户端应该使用环境变量中的API Key
        """
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env-api-key'}):
            client = OpenAI()
            assert client.api_key == 'env-api-key'
    
    @patch('openai.OpenAI.responses.create')
    def test_basic_response_creation_success(self, mock_create, client):
        """测试基本响应创建成功
        Given: 有效的客户端和mock的响应
        When: 调用responses.create方法
        Then: 应该返回包含output_text的响应对象
        """
        # 设置mock返回值
        mock_response = Mock()
        mock_response.output_text = "To check if a Python object is an instance of a class, use `isinstance(obj, ClassName)`"
        mock_create.return_value = mock_response
        
        response = client.responses.create(
            model="gpt-4o",
            instructions="You are a coding assistant that talks like a pirate.",
            input="How do I check if a Python object is an instance of a class?",
        )
        
        # 验证调用参数
        mock_create.assert_called_once_with(
            model="gpt-4o",
            instructions="You are a coding assistant that talks like a pirate.",
            input="How do I check if a Python object is an instance of a class?",
        )
        assert response.output_text is not None
        assert "isinstance" in response.output_text
    
    @patch('openai.OpenAI.chat.completions.create')
    def test_chat_completion_success(self, mock_create, client):
        """测试聊天完成功能成功
        Given: 有效的客户端和mock的聊天完成响应
        When: 调用chat.completions.create方法
        Then: 应该返回包含消息内容的响应对象
        """
        # 设置mock返回值
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Ahoy! To check if a Python object be an instance of a class, ye use `isinstance(obj, ClassName)`, matey!"
        mock_create.return_value = mock_response
        
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "developer", "content": "Talk like a pirate."},
                {
                    "role": "user",
                    "content": "How do I check if a Python object is an instance of a class?",
                },
            ],
        )
        
        # 验证调用和返回值
        mock_create.assert_called_once()
        assert completion.choices[0].message.content is not None
        assert "isinstance" in completion.choices[0].message.content
    
    @patch('openai.OpenAI.responses.create')
    def test_image_processing_success(self, mock_create, client):
        """测试图像处理功能成功
        Given: 有效的客户端和包含图像URL的输入
        When: 调用responses.create处理图像
        Then: 应该返回图像描述响应
        """
        # 设置mock返回值
        mock_response = Mock()
        mock_response.output_text = "This image shows a raccoon in a natural outdoor setting."
        mock_create.return_value = mock_response
        
        prompt = "What is in this image?"
        img_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d5/2023_06_08_Raccoon1.jpg/1599px-2023_06_08_Raccoon1.jpg"
        
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": f"{img_url}"},
                    ],
                }
            ],
        )
        
        # 验证调用参数包含图像URL
        call_args = mock_create.call_args
        assert call_args[1]['model'] == "gpt-4o-mini"
        assert img_url in str(call_args[1]['input'])
        assert response.output_text is not None
    
    @patch('openai.OpenAI.responses.create')
    def test_streaming_response_success(self, mock_create, client):
        """测试流式响应功能成功
        Given: 有效的客户端和流式响应mock
        When: 调用responses.create并设置stream=True
        Then: 应该返回可迭代的事件流
        """
        # 创建mock的流式响应
        mock_events = [
            Mock(data="Once"),
            Mock(data=" upon"),
            Mock(data=" a"),
            Mock(data=" time,"),
            Mock(data=" a"),
            Mock(data=" unicorn"),
            Mock(data=" danced"),
            Mock(data=" under"),
            Mock(data=" the"),
            Mock(data=" stars."),
        ]
        mock_create.return_value = iter(mock_events)
        
        stream = client.responses.create(
            model="gpt-4o",
            input="Write a one-sentence bedtime story about a unicorn.",
            stream=True,
        )
        
        # 验证流式响应
        events = list(stream)
        assert len(events) == 10
        mock_create.assert_called_once_with(
            model="gpt-4o",
            input="Write a one-sentence bedtime story about a unicorn.",
            stream=True,
        )
    
    def test_invalid_api_key_error(self):
        """测试无效API Key错误处理
        Given: 无效的API Key
        When: 尝试创建客户端并发起请求
        Then: 应该抛出认证错误
        """
        client = OpenAI(api_key="invalid-key")
        
        with patch('openai.OpenAI.responses.create') as mock_create:
            from openai import AuthenticationError
            mock_create.side_effect = AuthenticationError("Invalid API key")
            
            with pytest.raises(AuthenticationError):
                client.responses.create(
                    model="gpt-4o",
                    input="test input"
                )
    
    def test_network_error_handling(self, client):
        """测试网络错误处理
        Given: 网络连接问题
        When: 尝试发起API请求
        Then: 应该抛出连接错误
        """
        with patch('openai.OpenAI.responses.create') as mock_create:
            from openai import APIConnectionError
            mock_create.side_effect = APIConnectionError("Connection failed")
            
            with pytest.raises(APIConnectionError):
                client.responses.create(
                    model="gpt-4o",
                    input="test input"
                )
    
    def test_rate_limit_error_handling(self, client):
        """测试速率限制错误处理
        Given: API调用超过速率限制
        When: 尝试发起API请求
        Then: 应该抛出速率限制错误
        """
        with patch('openai.OpenAI.responses.create') as mock_create:
            from openai import RateLimitError
            mock_create.side_effect = RateLimitError("Rate limit exceeded")
            
            with pytest.raises(RateLimitError):
                client.responses.create(
                    model="gpt-4o",
                    input="test input"
                )
    
    def test_empty_input_validation(self, client):
        """测试空输入验证
        Given: 空的输入内容
        When: 尝试创建响应
        Then: 应该抛出验证错误或返回错误响应
        """
        with patch('openai.OpenAI.responses.create') as mock_create:
            mock_create.side_effect = ValueError("Input cannot be empty")
            
            with pytest.raises(ValueError):
                client.responses.create(
                    model="gpt-4o",
                    input=""
                )
    
    def test_invalid_model_error(self, client):
        """测试无效模型错误
        Given: 不存在的模型名称
        When: 尝试使用该模型创建响应
        Then: 应该抛出模型不存在错误
        """
        with patch('openai.OpenAI.responses.create') as mock_create:
            from openai import BadRequestError
            mock_create.side_effect = BadRequestError("Model not found")
            
            with pytest.raises(BadRequestError):
                client.responses.create(
                    model="non-existent-model",
                    input="test input"
                )
```

### 3. 业务代码实现设计

**要求：**
- 基于OpenAI API的功能需求，设计清晰的模块划分和目录结构
- 明确各功能模块的职责分工和依赖关系
- 考虑代码的可维护性、可扩展性和测试友好性

**项目目录结构：**
```
openai_sdk/
├── __init__.py                 # SDK入口，导出主要接口
├── client.py                   # OpenAI主客户端类
├── config.py                   # 配置管理
├── exceptions.py               # 异常类定义
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── base.py                # 基础模型类
│   ├── chat.py                # 聊天相关模型
│   ├── response.py            # 响应模型
│   └── stream.py              # 流式响应模型
├── api/                        # API接口模块
│   ├── __init__.py
│   ├── base.py                # API基类
│   ├── responses.py           # responses API
│   └── chat.py                # chat API
├── http/                       # HTTP客户端
│   ├── __init__.py
│   ├── base.py                # HTTP抽象基类
│   ├── httpx_client.py        # HTTPX实现
│   └── retry.py               # 重试逻辑
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── validation.py          # 参数验证
│   ├── logging.py             # 日志管理
│   └── auth.py                # 认证工具
└── tests/                      # 测试目录
    ├── __init__.py
    ├── conftest.py            # pytest配置
    ├── test_client.py         # 客户端测试
    ├── test_models.py         # 模型测试
    ├── test_api.py            # API测试
    └── test_http.py           # HTTP测试
```

**核心模块划分：**

#### 1. 客户端模块 (client.py)
**职责：**
- OpenAI主客户端类，统一入口
- 管理API Key和认证信息
- 初始化各功能模块实例
- 提供通用的请求处理方法

#### 2. 异常处理模块 (exceptions.py)
**职责：**
- 定义SDK所有异常类
- 异常类型：OpenAIError、AuthenticationError、APIConnectionError、RateLimitError、BadRequestError
- 提供错误码到异常的映射关系

#### 3. 数据模型模块 (models/)
**职责：**
- 定义API请求和响应的数据结构
- 包含：Response、Message、Choice、ChatCompletion、StreamEvent等
- 提供数据验证和序列化方法

#### 4. API接口模块 (api/)
**职责：**
- 封装具体的API调用逻辑
- ResponsesAPI：处理responses.create()
- ChatAPI：处理chat.completions.create()
- 负责请求参数构建和响应解析

#### 5. HTTP客户端模块 (http/)
**职责：**
- 抽象HTTP通信层
- BaseHTTPClient：定义HTTP接口规范
- HTTPXClient：具体HTTP实现
- 处理重试、超时、错误状态码映射

#### 6. 工具模块 (utils/)
**职责：**
- validation.py：参数验证工具
- logging.py：日志记录管理
- auth.py：认证相关工具函数

#### 7. 配置模块 (config.py)
**职责：**
- ClientConfig类：管理SDK配置
- 支持环境变量和代码配置
- 包含API Key、base_url、timeout等配置项

**模块依赖关系：**
```
client.py
├── api/ (API模块)
│   ├── models/ (数据模型)
│   └── http/ (HTTP客户端)
├── config.py (配置)
├── exceptions.py (异常)
└── utils/ (工具函数)
```

### 4. 分阶段实现计划

**要求：**
- 将OpenAI SDK实现分解为多个独立的开发阶段
- 每个阶段都有明确的目标和可测试的交付物
- 每个阶段内部可以进一步分解为具体的开发步骤

**示例格式：**

#### 阶段1：基础框架和异常处理
**目标：** 建立SDK的基础架构和异常处理体系
**步骤：**
1. 创建基础异常类（OpenAIError, AuthenticationError, APIConnectionError等）
2. 定义数据模型（Response, Message, Choice, ChatCompletion, StreamEvent）
3. 创建BaseHTTPClient抽象基类
4. 实现基础的OpenAI客户端框架（构造函数、认证逻辑）
5. 编写基础的单元测试框架
6. 实现配置管理（ClientConfig类）

**验收标准：**
- 所有异常类和数据模型可以正常导入
- OpenAI客户端可以成功初始化
- 基础测试框架可以运行
- API Key验证逻辑正常工作

#### 阶段2：HTTP客户端和网络层
**目标：** 实现HTTP通信和请求处理核心功能
**步骤：**
1. 实现HTTPXClient类（POST请求、流式请求）
2. 实现HTTP错误处理和状态码映射
3. 添加重试逻辑和指数退避算法
4. 实现Server-Sent Events (SSE) 数据解析
5. 编写HTTP客户端的单元测试
6. 添加请求和响应的日志记录

**验收标准：**
- HTTP客户端可以成功发送POST请求
- 错误处理机制正常工作（401, 429, 400, 500等）
- 重试逻辑在网络异常时正常触发
- 流式请求可以正确解析SSE数据
- 所有HTTP层面的测试通过

#### 阶段3：核心API功能实现
**目标：** 实现responses.create和chat.completions.create核心API功能
**步骤：**
1. 实现ResponsesAPI类和create方法
2. 实现ChatAPI和ChatCompletionsAPI类
3. 添加请求参数验证逻辑
4. 实现响应数据解析和模型构建
5. 支持多模态输入处理（文本+图像）
6. 编写API功能的单元测试
7. 确保所有正常流程测试通过

**验收标准：**
- client.responses.create() 功能完整
- client.chat.completions.create() 功能完整
- 多模态输入处理正常
- 参数验证和错误提示清晰
- 所有核心功能测试通过

#### 阶段4：流式处理和高级功能
**目标：** 实现流式响应和高级功能特性
**步骤：**
1. 完善流式响应处理逻辑
2. 实现流式事件的迭代器模式
3. 添加并发安全控制（threading.RLock）
4. 实现OpenAIClientFactory工厂类
5. 完善错误处理和异常边界情况
6. 编写流式处理和并发的单元测试

**验收标准：**
- 流式响应功能完整且稳定
- 并发访问时线程安全
- 工厂模式便于测试和扩展
- 所有边界条件测试通过
- 流式处理性能满足要求

#### 阶段5：完善和优化
**目标：** 完善SDK的健壮性和用户体验
**步骤：**
1. 完善日志记录和调试信息
2. 优化性能和内存使用
3. 添加更多的配置选项
4. 完善文档字符串和注释
5. 进行端到端测试
6. 代码审查和重构优化

**验收标准：**
- 所有功能测试和集成测试通过
- 性能指标满足预期要求
- 代码质量和可维护性良好
- 用户体验和错误提示友好
- 文档和注释完整清晰

## 开发注意事项

1. **测试驱动开发**：严格遵循TDD原则，先写测试再写实现
2. **Mock网络请求**：使用unittest.mock避免真实API调用
3. **异常处理优先**：每个阶段都要优先考虑错误处理
4. **向后兼容**：保证API接口的稳定性和向后兼容
5. **性能监控**：关注网络请求性能和内存使用
6. **安全考虑**：API Key不能出现在日志和错误信息中


