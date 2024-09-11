import argparse
from typing import Optional, List
import byzerllm
from autocoder.rag.api_server import serve, ServerArgs
from autocoder.rag.rag_entry import RAGFactory
from autocoder.rag.llm_wrapper import LLWrapper
from autocoder.common import AutoCoderArgs

def main(input_args: Optional[List[str]] = None):
    parser = argparse.ArgumentParser(description="Auto Coder RAG Server")
    parser.add_argument("--host", type=str, default=None, help="Host to bind the server")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server")
    parser.add_argument("--uvicorn-log-level", type=str, default="info", help="Uvicorn log level")
    parser.add_argument("--allow-credentials", action="store_true", help="Allow credentials")
    parser.add_argument("--allowed-origins", type=str, nargs="+", default=["*"], help="Allowed origins")
    parser.add_argument("--allowed-methods", type=str, nargs="+", default=["*"], help="Allowed methods")
    parser.add_argument("--allowed-headers", type=str, nargs="+", default=["*"], help="Allowed headers")
    parser.add_argument("--api-key", type=str, help="API key for authentication")
    parser.add_argument("--served-model-name", type=str, help="Name of the served model")
    parser.add_argument("--prompt-template", type=str, help="Prompt template")
    parser.add_argument("--response-role", type=str, default="assistant", help="Response role")
    parser.add_argument("--ssl-keyfile", type=str, help="SSL key file")
    parser.add_argument("--ssl-certfile", type=str, help="SSL certificate file")
    parser.add_argument("--doc-dir", type=str, default="", help="Document directory")
    parser.add_argument("--tokenizer-path", type=str, help="Tokenizer path")
    parser.add_argument("--model", type=str, required=True, help="Model name")
    parser.add_argument("--ray-address", type=str, default="auto", help="Ray address")
    parser.add_argument("--rag-type", type=str, default="simple", help="RAG type")
    
    args = parser.parse_args(input_args)
    
    server_args = ServerArgs(**vars(args))
    auto_coder_args = AutoCoderArgs(**vars(args))
    
    byzerllm.connect_cluster(address=args.ray_address)
    llm = byzerllm.ByzerLLM()
    llm.setup_default_model_name(args.model)
    
    if server_args.doc_dir:
        auto_coder_args.rag_type = "simple"
        rag = RAGFactory.get_rag(
            llm=llm,
            args=auto_coder_args,
            path=server_args.doc_dir,
            tokenizer_path=server_args.tokenizer_path,
        )
    else:
        rag = RAGFactory.get_rag(llm=llm, args=auto_coder_args, path="")

    llm_wrapper = LLWrapper(llm=llm, rag=rag)
    serve(llm=llm_wrapper, args=server_args)

if __name__ == "__main__":
    main()