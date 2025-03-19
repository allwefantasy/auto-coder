from typing import Any, Dict, List, Optional, Union
import base64
import os
from enum import Enum
from pydantic import BaseModel, Field, validator


class ContentType(str, Enum):
    """Type of content in the OpenAI chat message."""
    TEXT = "text"
    IMAGE_URL = "image_url"


class ImageUrl(BaseModel):
    """Image URL structure in OpenAI chat messages."""
    url: str = Field(..., description="URL of the image, can be http(s) or data URI")

    @validator('url')
    def validate_url(cls, v):
        """Validate that URL is either an http(s) URL or a valid data URI."""
        if v.startswith(('http://', 'https://')):
            return v
        elif v.startswith('data:image/'):
            return v
        else:
            raise ValueError("Image URL must be http(s) or data URI format")


class TextContent(BaseModel):
    """Text content in OpenAI chat messages."""
    type: str = ContentType.TEXT
    text: str


class ImageUrlContent(BaseModel):
    """Image URL content in OpenAI chat messages."""
    type: str = ContentType.IMAGE_URL
    image_url: Union[str, ImageUrl]

    @validator('image_url')
    def validate_image_url(cls, v):
        """Convert string to ImageUrl if necessary."""
        if isinstance(v, str):
            return ImageUrl(url=v)
        return v


ContentItem = Union[TextContent, ImageUrlContent]


class OpenAIMessage(BaseModel):
    """Model for an OpenAI chat message."""
    role: str
    content: Union[str, List[ContentItem]]
    name: Optional[str] = None


class OpenAIConversation(BaseModel):
    """Model for a conversation with OpenAI."""
    messages: List[OpenAIMessage]


def is_structured_content(content: Any) -> bool:
    """
    Check if the content is structured (list of items with type field).
    
    Args:
        content: The content to check
        
    Returns:
        bool: True if the content is structured, False otherwise
    """
    if not isinstance(content, list):
        return False
    
    if not content:
        return False
    
    # Check if all items have a 'type' field
    return all(isinstance(item, dict) and 'type' in item for item in content)


def encode_image_to_base64(image_path: str) -> str:
    """
    Encode an image file to base64.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Base64-encoded image data
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Determine content type based on file extension
    file_ext = os.path.splitext(image_path)[1].lower()
    content_type = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
    }.get(file_ext, 'image/jpeg')
    
    return f"data:{content_type};base64,{encoded_string}"


def create_text_content(text: str) -> TextContent:
    """
    Create a text content item.
    
    Args:
        text: The text content
        
    Returns:
        TextContent: A text content item
    """
    return TextContent(text=text)


def create_image_content(image_path_or_url: str) -> ImageUrlContent:
    """
    Create an image content item from a file path or URL.
    
    Args:
        image_path_or_url: Path to the image file or an image URL
        
    Returns:
        ImageUrlContent: An image content item
    """
    # If it's a URL already, use it directly
    if image_path_or_url.startswith(('http://', 'https://', 'data:')):
        return ImageUrlContent(image_url=image_path_or_url)
    
    # Otherwise, treat it as a file path and encode it
    return ImageUrlContent(image_url=encode_image_to_base64(image_path_or_url))


def normalize_content(content: Any) -> Union[str, List[ContentItem]]:
    """
    Normalize content to either a string or a list of structured content items.
    
    Args:
        content: The content to normalize
        
    Returns:
        Union[str, List[ContentItem]]: Normalized content
    """
    if isinstance(content, str):
        return content
    
    if is_structured_content(content):
        normalized_items = []
        for item in content:
            if item['type'] == ContentType.TEXT:
                normalized_items.append(create_text_content(item['text']))
            elif item['type'] == ContentType.IMAGE_URL:
                normalized_items.append(ImageUrlContent(image_url=item['image_url']))
        return normalized_items
    
    # If it's neither a string nor structured content, convert to string
    return str(content)


def create_message(role: str, content: Union[str, List[ContentItem]], name: Optional[str] = None) -> OpenAIMessage:
    """
    Create an OpenAI chat message.
    
    Args:
        role: Role of the message sender (system, user, assistant)
        content: Content of the message (string or structured content)
        name: Optional name of the sender
        
    Returns:
        OpenAIMessage: An OpenAI chat message
    """
    return OpenAIMessage(
        role=role,
        content=normalize_content(content),
        name=name
    )


def process_conversations(conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    处理会话列表，确保每个消息都符合标准格式，并只保留文本内容。
    
    Args:
        conversations: 会话列表，可能包含各种格式的消息
        
    Returns:
        List[Dict[str, Any]]: 标准化后的会话列表，每个消息都有 role 和 content 字段
    
    例子:
        >>> conversations = [
        ...     {"role": "user", "content": "Hello"},
        ...     {"role": "assistant", "content": "Hi, how can I help?"},
        ...     {"role": "user", "content": [
        ...         {"type": "text", "text": "What's in this image?"},
        ...         {"type": "image_url", "image_url": "data:image/jpeg;base64,/9j/4AAQ..."}
        ...     ]}
        ... ]
        >>> processed = process_conversations(conversations)
        >>> # 结果保持相同的结构，但确保格式一致性

        输出格式要是这样的：
        [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi, how can I help?"},
            {"role": "user", "content": "What's in this image?"}         
        ]

        只保留 text 内容。如果有多个 text 内容，用换行符连接弄成一个。
        
    """
    processed_conversations = []
    
    for message in conversations:
        # 确保消息有 role 字段
        if "role" not in message:
            raise ValueError(f"Message missing 'role' field: {message}")
        
        role = message["role"]
        
        # 处理 content 字段，确保存在
        if "content" not in message:
            processed_content = ""  # 如果不存在，设置为空字符串
        else:
            content = message["content"]
            
            # 处理结构化内容
            if isinstance(content, list) and is_structured_content(content):
                # 提取所有文本内容并用换行符连接
                text_contents = []
                for item in content:
                    if item.get('type') == ContentType.TEXT and 'text' in item:
                        text_contents.append(item['text'])
                processed_content = '\n'.join(text_contents)
            else:
                # 如果是字符串或其他类型，确保转换为字符串
                processed_content = str(content) if content is not None else ""
        
        # 构建标准化的消息
        processed_message = {"role": role, "content": processed_content}
        
        # 如果原消息有 name 字段，也加入
        if "name" in message and message["name"]:
            processed_message["name"] = message["name"]
        
        processed_conversations.append(processed_message)
    
    return processed_conversations 