import os
import time
import aiofiles
import uvicorn
from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response
from fastapi import HTTPException
import mimetypes
from urllib.parse import unquote

from byzerllm.log import init_logger
from byzerllm.utils import random_uuid
from byzerllm.version import __version__ as version
from byzerllm.utils.client import ByzerLLM, LLMRequest
from byzerllm.utils.client.entrypoints.openai.serving_chat import OpenAIServingChat
from byzerllm.utils.client.entrypoints.openai.serving_completion import OpenAIServingCompletion
from byzerllm.utils.client.entrypoints.openai.protocol import (
    ModelList,
    ModelCard,
    ModelPermission,
    ChatCompletionRequest,
    ErrorResponse,
    CompletionRequest,
    EmbeddingCompletionRequest,
    EmbeddingResponse,
    EmbeddingResponseData,
    UsageInfo,
)
from pydantic import BaseModel
from typing import List,Optional

# If support dotenv, use it
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

logger = init_logger(__name__)

llm_client: ByzerLLM = None
openai_serving_chat: OpenAIServingChat = None
openai_serving_completion: OpenAIServingCompletion = None

TIMEOUT_KEEP_ALIVE = 5  # seconds
# timeout in 10 minutes. Streaming can take longer than 3 min
TIMEOUT = float(os.environ.get("BYZERLLM_APISERVER_HTTP_TIMEOUT", 600))

# Static file serving security settings

router_app = FastAPI()


@router_app.get("/health")
async def health() -> Response:
    """Health check."""
    return Response(status_code=200)


@router_app.get("/v1/models")
async def show_available_models():
    models = await openai_serving_chat.show_available_models()
    return JSONResponse(content=models.model_dump())


@router_app.get("/version")
async def show_version():
    return JSONResponse(content={"version": version})


@router_app.get("/v1/models", response_model=ModelList)
async def models() -> ModelList:
    """Show available models. Right now we only have one model."""
    model_cards = [
        ModelCard(
            id="",
            root="",
            permission=[ModelPermission()]
        )
    ]
    return ModelList(data=model_cards)


@router_app.post("/v1/completions")
async def create_completion(
        body: CompletionRequest,
        request: Request
):
    generator = await openai_serving_completion.create_completion(body, request)
    if isinstance(generator, ErrorResponse):
        return JSONResponse(
            content=generator.model_dump(),
            status_code=generator.code
        )
    if body.stream:
        return StreamingResponse(
            content=generator,
            media_type="text/event-stream"
        )
    else:
        return JSONResponse(content=generator.model_dump())


@router_app.post("/v1/chat/completions")
async def create_chat_completion(
        body: ChatCompletionRequest,
        request: Request,
):
    """Completion API similar to OpenAI's API.

    See  https://platform.openai.com/docs/api-reference/chat/create
    for the API specification. This API mimics the OpenAI ChatCompletion API.

    NOTE: Currently we do not support the following features:
        - function_call (Users should implement this by themselves)
        - logit_bias (to be supported by vLLM engine)
    """    
    generator = await openai_serving_chat.create_chat_completion(body, request)
    if isinstance(generator, ErrorResponse):
        return JSONResponse(
            content=generator.model_dump(),
            status_code=generator.code
        )
    if body.stream:
        return StreamingResponse(
            content=generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "X-Accel-Buffering": "no",
                "Transfer-Encoding": "chunked",
            }
        )
    else:
        return JSONResponse(content=generator.model_dump())


@router_app.post("/v1/embeddings")
async def embed(body: EmbeddingCompletionRequest):
    """Generate embeddings for given input text.
    
    Args:
        body: The embedding request containing input text and parameters.
        
    Returns:
        EmbeddingResponse with embeddings and usage statistics.
    """
    embedding_id = f"embed-{random_uuid()}"
    
    # Handle both string and list inputs
    inputs = body.input if isinstance(body.input, list) else [body.input]
    
    # Generate embeddings for each input
    results_list = []
    for text in inputs:
        result = llm_client.emb(body.model, request=LLMRequest(instruction=text))
        results_list.extend(result)

    # Build response data
    data = [
        EmbeddingResponseData(
            embedding=result.output,
            index=i,
            object="embedding"
        )
        for i, result in enumerate(results_list)
    ]
    
    # Calculate token usage (simplified)
    token_count = sum(len(str(input).split()) for input in inputs)
    
    return EmbeddingResponse(
        data=data,
        model=body.model,
        object="list",
        usage=UsageInfo(
            prompt_tokens=token_count,
            total_tokens=token_count
        ),
        created=int(time.time()),
        id=embedding_id
    )

