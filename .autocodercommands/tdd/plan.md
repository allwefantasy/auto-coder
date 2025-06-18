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
- 基于OpenAI API的单元测试需求，设计具体的SDK架构和实现
- 明确HTTP客户端、认证机制、错误处理、重试逻辑等核心组件
- 考虑性能、并发安全、流式处理、扩展性等非功能性需求

**示例格式：**
```python
import os
import httpx
import asyncio
from typing import Dict, List, Optional, Union, Iterator, AsyncIterator
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import threading
import time
import json

# 核心异常类设计
class OpenAIError(Exception):
    """OpenAI SDK基础异常类"""
    pass

class AuthenticationError(OpenAIError):
    """认证错误"""
    pass

class APIConnectionError(OpenAIError):
    """API连接错误"""
    pass

class RateLimitError(OpenAIError):
    """速率限制错误"""
    pass

class BadRequestError(OpenAIError):
    """请求参数错误"""
    pass

# 数据模型设计
@dataclass
class Response:
    """API响应基础模型"""
    output_text: str
    model: str
    usage: Optional[Dict] = None
    
@dataclass
class Message:
    """聊天消息模型"""
    role: str
    content: str

@dataclass
class Choice:
    """聊天完成选择项"""
    message: Message
    index: int
    finish_reason: Optional[str] = None

@dataclass
class ChatCompletion:
    """聊天完成响应模型"""
    choices: List[Choice]
    model: str
    usage: Optional[Dict] = None

@dataclass
class StreamEvent:
    """流式响应事件模型"""
    data: str
    event_type: str = "data"

# HTTP客户端抽象层
class BaseHTTPClient(ABC):
    """HTTP客户端抽象基类"""
    
    @abstractmethod
    def post(self, url: str, headers: Dict, data: Dict) -> Dict:
        """发送POST请求"""
        pass
    
    @abstractmethod
    def post_stream(self, url: str, headers: Dict, data: Dict) -> Iterator[Dict]:
        """发送流式POST请求"""
        pass

class HTTPXClient(BaseHTTPClient):
    """基于HTTPX的HTTP客户端实现"""
    
    def __init__(self, timeout: int = 30, max_retries: int = 3):
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.Client(timeout=timeout)
        
    def post(self, url: str, headers: Dict, data: Dict) -> Dict:
        """发送POST请求并处理重试逻辑"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.post(url, headers=headers, json=data)
                self._handle_http_errors(response)
                return response.json()
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == self.max_retries - 1:
                    raise APIConnectionError(f"Connection failed after {self.max_retries} attempts: {e}")
                time.sleep(2 ** attempt)  # 指数退避
                
    def post_stream(self, url: str, headers: Dict, data: Dict) -> Iterator[Dict]:
        """发送流式POST请求"""
        try:
            with self.client.stream('POST', url, headers=headers, json=data) as response:
                self._handle_http_errors(response)
                for line in response.iter_lines():
                    if line.strip():
                        yield self._parse_sse_line(line)
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            raise APIConnectionError(f"Stream connection failed: {e}")
    
    def _handle_http_errors(self, response: httpx.Response):
        """处理HTTP错误状态码"""
        if response.status_code == 401:
            raise AuthenticationError("Invalid API key")
        elif response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")
        elif response.status_code == 400:
            raise BadRequestError("Invalid request parameters")
        elif response.status_code >= 500:
            raise APIConnectionError(f"Server error: {response.status_code}")
        elif response.status_code >= 400:
            raise OpenAIError(f"HTTP error: {response.status_code}")
    
    def _parse_sse_line(self, line: str) -> Dict:
        """解析Server-Sent Events格式的数据"""
        if line.startswith("data: "):
            data = line[6:]  # 去掉"data: "前缀
            if data.strip() == "[DONE]":
                return {"done": True}
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                return {"data": data}
        return {"raw": line}

# 核心OpenAI客户端设计
class OpenAI:
    """OpenAI SDK主客户端类"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.openai.com/v1",
                 http_client: Optional[BaseHTTPClient] = None):
        # 认证设置
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required")
        
        self.base_url = base_url
        self.http_client = http_client or HTTPXClient()
        
        # 创建各功能模块
        self.responses = ResponsesAPI(self)
        self.chat = ChatAPI(self)
        
        # 并发控制
        self._lock = threading.RLock()
        
    def _get_headers(self) -> Dict[str, str]:
        """获取通用请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "openai-python-sdk/1.0.0"
        }
    
    def _make_request(self, endpoint: str, data: Dict, stream: bool = False):
        """发送API请求的统一入口"""
        url = f"{self.base_url}/{endpoint}"
        headers = self._get_headers()
        
        # 参数验证
        self._validate_request_data(data)
        
        try:
            if stream:
                return self.http_client.post_stream(url, headers, data)
            else:
                return self.http_client.post(url, headers, data)
        except Exception as e:
            # 统一错误处理和日志记录
            self._log_error(endpoint, data, e)
            raise
    
    def _validate_request_data(self, data: Dict):
        """验证请求参数"""
        if not data.get("model"):
            raise ValueError("Model is required")
        
        if "input" in data and not data["input"]:
            raise ValueError("Input cannot be empty")
        
        if "messages" in data and not data["messages"]:
            raise ValueError("Messages cannot be empty")
    
    def _log_error(self, endpoint: str, data: Dict, error: Exception):
        """记录错误日志（简化版）"""
        # 实际实现中应该使用专业的日志库
        print(f"API Error - Endpoint: {endpoint}, Error: {error}")

# 响应API模块
class ResponsesAPI:
    """处理responses相关的API调用"""
    
    def __init__(self, client: OpenAI):
        self.client = client
    
    def create(self, model: str, input: Union[str, List[Dict]], 
               instructions: Optional[str] = None, stream: bool = False, **kwargs) -> Union[Response, Iterator[StreamEvent]]:
        """创建响应
        
        实现思路：
        1. 构建请求数据
        2. 处理多模态输入（文本+图像）
        3. 发送请求
        4. 解析响应并构建模型对象
        5. 处理流式响应
        """
        # 构建请求数据
        request_data = {
            "model": model,
            "input": input,
            "stream": stream,
            **kwargs
        }
        
        if instructions:
            request_data["instructions"] = instructions
        
        # 发送请求
        if stream:
            return self._create_stream_response(request_data)
        else:
            response_data = self.client._make_request("responses", request_data)
            return self._parse_response(response_data)
    
    def _create_stream_response(self, request_data: Dict) -> Iterator[StreamEvent]:
        """处理流式响应"""
        stream = self.client._make_request("responses", request_data, stream=True)
        for chunk in stream:
            if chunk.get("done"):
                break
            yield StreamEvent(
                data=chunk.get("data", ""),
                event_type=chunk.get("event", "data")
            )
    
    def _parse_response(self, response_data: Dict) -> Response:
        """解析普通响应"""
        return Response(
            output_text=response_data.get("output_text", ""),
            model=response_data.get("model", ""),
            usage=response_data.get("usage")
        )

# 聊天API模块
class ChatAPI:
    """处理chat相关的API调用"""
    
    def __init__(self, client: OpenAI):
        self.client = client
        self.completions = ChatCompletionsAPI(client)

class ChatCompletionsAPI:
    """处理chat.completions相关的API调用"""
    
    def __init__(self, client: OpenAI):
        self.client = client
    
    def create(self, model: str, messages: List[Dict], stream: bool = False, **kwargs) -> ChatCompletion:
        """创建聊天完成
        
        实现思路：
        1. 验证messages格式
        2. 构建请求数据
        3. 发送请求
        4. 解析响应并构建ChatCompletion对象
        """
        # 验证messages格式
        self._validate_messages(messages)
        
        # 构建请求数据
        request_data = {
            "model": model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        
        # 发送请求
        response_data = self.client._make_request("chat/completions", request_data)
        return self._parse_chat_completion(response_data)
    
    def _validate_messages(self, messages: List[Dict]):
        """验证消息格式"""
        for msg in messages:
            if "role" not in msg or "content" not in msg:
                raise ValueError("Each message must have 'role' and 'content' fields")
            if msg["role"] not in ["user", "assistant", "system", "developer"]:
                raise ValueError(f"Invalid role: {msg['role']}")
    
    def _parse_chat_completion(self, response_data: Dict) -> ChatCompletion:
        """解析聊天完成响应"""
        choices = []
        for choice_data in response_data.get("choices", []):
            message = Message(
                role=choice_data["message"]["role"],
                content=choice_data["message"]["content"]
            )
            choice = Choice(
                message=message,
                index=choice_data.get("index", 0),
                finish_reason=choice_data.get("finish_reason")
            )
            choices.append(choice)
        
        return ChatCompletion(
            choices=choices,
            model=response_data.get("model", ""),
            usage=response_data.get("usage")
        )

# 工厂模式 - 方便测试和扩展
class OpenAIClientFactory:
    """OpenAI客户端工厂类"""
    
    @staticmethod
    def create_client(api_key: Optional[str] = None, 
                     base_url: str = "https://api.openai.com/v1",
                     http_client: Optional[BaseHTTPClient] = None) -> OpenAI:
        """创建OpenAI客户端实例"""
        return OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=http_client
        )
    
    @staticmethod
    def create_test_client(mock_http_client: BaseHTTPClient) -> OpenAI:
        """创建用于测试的客户端实例"""
        return OpenAI(
            api_key="test-key",
            http_client=mock_http_client
        )

# 配置管理
@dataclass
class ClientConfig:
    """客户端配置类"""
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 30
    max_retries: int = 3
    enable_logging: bool = True
    
    @classmethod
    def from_env(cls) -> 'ClientConfig':
        """从环境变量加载配置"""
        return cls(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout=int(os.environ.get("OPENAI_TIMEOUT", "30")),
            max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "3")),
            enable_logging=os.environ.get("OPENAI_ENABLE_LOGGING", "true").lower() == "true"
        )
```

### 4. 分阶段实现计划

**要求：**
- 将OpenAI SDK实现分解为多个独立的开发阶段
- 每个阶段都有明确的目标和可测试的交付物
- 每个阶段内部可以进一步分解为具体的开发步骤

**示例格式：**

#### 阶段1：基础框架和异常处理（预计3小时）
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

#### 阶段2：HTTP客户端和网络层（预计4小时）
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

#### 阶段3：核心API功能实现（预计5小时）
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

#### 阶段4：流式处理和高级功能（预计3小时）
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

#### 阶段5：完善和优化（预计2小时）
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


