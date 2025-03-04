import inspect

def stream_with_thinking(response):
    """
    Process an OpenAI streaming response that may contain regular content and reasoning_content.
    Returns a generator that yields the formatted output.
    
    Args:
        response: An OpenAI streaming response (generator)
        
    Yields:
        str: Formatted output with thinking sections marked
    """
    start_mark = "<thinking>\n"
    end_mark = "\n</thinking>\n"
    is_thinking = False  # 跟踪我们是否在输出思考内容
    
    for chunk in response:
        # 如果有常规内容
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
            # 如果我们之前在输出思考内容，需要先结束思考部分
            if is_thinking:
                yield end_mark
                is_thinking = False
            
            yield chunk.choices[0].delta.content
        
        # 如果有思考内容
        elif hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
            # 如果这是第一次输出思考内容，打印开始标记
            if not is_thinking:
                yield start_mark
                is_thinking = True
            
            yield chunk.choices[0].delta.reasoning_content
    
    # 确保思考内容结束后有结束标记
    if is_thinking:
        yield end_mark

async def stream_with_thinking_async(response):
    """
    Process an OpenAI async streaming response that may contain regular content and reasoning_content.
    Returns an async generator that yields the formatted output.
    
    Args:
        response: An OpenAI async streaming response
        
    Yields:
        str: Formatted output with thinking sections marked
    """
    start_mark = "<thinking>\n"
    end_mark = "\n</thinking>\n"
    is_thinking = False  # 跟踪我们是否在输出思考内容
    
    async for chunk in response:
        # 如果有常规内容
        if hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
            # 如果我们之前在输出思考内容，需要先结束思考部分
            if is_thinking:
                yield end_mark
                is_thinking = False
            
            yield chunk.choices[0].delta.content
        
        # 如果有思考内容
        elif hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
            # 如果这是第一次输出思考内容，打印开始标记
            if not is_thinking:
                yield start_mark
                is_thinking = True
            
            yield chunk.choices[0].delta.reasoning_content
    
    # 确保思考内容结束后有结束标记
    if is_thinking:
        yield end_mark

def process_streaming_response(response):
    """
    Process an OpenAI streaming response, detecting whether it's a regular or async generator.
    If using the async version, you must use this with await in an async context.
    
    Args:
        response: An OpenAI streaming response
        
    Returns:
        A generator or async generator that yields formatted output
    """
    if inspect.isasyncgen(response):
        return stream_with_thinking_async(response)
    else:
        return stream_with_thinking(response)

def print_streaming_response(response):
    """
    Print a streaming response with thinking sections clearly marked.
    
    Args:
        response: An OpenAI streaming response
    """
    for text in stream_with_thinking(response):
        print(text, end="", flush=True)

async def print_streaming_response_async(response):
    """
    Print an async streaming response with thinking sections clearly marked.
    
    Args:
        response: An OpenAI async streaming response
    """
    async for text in stream_with_thinking_async(response):
        print(text, end="", flush=True)

def separate_stream_thinking(response):
    """
    Process an OpenAI streaming response and return two separate generators:
    one for thinking content and one for normal content.
    
    Args:
        response: An OpenAI streaming response (generator)
        
    Returns:
        tuple: (thinking_generator, content_generator)
    """
    pending_content_chunk = None
    
    def thinking_generator():
        nonlocal pending_content_chunk
        
        for chunk in response:
            # If we have thinking content
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                yield chunk.choices[0].delta.reasoning_content
            # If we have regular content, store it but don't consume more than one chunk
            elif hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                pending_content_chunk = chunk
                break
    
    def content_generator():
        nonlocal pending_content_chunk
        
        # First yield any pending content chunk from the thinking generator
        if pending_content_chunk is not None:
            yield pending_content_chunk.choices[0].delta.content
            pending_content_chunk = None
        
        # Continue with the rest of the response
        for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    return thinking_generator(), content_generator()

async def separate_stream_thinking_async(response):
    """
    Process an OpenAI async streaming response and return two separate async generators:
    one for thinking content and one for normal content.
    
    Args:
        response: An OpenAI async streaming response
        
    Returns:
        tuple: (thinking_generator, content_generator)
    """
    pending_content_chunk = None
    
    async def thinking_generator():
        nonlocal pending_content_chunk
        
        async for chunk in response:
            # If we have thinking content
            if hasattr(chunk.choices[0].delta, 'reasoning_content') and chunk.choices[0].delta.reasoning_content:
                yield chunk.choices[0].delta.reasoning_content
            # If we have regular content, store it but don't consume more than one chunk
            elif hasattr(chunk.choices[0].delta, 'content') and chunk.choices[0].delta.content:
                pending_content_chunk = chunk
                break
    
    async def content_generator():
        nonlocal pending_content_chunk
        
        # First yield any pending content chunk from the thinking generator
        if pending_content_chunk is not None:
            yield pending_content_chunk.choices[0].delta.content
            pending_content_chunk = None
        
        # Continue with the rest of the response
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    return thinking_generator(), content_generator()