@router_app.get("/static/{full_path:path}")
async def serve_static_file(full_path: str, request: Request):
    
    try:
        # 路径安全检查已经在中间件中完成
        # 直接使用规范化的路径
        file_path = os.path.join("/", os.path.normpath(unquote(full_path)))
        
        # 获取允许的静态文件目录
        allowed_static_abs = request.app.state.allowed_static_abs
        logger.info(f"==allowed_static_abs==: {allowed_static_abs}")
        
        if file_path.startswith(("/_images","_images")):            
            file_path = os.path.join(allowed_static_abs, file_path)  

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")          
        
        # 如果启用了Nginx X-Accel-Redirect，使用X-Accel特性
        if hasattr(request.app.state, "enable_nginx_x_accel") and request.app.state.enable_nginx_x_accel:
            # 获取文件的 MIME 类型
            content_type = mimetypes.guess_type(file_path)[0]
            if not content_type:
                content_type = "application/octet-stream"
                
            # 返回带X-Accel-Redirect头的响应
            # 通过添加X-Accel-Redirect头告诉Nginx直接提供该文件
            # 注意：Nginx配置必须正确设置内部路径映射
            response = Response(content="", media_type=content_type)
            response.headers["X-Accel-Redirect"] = f"/internal{file_path}"
            return response
            
        # 默认行为：异步读取文件内容
        async with aiofiles.open(file_path, "rb") as f:
            content = await f.read()
        
        # 获取文件的 MIME 类型
        content_type = mimetypes.guess_type(file_path)[0]
        if not content_type:
            content_type = "application/octet-stream"
            
        # 返回文件内容
        return Response(content=content, media_type=content_type)
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise HTTPException(status_code=404, detail=f"File not found: {str(e)}")
    except PermissionError as e:
        logger.error(f"Permission denied: {str(e)}")
        raise HTTPException(status_code=403, detail=f"Permission denied: {str(e)}")
    except Exception as e:
        logger.error(f"Error serving file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving file: {str(e)}")

class ServerArgs(BaseModel):
    host: str = None
    port: int = 8000
    workers: int = 4
    uvicorn_log_level: str = "info"
    allow_credentials: bool = False
    allowed_origins: List[str] = ["*"]  
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]
    api_key: str = None
    served_model_name: str = None
    prompt_template: str = None
    response_role: str = "assistant"
    ssl_keyfile: str = None
    ssl_certfile: str = None 
    doc_dir: str = ""  # Document directory path, also used as the root directory for serving static files
    tokenizer_path: Optional[str] = None
    max_static_path_length: int = int(os.environ.get("BYZERLLM_MAX_STATIC_PATH_LENGTH", 3000))  # Maximum length allowed for static file paths (larger value to better support Chinese characters)
    enable_nginx_x_accel: bool = False  # Enable Nginx X-Accel-Redirect for static file serving

