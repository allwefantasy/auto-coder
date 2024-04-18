import argparse
import json
import os
import time

import ray
import uvicorn
from fastapi import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, Response

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
    Embeddings,
    EmbeddingsOutput,
    EmbeddingsData,
    EmbeddingsUsage,
)
import byzerllm

logger = init_logger(__name__)

llm_client: ByzerLLM = None
openai_serving_chat: OpenAIServingChat = None
openai_serving_completion: OpenAIServingCompletion = None

TIMEOUT_KEEP_ALIVE = 5  # seconds
# timeout in 10 minutes. Streaming can take longer than 3 min
TIMEOUT = float(os.environ.get("BYZERLLM_APISERVER_HTTP_TIMEOUT", 600))

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
    # async with async_timeout.timeout(TIMEOUT):

    generator = await openai_serving_chat.create_chat_completion(body, request)
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


@router_app.post("/v1/embeddings")
async def embed(body: Embeddings):
    """Given a prompt, the model will return one embedding.

    Returns:
        A response object with an embedding.
    """
    embedding_id = f"embed-{random_uuid()}"

    results_list = llm_client.emb(body.model, request=LLMRequest(instruction=body.input))
    tokens = 0

    return EmbeddingsOutput(
        data=[
            EmbeddingsData(
                embedding=results.output,
                index=i,
                object="embedding",
            )
            for i, results in enumerate(results_list)
        ],
        id=embedding_id,
        object="list",
        created=int(time.time()),
        model=body.model,
        usage=EmbeddingsUsage(
            prompt_tokens=tokens,
            total_tokens=tokens,
        ),
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="ByzerLLm OpenAI-Compatible RESTful API server.")
    parser.add_argument("--host", type=str, default=None, help="host name")
    parser.add_argument("--port", type=int, default=8000, help="port number")
    parser.add_argument(
        "--uvicorn-log-level",
        type=str,
        default="info",
        choices=['debug', 'info', 'warning', 'error', 'critical', 'trace'],
        help="log level for uvicorn")
    parser.add_argument("--allow-credentials",
                        action="store_true",
                        help="allow credentials")
    parser.add_argument("--allowed-origins",
                        type=json.loads,
                        default=["*"],
                        help="allowed origins")
    parser.add_argument("--allowed-methods",
                        type=json.loads,
                        default=["*"],
                        help="allowed methods")
    parser.add_argument("--allowed-headers",
                        type=json.loads,
                        default=["*"],
                        help="allowed headers")
    parser.add_argument("--api-key",
                        type=str,
                        default=None,
                        help="If provided, the server will require this key "
                             "to be presented in the header.")
    parser.add_argument("--served-model-name",
                        type=str,
                        default=None,
                        help="The model name used in the API. If not "
                             "specified, the model name will be the same as "
                             "the huggingface name.")
    parser.add_argument("--prompt-template",
                        type=str,
                        default=None,
                        help="The file path to the chat template, "
                             "or the template in single-line form "
                             "for the specified model")
    parser.add_argument("--response-role",
                        type=str,
                        default="assistant",
                        help="The role name to return if "
                             "`request.add_generation_prompt=true`.")
    parser.add_argument("--ssl-keyfile",
                        type=str,
                        default=None,
                        help="The file path to the SSL key file")
    parser.add_argument("--ssl-certfile",
                        type=str,
                        default=None,
                        help="The file path to the SSL cert file")

    return parser.parse_args()


def serve(llm:ByzerLLM):
    args = parse_args()

    logger.info(f"ByzerLLM API server version {version}")
    logger.info(f"args: {args}")

    router_app.add_middleware(
        CORSMiddleware,
        allow_origins=args.allowed_origins,
        allow_credentials=args.allow_credentials,
        allow_methods=args.allowed_methods,
        allow_headers=args.allowed_headers,
    )
    
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
    llm_client = llm

    openai_serving_chat = OpenAIServingChat(
        llm_client=llm_client,
        response_role=args.response_role,
        server_model_name=args.served_model_name,
        prompt_template=args.prompt_template
    )

    openai_serving_completion = OpenAIServingCompletion(
        llm_client=llm_client,
        server_model_name=args.served_model_name,
        prompt_template=args.prompt_template
    )

    uvicorn.run(
        router_app,
        host=args.host,
        port=args.port,
        log_level=args.uvicorn_log_level,
        timeout_keep_alive=TIMEOUT_KEEP_ALIVE,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile
    )
