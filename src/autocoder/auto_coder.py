from autocoder.events.event_types import EventMetadata
import byzerllm
import yaml
import os
import time
from typing import List, Dict, Any, Optional
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher
from autocoder.common import git_utils, code_auto_execute
from autocoder.utils.llm_client_interceptors import token_counter_interceptor
from autocoder.db.store import Store
from autocoder.common.action_yml_file_manager import ActionYmlFileManager

from autocoder.utils.llms import get_llm_names

from byzerllm.utils.client import EventCallbackResult, EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText

from jinja2 import Template
import hashlib
from autocoder.utils.rest import HttpDoc
from byzerllm.apps.byzer_storage.env import get_latest_byzer_retrieval_lib
from autocoder.command_args import parse_args
from autocoder.rag.api_server import serve, ServerArgs
from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    StreamValue,
    DefaultValue,
    RequestOption,
)
from loguru import logger
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from autocoder.common.auto_coder_lang import get_message
from autocoder.common.memory_manager import save_to_memory_file
from autocoder import models as models_module
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from autocoder.privacy.model_filter import ModelPathFilter
from autocoder.common.result_manager import ResultManager
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.common.mcp_server import get_mcp_server
from autocoder.common.mcp_server_types import (
    McpRequest, McpInstallRequest, McpRemoveRequest, McpListRequest, 
    McpListRunningRequest, McpRefreshRequest
)
from autocoder.run_context import get_run_context,RunMode
console = Console()


def resolve_include_path(base_path, include_path):
    if include_path.startswith(".") or include_path.startswith(".."):
        full_base_path = os.path.abspath(base_path)
        parent_dir = os.path.dirname(full_base_path)
        return os.path.abspath(os.path.join(parent_dir, include_path))
    else:
        return include_path


def load_include_files(config, base_path, max_depth=10, current_depth=0):
    if current_depth >= max_depth:
        raise ValueError(
            f"Exceeded maximum include depth of {max_depth},you may have a circular dependency in your include files."
        )

    if "include_file" in config:
        include_files = config["include_file"]
        if not isinstance(include_files, list):
            include_files = [include_files]

        for include_file in include_files:
            abs_include_path = resolve_include_path(base_path, include_file)            
            with open(abs_include_path, "r",encoding="utf-8") as f:
                include_config = yaml.safe_load(f)
                if not include_config:
                    logger.info(
                        f"Include file {abs_include_path} is empty,skipping.")
                    continue
                config.update(
                    {
                        **load_include_files(
                            include_config,
                            abs_include_path,
                            max_depth,
                            current_depth + 1,
                        ),
                        **config,
                    }
                )

        del config["include_file"]

    return config


