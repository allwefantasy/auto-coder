import byzerllm
from typing import List, Dict, Any, Optional
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher
from autocoder.common import git_utils, code_auto_execute
from autocoder.utils.llm_client_interceptors import token_counter_interceptor
from autocoder.db.store import Store

from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)

import yaml
import os
import uuid
from byzerllm.utils.client import EventCallbackResult, EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText

from jinja2 import Template
import hashlib
from autocoder.utils.rest import HttpDoc
from byzerllm.apps.byzer_storage.env import get_latest_byzer_retrieval_lib
from autocoder.command_args import parse_args
from autocoder.rag.api_server import serve, ServerArgs
from autocoder.utils import open_yaml_file_in_editor, get_last_yaml_file
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
            logger.info(f"Loading include file: {abs_include_path}")
            with open(abs_include_path, "r") as f:
                include_config = yaml.safe_load(f)
                if not include_config:
                    logger.info(f"Include file {abs_include_path} is empty,skipping.")
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
        with open(args.file, "r") as f:
            config = yaml.safe_load(f)
            config = load_include_files(config, args.file)
            for key, value in config.items():
                if key != "file":  # 排除 --file 参数本身
                    ## key: ENV {{VARIABLE_NAME}}
                    if isinstance(value, str) and value.startswith("ENV"):
                        template = Template(value.removeprefix("ENV").strip())
                        value = template.render(os.environ)
                    setattr(args, key, value)
    # if not args.request_id:
    #     args.request_id = str(uuid.uuid4())

    if raw_args.command == "revert":
        repo_path = args.source_dir

        file_content = open(args.file).read()
        md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
        file_name = os.path.basename(args.file)

        revert_result = git_utils.revert_changes(
            repo_path, f"auto_coder_{file_name}_{md5}"
        )
        if revert_result:
            print(f"Successfully reverted changes for {args.file}")
        else:
            print(f"Failed to revert changes for {args.file}")
        return

    if not os.path.isabs(args.source_dir):
        args.source_dir = os.path.abspath(args.source_dir)

    if not args.silence:
        print("Command Line Arguments:")
        print("-" * 50)
        for arg, value in vars(args).items():
            if arg == "context" and value:
                print(f"{arg:20}: {value[:30]}...")
            else:
                print(f"{arg:20}: {value}")
        print("-" * 50)

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
        os.makedirs(os.path.join(args.source_dir, ".auto-coder"), exist_ok=True)

        from autocoder.common.command_templates import create_actions

        source_dir = os.path.abspath(args.source_dir)
        create_actions(
            source_dir=source_dir,
            params={"project_type": args.project_type, "source_dir": source_dir},
        )
        git_utils.init(os.path.abspath(args.source_dir))

        with open(os.path.join(source_dir, ".gitignore"), "a") as f:
            f.write("\n.auto-coder/")
            f.write("\nactions/")
            f.write("\noutput.txt")

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
        actions_dir = os.path.join(os.getcwd(), "actions")
        if not os.path.exists(actions_dir):
            print("Current directory does not have an actions directory")
            return

        action_files = [
            f for f in os.listdir(actions_dir) if f[:3].isdigit() and f.endswith(".yml")
        ]
        if not action_files:
            max_seq = 0
        else:
            seqs = [int(f[:3]) for f in action_files]
            max_seq = max(seqs)

        new_seq = str(max_seq + 1).zfill(3)
        prev_files = [f for f in action_files if int(f[:3]) < int(new_seq)]

        if raw_args.from_yaml:
            # If --from_yaml is specified, copy content from the matching YAML file
            from_files = [f for f in action_files if f.startswith(raw_args.from_yaml)]
            if from_files:
                from_file = from_files[0]  # Take the first match
                with open(os.path.join(actions_dir, from_file), "r") as f:
                    content = f.read()
                new_file = os.path.join(actions_dir, f"{new_seq}_{raw_args.name}.yml")
                with open(new_file, "w") as f:
                    f.write(content)
            else:
                print(f"No YAML file found matching prefix: {raw_args.from_yaml}")
                return
        else:
            # If --from_yaml is not specified, use the previous logic
            if not prev_files:
                new_file = os.path.join(actions_dir, f"{new_seq}_{raw_args.name}.yml")
                with open(new_file, "w") as f:
                    pass
            else:
                prev_file = sorted(prev_files)[-1]  # 取序号最大的文件
                with open(os.path.join(actions_dir, prev_file), "r") as f:
                    content = f.read()
                new_file = os.path.join(actions_dir, f"{new_seq}_{raw_args.name}.yml")
                with open(new_file, "w") as f:
                    f.write(content)

        print(f"Successfully created new action file: {new_file}")

        # open_yaml_file_in_editor(new_file)
        return

    if args.model:

        home = os.path.expanduser("~")
        auto_coder_dir = os.path.join(home, ".auto-coder")
        libs_dir = os.path.join(auto_coder_dir, "storage", "libs")
        code_search_path = None
        if os.path.exists(libs_dir):
            retrieval_libs_dir = os.path.join(
                libs_dir, get_latest_byzer_retrieval_lib(libs_dir)
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

        if args.code_model:
            code_model = byzerllm.ByzerLLM()
            code_model.setup_default_model_name(args.code_model)
            llm.setup_sub_client("code_model", code_model)

        if args.human_as_model:

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

                try:
                    import pyperclip

                    pyperclip.copy(final_ins)
                    console.print(
                        Panel(
                            "You are now in Human as Model mode. The content has been copied to your clipboard.\n"
                            "The system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\n"
                            "Use '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again.",
                            title="Instructions",
                            border_style="blue",
                            expand=False,
                        )
                    )
                except Exception:
                    logger.warning(
                        "pyperclip not installed or clipboard is not supported, instruction will not be copied to clipboard."
                    )
                    console.print(
                        Panel(
                            "You are now in Human as Model mode. [bold red]The content could not be copied to your clipboard.[/bold red]\n"
                            "but you can copy prompt from output.txt file.\n"
                            "The system is waiting for your input. When finished, enter 'EOF' on a new line to submit.\n"
                            "Use '/break' to exit this mode. If you have issues with copy-paste, use '/clear' to clean and paste again.",
                            title="Instructions",
                            border_style="blue",
                            expand=False,
                        )
                    )

                if args.request_id and not args.silence:
                    event_data = {
                        "instruction": final_ins,
                        "model": model,
                        "request_id": args.request_id,
                    }
                    response_json = queue_communicate.send_event(
                        request_id=args.request_id,
                        event=CommunicateEvent(
                            event_type=CommunicateEventType.CODE_HUMAN_AS_MODEL.value,
                            data=json.dumps(event_data, ensure_ascii=False),
                        ),
                    )
                    response = json.loads(response_json)
                    v = [
                        {
                            "predict": response["value"],
                            "input": input_value[0]["instruction"],
                            "metadata": {},
                        }
                    ]
                    return False, v

                lines = []
                while True:
                    line = prompt(FormattedText([("#00FF00", "> ")]), multiline=False)
                    line_lower = line.strip().lower()
                    if line_lower in ["eof", "/eof"]:
                        break
                    elif line_lower in ["/clear"]:
                        lines = []
                        print("\033[2J\033[H")  # Clear terminal screen
                        continue
                    elif line_lower in ["/break"]:
                        raise Exception("User requested to break the operation.")
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

            llm.add_event_callback(EventName.BEFORE_CALL_MODEL, intercept_callback)
            code_model = llm.get_sub_client("code_model")
            if code_model:
                code_model.add_event_callback(
                    EventName.BEFORE_CALL_MODEL, intercept_callback
                )
        # llm.add_event_callback(EventName.AFTER_CALL_MODEL, token_counter_interceptor)

        code_model = llm.get_sub_client("code_model")
        if code_model:
            code_model.add_event_callback(
                EventName.AFTER_CALL_MODEL, token_counter_interceptor
            )

        llm.setup_template(model=args.model, template="auto")
        llm.setup_default_model_name(args.model)
        llm.setup_max_output_length(args.model, args.model_max_length)
        llm.setup_max_input_length(args.model, args.model_max_input_length)
        llm.setup_extra_generation_params(
            args.model, {"max_length": args.model_max_length}
        )

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
            # )
            return
        elif raw_args.agent_command == "project_reader":
            from autocoder.agent.project_reader import ProjectReader

            project_reader = ProjectReader(args, llm)
            v = project_reader.run(args.query)
            request_queue.add_request(
                args.request_id,
                RequestValue(
                    value=DefaultValue(value=v), status=RequestOption.COMPLETED
                ),
            )
            console = Console()
            markdown_content = v

            with Live(
                Panel("", title="Response", border_style="green", expand=False),
                refresh_per_second=4,
            ) as live:
                live.update(
                    Panel(
                        Markdown(markdown_content),
                        title="Response",
                        border_style="green",
                        expand=False,
                    )
                )

            return
        elif raw_args.agent_command == "voice2text":
            from autocoder.common.audio import TranscribeAudio
            import tempfile

            transcribe_audio = TranscribeAudio()
            temp_wav_file = os.path.join(tempfile.gettempdir(), "voice_input.wav")

            console = Console()

            transcribe_audio.record_audio(temp_wav_file)
            console.print(
                Panel(
                    "Recording finished. Transcribing...",
                    title="Voice",
                    border_style="green",
                )
            )

            if llm and llm.get_sub_client("voice2text_model"):
                voice2text_llm = llm.get_sub_client("voice2text_model")
            else:
                voice2text_llm = llm
            transcription = transcribe_audio.transcribe_audio(
                temp_wav_file, voice2text_llm
            )

            console.print(
                Panel(
                    f"Transcription: <_transcription_>{transcription}</_transcription_>",
                    title="Result",
                    border_style="magenta",
                )
            )

            with open(os.path.join(".auto-coder", "exchange.txt"), "w") as f:
                f.write(transcription)

            request_queue.add_request(
                args.request_id,
                RequestValue(
                    value=DefaultValue(value=transcription),
                    status=RequestOption.COMPLETED,
                ),
            )

            os.remove(temp_wav_file)
            return
        elif raw_args.agent_command == "generate_command":
            from autocoder.common.command_generator import generate_shell_script

            console = Console()

            console.print(
                Panel(
                    f"Generating shell script from user input {args.query}...",
                    title="Command Generator",
                    border_style="green",
                )
            )

            shell_script = generate_shell_script(args.query, llm)

            console.print(
                Panel(
                    shell_script,
                    title="Shell Script",
                    border_style="magenta",
                )
            )

            with open(os.path.join(".auto-coder", "exchange.txt"), "w") as f:
                f.write(shell_script)

            request_queue.add_request(
                args.request_id,
                RequestValue(
                    value=DefaultValue(value=shell_script),
                    status=RequestOption.COMPLETED,
                ),
            )

            return
        elif raw_args.agent_command == "auto_tool":
            from autocoder.agent.auto_tool import AutoTool

            auto_tool = AutoTool(args, llm)
            v = auto_tool.run(args.query)
            if args.request_id:
                request_queue.add_request(
                    args.request_id,
                    RequestValue(
                        value=DefaultValue(value=v), status=RequestOption.COMPLETED
                    ),
                )
            console = Console()
            markdown_content = v

            with Live(
                Panel("", title="Response", border_style="green", expand=False),
                refresh_per_second=4,
            ) as live:
                live.update(
                    Panel(
                        Markdown(markdown_content),
                        title="Response",
                        border_style="green",
                        expand=False,
                    )
                )
            return

        elif raw_args.agent_command == "chat":
            from autocoder.rag.rag_entry import RAGFactory

            memory_dir = os.path.join(args.source_dir, ".auto-coder", "memory")
            os.makedirs(memory_dir, exist_ok=True)
            memory_file = os.path.join(memory_dir, "chat_history.json")
            console = Console()
            if args.new_session:
                chat_history = {"ask_conversation": []}
                with open(memory_file, "w") as f:
                    json.dump(chat_history, f, ensure_ascii=False)
                console.print(
                    Panel(
                        "New session started. Previous chat history has been cleared.",
                        title="Session Status",
                        expand=False,
                        border_style="green",
                    )
                )
                return

            if os.path.exists(memory_file):
                with open(memory_file, "r") as f:
                    chat_history = json.load(f)
            else:
                chat_history = {"ask_conversation": []}

            chat_history["ask_conversation"].append(
                {"role": "user", "content": args.query}
            )

            pre_conversations = []
            if args.context:
                context = json.loads(args.context)
                if "file_content" in context:
                    file_content = context["file_content"]
                    pre_conversations.append(
                        {
                            "role": "user",
                            "content": f"下面是一些文档和源码，如果用户的问题和他们相关，请参考他们：{file_content}",
                        },
                    )
                    pre_conversations.append({"role": "assistant", "content": "read"})

            loaded_conversations = (
                pre_conversations + chat_history["ask_conversation"][-31:]
            )

            if args.enable_rag_search or args.enable_rag_context:
                rag = RAGFactory.get_rag(llm=llm, args=args, path="")
                response = rag.stream_chat_oai(conversations=loaded_conversations)[0]
                v = ([item, None] for item in response)
            else:
                v = llm.stream_chat_oai(
                    conversations=loaded_conversations, delta_mode=True
                )

            assistant_response = ""
            markdown_content = ""

            with Live(
                Panel("", title="Response", border_style="green", expand=False),
                refresh_per_second=4,
            ) as live:
                for res in v:
                    markdown_content += res[0]
                    assistant_response += res[0]
                    request_queue.add_request(
                        args.request_id,
                        RequestValue(
                            value=StreamValue(value=[res[0]]),
                            status=RequestOption.RUNNING,
                        ),
                    )
                    live.update(
                        Panel(
                            Markdown(markdown_content),
                            title="Response",
                            border_style="green",
                            expand=False,
                        )
                    )

            request_queue.add_request(
                args.request_id,
                RequestValue(
                    value=StreamValue(value=[""]), status=RequestOption.COMPLETED
                ),
            )

            chat_history["ask_conversation"].append(
                {"role": "assistant", "content": assistant_response}
            )

            with open(memory_file, "w") as f:
                json.dump(chat_history, f, ensure_ascii=False)
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
        elif raw_args.doc_command == "chat":
            from autocoder.rag.rag_entry import RAGFactory

            rag = RAGFactory.get_rag(llm=llm, args=args, path="")
            rag.stream_chat_repl(args.query)
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

        else:
            http_doc = HttpDoc(args=args, llm=llm, urls=None)
            source_codes = http_doc.crawl_urls()
            with open(args.target_file, "w") as f:
                f.write("\n".join([sc.source_code for sc in source_codes]))
            return

    dispacher = Dispacher(args, llm)
    dispacher.dispach()


if __name__ == "__main__":
    main()