def serve(llm:ByzerLLM, args: ServerArgs):
    
    logger.info(f"ByzerLLM API server version {version}")
    logger.info(f"args: {args}")

    # 设置静态文件路径长度限制
    max_path_length = args.max_static_path_length
    logger.info(f"Maximum static file path length: {max_path_length}")
    
    # 存储Nginx X-Accel设置到应用状态
    router_app.state.enable_nginx_x_accel = args.enable_nginx_x_accel
    if args.enable_nginx_x_accel:
        logger.info("Nginx X-Accel-Redirect enabled for static file serving")
    
    # 确定允许访问的静态文件目录
    # 优先级：1. 环境变量 BYZERLLM_ALLOWED_STATIC_DIR
    #        2. 命令行参数 doc_dir
    #        3. 默认值 "/tmp"
    allowed_static_dir = os.environ.get("BYZERLLM_ALLOWED_STATIC_DIR")
    if not allowed_static_dir and args.doc_dir:
        allowed_static_dir = args.doc_dir
    if not allowed_static_dir:
        allowed_static_dir = "/tmp"
    
    allowed_static_abs = os.path.abspath(allowed_static_dir)
    logger.info(f"Static files root directory: {allowed_static_abs}")
    
    # 将允许的静态文件目录存储到应用状态中
    router_app.state.allowed_static_abs = allowed_static_abs
    
    router_app.add_middleware(
        CORSMiddleware,
        allow_origins=args.allowed_origins,
        allow_credentials=args.allow_credentials,
        allow_methods=args.allowed_methods,
        allow_headers=args.allowed_headers,
    )
    
    # Add static file security middleware
    @router_app.middleware("http")
    async def static_file_security(request: Request, call_next):
        # Only apply to static routes
        if request.url.path.startswith("/static/"):
            # Extract the full_path from the URL
            path_parts = request.url.path.split("/static/", 1)
            if len(path_parts) > 1:
                full_path = path_parts[1]
                
                # Check path length
                if len(full_path) > max_path_length:
                    logger.warning(f"Path too long: {len(full_path)} > {max_path_length}")
                    return JSONResponse(
                        content={"error": "Path too long"},
                        status_code=401
                    )
                
                # Add warning when path length approaches the limit (80% of max)
                if len(full_path) > (max_path_length * 0.8):
                    logger.warning(f"Path length approaching limit: {len(full_path)} is {(len(full_path) / max_path_length * 100):.1f}% of max ({max_path_length})")
                
                # Decode and normalize path
                decoded_path = unquote(full_path)
                normalized_path = os.path.normpath(decoded_path)
                
                # Check if path is in allowed directory
                abs_path = os.path.abspath(os.path.join("/", normalized_path))
                if abs_path.startswith("/_images"):
                    return await call_next(request)
                
                # 使用预先计算好的allowed_static_abs
                is_allowed = abs_path.startswith(request.app.state.allowed_static_abs)
                
                if not is_allowed:
                    logger.warning(f"Unauthorized path access: {abs_path}")
                    return JSONResponse(
                        content={"error": "Unauthorized path"},
                        status_code=401
                    )
        
        return await call_next(request)
    
    if token := os.environ.get("BYZERLLM_API_KEY") or args.api_key:

        @router_app.middleware("http")
        async def authentication(request: Request, call_next):
            if not request.url.path.startswith("/v1"):
                return await call_next(request)
            if request.headers.get("Authorization") != "Bearer " + token:
                return JSONResponse(
                    content={"error": "Unauthorized"},
                    status_code=401
                )
            return await call_next(request)

    # Register labels for metrics
    # add_global_metrics_labels(model_name=engine_args.model)
    global llm_client
    llm_client = llm
    
    global openai_serving_chat
    openai_serving_chat = OpenAIServingChat(
        llm_client=llm_client,
        response_role=args.response_role,
        server_model_name=args.served_model_name,
        prompt_template=args.prompt_template
    )
    global openai_serving_completion
    openai_serving_completion = OpenAIServingCompletion(
        llm_client=llm_client,
        server_model_name=args.served_model_name,
        prompt_template=args.prompt_template
    )
    
    # Patch _check_model方法，使其永远返回None
    async def always_return_none(*args, **kwargs):
        return None
    
    openai_serving_chat._check_model = always_return_none
    openai_serving_completion._check_model = always_return_none

    # 如果使用workers>1或reload=True，必须使用导入字符串而不是应用实例    
    uvicorn.run(
        router_app,
        host=args.host,
        port=args.port,
        log_level=args.uvicorn_log_level,
        timeout_keep_alive=TIMEOUT_KEEP_ALIVE,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile                
    )