def main(input_args: Optional[List[str]] = None):
    args, raw_args = parse_args(input_args)
    args: AutoCoderArgs = args

    if args.file:
        with open(args.file, "r",encoding="utf-8") as f:
            config = yaml.safe_load(f)
            config = load_include_files(config, args.file)
            for key, value in config.items():
                if key != "file":  # 排除 --file 参数本身
                    # key: ENV {{VARIABLE_NAME}}
                    if isinstance(value, str) and value.startswith("ENV"):
                        template = Template(value.removeprefix("ENV").strip())
                        value = template.render(os.environ)
                    setattr(args, key, value)
    # if not args.request_id:
    #     args.request_id = str(uuid.uuid4())

    if raw_args.command == "revert":
        file_name = os.path.basename(args.file)
        action_file_manager = ActionYmlFileManager(source_dir=args.source_dir)
        revert_result = action_file_manager.revert_file(file_name)
        
        if revert_result:
            print(f"Successfully reverted changes for {args.file}")
        else:
            print(f"Failed to revert changes for {args.file}")
        return

    if not os.path.isabs(args.source_dir):
        args.source_dir = os.path.abspath(args.source_dir)

    # if not args.silence:
    #     print("Command Line Arguments:")
    #     print("-" * 50)
    #     for arg, value in vars(args).items():
    #         if arg == "context" and value:
    #             print(f"{arg:20}: {value[:30]}...")
    #         else:
    #             print(f"{arg:20}: {value}")
    #     print("-" * 50)

    # init store
    store = Store(os.path.join(args.source_dir, ".auto-coder", "metadata.db"))
    store.update_token_counter(os.path.basename(args.source_dir), 0, 0)

    if raw_args.command == "store":
        from autocoder.utils.print_table import print_table

        tc = store.get_token_counter()
        print_table([tc])
        return

    if raw_args.command == "init":
        if not args.project_type:
            logger.error(
                "Please specify the project type.The available project types are: py|ts| or any other file extension(for example: .java,.scala), you can specify multiple file extensions separated by commas."
            )
            return
        os.makedirs(os.path.join(args.source_dir, "actions"), exist_ok=True)
        os.makedirs(os.path.join(args.source_dir,
                    ".auto-coder"), exist_ok=True)

        from autocoder.common.command_templates import create_actions

        source_dir = os.path.abspath(args.source_dir)
        create_actions(
            source_dir=source_dir,
            params={"project_type": args.project_type,
                    "source_dir": source_dir},
        )
        git_utils.init(os.path.abspath(args.source_dir))

        with open(os.path.join(source_dir, ".gitignore"), "a") as f:
            f.write("\n.auto-coder/")
            f.write("\n/actions/")
            f.write("\n/output.txt")

        # 生成 .autocoderignore 文件，采用 .gitignore 格式
        autocoderignore_path = os.path.join(source_dir, ".autocoderignore")
        autocoderignore_content = "target\n"
        with open(autocoderignore_path, "w", encoding="utf-8") as f:
            f.write(autocoderignore_content)

        print(
            f"""Successfully initialized auto-coder project in {os.path.abspath(args.source_dir)}."""
        )
        return

    if raw_args.command == "screenshot":
        from autocoder.common.screenshots import gen_screenshots

        gen_screenshots(args.urls, args.output)
        print(
            f"Successfully captured screenshot of {args.urls} and saved to {args.output}"
        )
        return

    if raw_args.command == "next":
        # 使用 ActionYmlFileManager 创建下一个 action 文件
        action_manager = ActionYmlFileManager(args.source_dir)
        
        if raw_args.from_yaml:
            # 基于指定的 yaml 文件创建新文件
            new_file = action_manager.create_next_action_file(
                name=raw_args.name,
                from_yaml=raw_args.from_yaml
            )
            if not new_file:
                print(f"No YAML file found matching prefix: {raw_args.from_yaml}")
                return
        else:
            # 创建新的 action 文件
            new_file = action_manager.create_next_action_file(name=raw_args.name)
            if not new_file:
                print("Failed to create new action file")
                return
        
        # open_yaml_file_in_editor(new_file)
        return

    if args.model:
        if args.product_mode == "pro":
            home = os.path.expanduser("~")
            auto_coder_dir = os.path.join(home, ".auto-coder")
            libs_dir = os.path.join(auto_coder_dir, "storage", "libs")
            code_search_path = None
            if os.path.exists(libs_dir):
                latest_retrieval_lib_dir = get_latest_byzer_retrieval_lib(libs_dir)
                if latest_retrieval_lib_dir :
                    retrieval_libs_dir = os.path.join(
                        libs_dir, latest_retrieval_lib_dir
                    )
                    if os.path.exists(retrieval_libs_dir):
                        code_search_path = [retrieval_libs_dir]

            try:
                init_options = {}
                if raw_args.doc_command == "serve":
                    init_options["log_to_driver"] = True

                byzerllm.connect_cluster(
                    address=args.ray_address,
                    code_search_path=code_search_path,
                    init_options=init_options,
                )
            except Exception as e:
                logger.warning(
                    f"Detecting error when connecting to ray cluster: {e}, try to connect to ray cluster without storage support."
                )
                byzerllm.connect_cluster(address=args.ray_address)

            llm = byzerllm.ByzerLLM(verbose=args.print_request)                        
        
        if args.product_mode == "lite":
            default_model = args.model        
            model_info = models_module.get_model_by_name(default_model)                
            llm = byzerllm.SimpleByzerLLM(default_model_name=default_model)
            llm.deploy(
                model_path="",
                pretrained_model_type=model_info["model_type"],
                udf_name=args.model,
                infer_params={
                    "saas.base_url": model_info["base_url"],
                    "saas.api_key": model_info["api_key"],
                    "saas.model": model_info["model_name"],
                    "saas.is_reasoning": model_info["is_reasoning"],
                    "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                }
            )                                                    

        if args.product_mode == "lite":                                    
            # Set up default models based on configuration
            if args.code_model:
                if "," in args.code_model:
                    # Multiple code models specified
                    model_names = args.code_model.split(",")
                    models = []
                    for _, model_name in enumerate(model_names):
                        model_name = model_name.strip()
                        model_info = models_module.get_model_by_name(model_name)
                        code_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                        code_model.deploy(
                            model_path="",
                            pretrained_model_type=model_info["model_type"],
                            udf_name=model_name,
                            infer_params={
                                "saas.base_url": model_info["base_url"],
                                "saas.api_key": model_info["api_key"],
                                "saas.model": model_info["model_name"],
                                "saas.is_reasoning": model_info["is_reasoning"],
                                "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                            }
                        )
                        models.append(code_model)
                    llm.setup_sub_client("code_model", models)
                else:
                    # Single code model
                    model_info = models_module.get_model_by_name(args.code_model)
                    model_name = args.code_model
                    code_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                    code_model.deploy(
                        model_path="",
                        pretrained_model_type=model_info["model_type"],
                        udf_name=model_name,
                        infer_params={
                            "saas.base_url": model_info["base_url"],
                            "saas.api_key": model_info["api_key"],
                            "saas.model": model_info["model_name"],
                            "saas.is_reasoning": model_info["is_reasoning"],
                            "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                        }
                    )
                    llm.setup_sub_client("code_model", code_model)

            if args.generate_rerank_model:
                if "," in args.generate_rerank_model:
                    # Multiple rerank models specified
                    model_names = args.generate_rerank_model.split(",")
                    models = []
                    for _, model_name in enumerate(model_names):
                        model_info = models_module.get_model_by_name(model_name)                        
                        rerank_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                        rerank_model.deploy(
                            model_path="",
                            pretrained_model_type=model_info["model_type"],
                            udf_name=model_name,
                            infer_params={
                                "saas.base_url": model_info["base_url"],
                                "saas.api_key": model_info["api_key"],
                                "saas.model": model_info["model_name"],
                                "saas.is_reasoning": model_info["is_reasoning"],
                                "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                            }
                        )
                        models.append(rerank_model)
                    llm.setup_sub_client("generate_rerank_model", models)
                else:
                    # Single rerank model
                    model_info = models_module.get_model_by_name(args.generate_rerank_model)
                    model_name = args.generate_rerank_model
                    rerank_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                    rerank_model.deploy(
                        model_path="",
                        pretrained_model_type=model_info["model_type"],
                        udf_name=model_name,
                        infer_params={
                            "saas.base_url": model_info["base_url"],
                            "saas.api_key": model_info["api_key"],
                            "saas.model": model_info["model_name"],
                            "saas.is_reasoning": model_info["is_reasoning"],
                            "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                        }
                    )
                    llm.setup_sub_client("generate_rerank_model", rerank_model)
            
            if args.inference_model:
                model_info = models_module.get_model_by_name(args.inference_model)
                model_name = args.inference_model
                inference_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                inference_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("inference_model", inference_model)                 

            if args.index_filter_model:
                model_name = args.index_filter_model.strip()
                model_info = models_module.get_model_by_name(model_name)                
                index_filter_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                index_filter_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("index_filter_model", index_filter_model)            

            if args.context_prune_model:
                model_name = args.context_prune_model.strip()
                model_info = models_module.get_model_by_name(model_name)                
                context_prune_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                context_prune_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("context_prune_model", context_prune_model)

            if args.conversation_prune_model:
                model_name = args.conversation_prune_model.strip()
                model_info = models_module.get_model_by_name(model_name)                
                conversation_prune_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                conversation_prune_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("conversation_prune_model", conversation_prune_model)

        if args.product_mode == "pro":
            if args.code_model:
                if "," in args.code_model:
                    # Multiple code models specified
                    model_names = args.code_model.split(",")
                    models = []
                    for _, model_name in enumerate(model_names):
                        code_model = byzerllm.ByzerLLM()
                        code_model.setup_default_model_name(model_name.strip())
                        models.append(code_model)
                    llm.setup_sub_client("code_model", models)
                else:
                    # Single code model
                    code_model = byzerllm.ByzerLLM()
                    code_model.setup_default_model_name(args.code_model)
                    llm.setup_sub_client("code_model", code_model)

            if args.generate_rerank_model:
                if "," in args.generate_rerank_model:
                    # Multiple rerank models specified
                    model_names = args.generate_rerank_model.split(",")
                    models = []
                    for _, model_name in enumerate(model_names):
                        rerank_model = byzerllm.ByzerLLM()
                        rerank_model.setup_default_model_name(model_name.strip())
                        models.append(rerank_model)
                    llm.setup_sub_client("generate_rerank_model", models)
                else:
                    # Single rerank model
                    rerank_model = byzerllm.ByzerLLM()
                    rerank_model.setup_default_model_name(args.generate_rerank_model)
                    llm.setup_sub_client("generate_rerank_model", rerank_model)

            if args.inference_model:
                inference_model = byzerllm.ByzerLLM()
                inference_model.setup_default_model_name(args.inference_model)
                llm.setup_sub_client("inference_model", inference_model)   

            if args.index_filter_model:
                index_filter_model = byzerllm.ByzerLLM()
                index_filter_model.setup_default_model_name(args.index_filter_model)
                llm.setup_sub_client("index_filter_model", index_filter_model)
            
            if args.context_prune_model:
                context_prune_model = byzerllm.ByzerLLM()
                context_prune_model.setup_default_model_name(args.context_prune_model)
                llm.setup_sub_client("context_prune_model", context_prune_model)

            if args.conversation_prune_model:
                conversation_prune_model = byzerllm.ByzerLLM()
                conversation_prune_model.setup_default_model_name(args.conversation_prune_model)
                llm.setup_sub_client("conversation_prune_model", conversation_prune_model)

        if get_run_context().mode != RunMode.WEB and args.human_as_model:

            def intercept_callback(
                llm, model: str, input_value: List[Dict[str, Any]]
            ) -> EventCallbackResult:
                if (
                    input_value[0].get("embedding", False)
                    or input_value[0].get("tokenizer", False)
                    or input_value[0].get("apply_chat_template", False)
                    or input_value[0].get("meta", False)
                ):
                    return True, None
                if not input_value[0].pop("human_as_model", None):
                    return True, None

                console = Console()
                console.print(
                    Panel(
                        f"Intercepted request to model: [bold]{model}[/bold]",
                        border_style="yellow",
                    )
                )
                instruction = input_value[0]["instruction"]
                final_ins = instruction
                
                with open(args.target_file, "w",encoding="utf-8") as f:
                    f.write(final_ins)

                try:
                    import pyperclip

                    pyperclip.copy(final_ins)
                    console.print(
                        Panel(
                            get_message("human_as_model_instructions"),
                            title="Instructions",
                            border_style="blue",
                            expand=False,
                        )
                    )
                except Exception:
                    logger.warning(get_message("clipboard_not_supported"))
                    console.print(
                        Panel(
                            get_message(
                                "human_as_model_instructions_no_clipboard"),
                            title="Instructions",
                            border_style="blue",
                            expand=False,
                        )
                    )                

                lines = []
                while True:
                    line = prompt(FormattedText(
                        [("#00FF00", "> ")]), multiline=False)
                    line_lower = line.strip().lower()
                    if line_lower in ["eof", "/eof"]:
                        break
                    elif line_lower in ["/clear"]:
                        lines = []
                        print("\033[2J\033[H")  # Clear terminal screen
                        continue
                    elif line_lower in ["/break"]:
                        raise Exception(
                            "User requested to break the operation.")
                    lines.append(line)

                result = "\n".join(lines)

                if result.lower() == "c":
                    return True, None
                else:
                    v = [
                        {
                            "predict": result,
                            "input": input_value[0]["instruction"],
                            "metadata": {},
                        }
                    ]
                    return False, v

            llm.add_event_callback(
                EventName.BEFORE_CALL_MODEL, intercept_callback)
            
            code_models = llm.get_sub_client("code_model")
            if code_models:
                if not isinstance(code_models, list):
                    code_models = [code_models]
                for model in code_models:
                    model.add_event_callback(
                        EventName.BEFORE_CALL_MODEL, intercept_callback
                    )
        # llm.add_event_callback(EventName.AFTER_CALL_MODEL, token_counter_interceptor)
        
        code_models = llm.get_sub_client("code_model")
        if code_models:
            if not isinstance(code_models, list):
                code_models = [code_models]
            for model in code_models:
                model.add_event_callback(
                    EventName.AFTER_CALL_MODEL, token_counter_interceptor
                )
        if args.product_mode == "lite":             
            if args.chat_model:
                model_name = args.chat_model.strip()
                model_info = models_module.get_model_by_name(model_name)                
                chat_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                chat_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("chat_model", chat_model)
            
            if args.vl_model:   
                model_name = args.vl_model.strip()
                model_info = models_module.get_model_by_name(model_name)                
                vl_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                vl_model.deploy(
                    model_path="",
                    pretrained_model_type="saas/openai",
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("vl_model", vl_model)

            if args.index_model:   
                model_name = args.index_model.strip()
                model_info = models_module.get_model_by_name(model_name)                
                index_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                index_model.deploy(
                    model_path="",
                    pretrained_model_type="saas/openai",
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("index_model", index_model)    

            if args.sd_model:
                model_name = args.sd_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                sd_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                sd_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("sd_model", sd_model)

            if args.text2voice_model:
                model_name = args.text2voice_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                text2voice_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                text2voice_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("text2voice_model", text2voice_model)

            if args.voice2text_model:
                model_name = args.voice2text_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                voice2text_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                voice2text_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("voice2text_model", voice2text_model)

            if args.planner_model:
                model_name = args.planner_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                planner_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                planner_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("planner_model", planner_model)

            if args.commit_model:
                model_name = args.commit_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                commit_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                commit_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("commit_model", commit_model)    

            if args.designer_model:
                model_name = args.designer_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                designer_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                designer_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("designer_model", designer_model)

            if args.emb_model:
                model_name = args.emb_model.strip()
                model_info = models_module.get_model_by_name(model_name)
                emb_model = byzerllm.SimpleByzerLLM(default_model_name=model_name)
                emb_model.deploy(
                    model_path="",
                    pretrained_model_type=model_info["model_type"],
                    udf_name=model_name,
                    infer_params={
                        "saas.base_url": model_info["base_url"],
                        "saas.api_key": model_info["api_key"],
                        "saas.model": model_info["model_name"],
                        "saas.is_reasoning": model_info["is_reasoning"],
                        "saas.max_output_tokens": model_info.get("max_output_tokens", 8096)
                    }
                )
                llm.setup_sub_client("emb_model", emb_model)
        
        if args.product_mode == "pro":
            llm.setup_template(model=args.model, template="auto")
            llm.setup_default_model_name(args.model)

            llm.setup_max_output_length(args.model, args.model_max_length)
            llm.setup_max_input_length(args.model, args.model_max_input_length)
            llm.setup_extra_generation_params(
                args.model, {"max_length": args.model_max_length}
            )

            if args.chat_model:
                chat_model = byzerllm.ByzerLLM()
                chat_model.setup_default_model_name(args.chat_model)
                llm.setup_sub_client("chat_model", chat_model)

            if args.vl_model:
                vl_model = byzerllm.ByzerLLM()
                vl_model.setup_default_model_name(args.vl_model)
                vl_model.setup_template(model=args.vl_model, template="auto")
                llm.setup_sub_client("vl_model", vl_model)

            if args.sd_model:
                sd_model = byzerllm.ByzerLLM()
                sd_model.setup_default_model_name(args.sd_model)
                sd_model.setup_template(model=args.sd_model, template="auto")
                llm.setup_sub_client("sd_model", sd_model)

            if args.text2voice_model:
                text2voice_model = byzerllm.ByzerLLM()
                text2voice_model.setup_default_model_name(args.text2voice_model)
                text2voice_model.setup_template(
                    model=args.text2voice_model, template="auto"
                )
                llm.setup_sub_client("text2voice_model", text2voice_model)

            if args.voice2text_model:
                voice2text_model = byzerllm.ByzerLLM()
                voice2text_model.setup_default_model_name(args.voice2text_model)
                voice2text_model.setup_template(
                    model=args.voice2text_model, template="auto"
                )
                llm.setup_sub_client("voice2text_model", voice2text_model)

            if args.index_model:
                index_model = byzerllm.ByzerLLM()
                index_model.setup_default_model_name(args.index_model)
                index_model.setup_max_output_length(
                    args.index_model, args.index_model_max_length or args.model_max_length
                )
                index_model.setup_max_input_length(
                    args.index_model,
                    args.index_model_max_input_length or args.model_max_input_length,
                )
                index_model.setup_extra_generation_params(
                    args.index_model,
                    {"max_length": args.index_model_max_length or args.model_max_length},
                )
                llm.setup_sub_client("index_model", index_model)

            if args.emb_model:
                llm.setup_default_emb_model_name(args.emb_model)
                emb_model = byzerllm.ByzerLLM()
                emb_model.setup_default_emb_model_name(args.emb_model)
                # emb_model.setup_template(model=args.emb_model, template="auto")
                llm.setup_sub_client("emb_model", emb_model)

            if args.planner_model:
                planner_model = byzerllm.ByzerLLM()
                planner_model.setup_default_model_name(args.planner_model)
                llm.setup_sub_client("planner_model", planner_model)

            if args.designer_model:
                designer_model = byzerllm.ByzerLLM()
                designer_model.setup_default_model_name(args.designer_model)
                llm.setup_sub_client("designer_model", designer_model)

            if args.commit_model:
                commit_model = byzerllm.ByzerLLM()
                commit_model.setup_default_model_name(args.commit_model)
                llm.setup_sub_client("commit_model", commit_model)

    else:
        llm = None

    # Add query prefix and suffix
    if args.query_prefix:
        args.query = f"{args.query_prefix}\n{args.query}"
    if args.query_suffix:
        args.query = f"{args.query}\n{args.query_suffix}"

    if raw_args.command == "index":  # New subcommand logic
        from autocoder.index.for_command import index_command

        index_command(args, llm)
        return

    if raw_args.command == "index-query":  # New subcommand logic
        from autocoder.index.for_command import index_query_command

        index_query_command(args, llm)
        return

    if raw_args.command == "agent":
        if raw_args.agent_command == "planner":
            from autocoder.agent.planner import Planner

            planner = Planner(args, llm)
            v = planner.run(args.query)
            print()
            print("\n\n=============RESPONSE==================\n\n")
            request_queue.add_request(
                args.request_id,
                RequestValue(
                    value=DefaultValue(value=v), status=RequestOption.COMPLETED
                ),
            )
            print(v)
            # import time
            # time.sleep(3)
            # open_yaml_file_in_editor(
            #     get_last_yaml_file(
            #         actions_dir=os.path.abspath(
            #             os.path.join(args.source_dir, "actions")
            #         )
            #     )
            return
        elif raw_args.agent_command == "project_reader":
            from autocoder.agent.entry_command_agent import ProjectReaderAgent
            
            project_reader_agent = ProjectReaderAgent(args, llm, raw_args)
            project_reader_agent.run()
            return
        elif raw_args.agent_command == "voice2text":
            from autocoder.agent.entry_command_agent import Voice2TextAgent
            
            voice2text_agent = Voice2TextAgent(args, llm, raw_args)
            voice2text_agent.run()
            return
        elif raw_args.agent_command == "generate_command":
            from autocoder.agent.entry_command_agent import GenerateCommandAgent
            
            generate_command_agent = GenerateCommandAgent(args, llm, raw_args)
            generate_command_agent.run()
            return
        elif raw_args.agent_command == "auto_tool":
            from autocoder.agent.entry_command_agent import AutoToolAgent
            
            auto_tool_agent = AutoToolAgent(args, llm, raw_args)
            auto_tool_agent.run()
            return
        elif raw_args.agent_command == "designer":
            from autocoder.agent.entry_command_agent import DesignerAgent
            
            designer_agent = DesignerAgent(args, llm, raw_args)
            designer_agent.run()
            return

        elif raw_args.agent_command == "chat":
            from autocoder.agent.entry_command_agent import ChatAgent
            
            chat_agent = ChatAgent(args, llm, raw_args)
            chat_agent.run()
            return

        else:
            raise ValueError(f"Unknown agent name: {raw_args.agent_command}")

    if raw_args.command == "doc2html":
        from autocoder.common.screenshots import gen_screenshots
        from autocoder.common.anything2images import Anything2Images

        a2i = Anything2Images(llm=llm, args=args)
        html = a2i.to_html(args.urls)
        output_path = os.path.join(
            args.output, f"{os.path.splitext(os.path.basename(args.urls))[0]}.html"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Successfully converted {args.urls} to {output_path}")
        return

    if raw_args.command == "doc":

        if raw_args.doc_command == "build":
            from autocoder.rag.rag_entry import RAGFactory

            rag = RAGFactory.get_rag(llm=llm, args=args, path=args.source_dir)
            rag.build()
            print("Successfully built the document index")
            return
        elif raw_args.doc_command == "query":
            from autocoder.rag.rag_entry import RAGFactory

            rag = RAGFactory.get_rag(llm=llm, args=args, path="")
            response, contexts = rag.stream_search(args.query)

            s = ""
            print("\n\n=============RESPONSE==================\n\n")
            for res in response:
                print(res, end="")
                s += res

            print("\n\n=============CONTEXTS==================")

            print("\n".join(set([ctx["doc_url"] for ctx in contexts])))

            if args.execute:
                print("\n\n=============EXECUTE==================")
                executor = code_auto_execute.CodeAutoExecute(
                    llm, args, code_auto_execute.Mode.SINGLE_ROUND
                )
                executor.run(query=args.query, context=s, source_code="")
            return
        elif raw_args.doc_command == "serve":

            from autocoder.rag.llm_wrapper import LLWrapper

            server_args = ServerArgs(
                **{arg: getattr(raw_args, arg) for arg in vars(ServerArgs())}
            )
            server_args.served_model_name = server_args.served_model_name or args.model
            from autocoder.rag.rag_entry import RAGFactory

            if server_args.doc_dir:
                args.rag_type = "simple"
                rag = RAGFactory.get_rag(
                    llm=llm,
                    args=args,
                    path=server_args.doc_dir,
                    tokenizer_path=server_args.tokenizer_path,
                )
            else:
                rag = RAGFactory.get_rag(llm=llm, args=args, path="")

            llm_wrapper = LLWrapper(llm=llm, rag=rag)
            serve(llm=llm_wrapper, args=server_args)
            return

        elif raw_args.doc_command == "chat":
            from autocoder.rag.rag_entry import RAGFactory

            rag = RAGFactory.get_rag(llm=llm, args=args, path="")
            rag.stream_chat_repl(args.query)
            return

        else:
            http_doc = HttpDoc(args=args, llm=llm, urls=None)
            source_codes = http_doc.crawl_urls()
            with open(args.target_file, "w",encoding="utf-8") as f:
                f.write("\n".join([sc.source_code for sc in source_codes]))
            return

    dispacher = Dispacher(args, llm)
    dispacher.dispach()


if __name__ == "__main__":
    main()
