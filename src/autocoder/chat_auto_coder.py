from autocoder.run_context import get_run_context,RunMode

# 设置运行模式为终端模式
get_run_context().set_mode(RunMode.TERMINAL)

import argparse
import os
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from autocoder.version import __version__
from autocoder.chat_auto_coder_lang import get_message
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.completion import Completer, Completion
from autocoder.plugins import PluginManager
from autocoder.events.event_manager_singleton import gengerate_event_file_path
from autocoder.common.global_cancel import global_cancel
from autocoder.chat.models_command import handle_models_command
from autocoder.auto_coder_runner import (
    auto_command,    
    configure, # Keep configure if it's used elsewhere or by handle_conf_command internally (though we adapted handle_conf_command not to)
    # manage_models, # Removed
    # print_conf, # Removed
    save_memory,
    exclude_dirs,
    exclude_files,
    ask,
    coding,
    load_tokenizer,
    initialize_system,
    InitializeSystemRequest,
    add_files,
    remove_files,
    index_query,
    index_build,
    index_export,
    index_import,
    list_files,
    lib_command,
    mcp,
    revert,
    commit,
    design,
    voice_input,
    chat,
    gen_and_exec_shell_command,
    execute_shell_command,
    get_mcp_server,
    completer,
    summon,
    get_memory,
    active_context,
    rules,
    start as start_engine,
    stop as stop_engine
)
# Ensure the correct import is present
from autocoder.chat.conf_command import handle_conf_command

# Create a global plugin manager
plugin_manager = PluginManager()

# Create wrapped versions of intercepted functions
original_functions = {
    "ask": ask,
    "coding": coding,
    "chat": chat,
    "design": design,
    "voice_input": voice_input,
    "auto_command": auto_command,
    "execute_shell_command": execute_shell_command,
    "active_context": active_context,
}


def parse_arguments():

    parser = argparse.ArgumentParser(description="Chat Auto Coder")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Enter the auto-coder.chat without initializing the system",
    )

    parser.add_argument(
        "--skip_provider_selection",
        action="store_true",
        help="Skip the provider selection",
    )

    parser.add_argument(
        "--product_mode",
        type=str,
        default="lite",
        help="The mode of the auto-coder.chat, lite/pro default is lite",
    )

    parser.add_argument("--lite", action="store_true", help="Lite mode")
    parser.add_argument("--pro", action="store_true", help="Pro mode")

    return parser.parse_args()


def show_help():
    print(f"\033[1m{get_message('official_doc')}\033[0m")
    print()
    print(f"\033[1m{get_message('supported_commands')}\033[0m")
    print()
    print(
        f"  \033[94m{get_message('commands')}\033[0m - \033[93m{get_message('description')}\033[0m"
    )
    print(
        f"  \033[94m/add_files\033[0m \033[93m<file1> <file2> ...\033[0m - \033[92m{get_message('add_files_desc')}\033[0m"
    )
    print(
        f"  \033[94m/remove_files\033[0m \033[93m<file1>,<file2> ...\033[0m - \033[92m{get_message('remove_files_desc')}\033[0m"
    )
    print(
        f"  \033[94m/chat\033[0m \033[93m<query>\033[0m - \033[92m{get_message('chat_desc')}\033[0m"
    )
    print(
        f"  \033[94m/coding\033[0m \033[93m<query>\033[0m - \033[92m{get_message('coding_desc')}\033[0m"
    )    
    print(
        f"  \033[94m/summon\033[0m \033[93m<query>\033[0m - \033[92m{get_message('summon_desc')}\033[0m"
    )
    print(f"  \033[94m/revert\033[0m - \033[92m{get_message('revert_desc')}\033[0m")
    print(f"  \033[94m/commit\033[0m - \033[92m{get_message('commit_desc')}\033[0m")
    print(
        f"  \033[94m/conf\033[0m \033[93m<key>:<value>\033[0m  - \033[92m{get_message('conf_desc')}\033[0m"
    )
    print(
        f"  \033[94m/index/query\033[0m \033[93m<args>\033[0m - \033[92m{get_message('index_query_desc')}\033[0m"
    )
    print(
        f"  \033[94m/index/build\033[0m - \033[92m{get_message('index_build_desc')}\033[0m"
    )
    print(
        f"  \033[94m/list_files\033[0m - \033[92m{get_message('list_files_desc')}\033[0m"
    )
    print(f"  \033[94m/help\033[0m - \033[92m{get_message('help_desc')}\033[0m")
    print(
        f"  \033[94m/exclude_dirs\033[0m \033[93m<dir1>,<dir2> ...\033[0m - \033[92m{get_message('exclude_dirs_desc')}\033[0m"
    )
    print(
        f"  \033[94m/shell\033[0m \033[93m<command>\033[0m - \033[92m{get_message('shell_desc')}\033[0m"
    )
    print(
        f"  \033[94m/voice_input\033[0m - \033[92m{get_message('voice_input_desc')}\033[0m"
    )
    print(f"  \033[94m/mode\033[0m - \033[92m{get_message('mode_desc')}\033[0m")
    print(f"  \033[94m/lib\033[0m - \033[92m{get_message('lib_desc')}\033[0m")
    print(f"  \033[94m/models\033[0m - \033[92m{get_message('models_desc')}\033[0m")
    print(f"  \033[94m/plugins\033[0m - \033[92m{get_message('plugins_desc')}\033[0m")
    print(f"  \033[94m/active_context\033[0m - \033[92m{get_message('active_context_desc')}\033[0m")
    print(f"  \033[94m/exit\033[0m - \033[92m{get_message('exit_desc')}\033[0m")
    print()

    # 显示插件命令
    if plugin_manager.command_handlers:
        print("\033[1mPlugin Commands:\033[0m")
        print("  \033[94mCommand\033[0m - \033[93mDescription\033[0m")
        for cmd, (_, desc, plugin_id) in plugin_manager.command_handlers.items():
            plugin = plugin_manager.get_plugin(plugin_id)
            print(
                f"  \033[94m{cmd}\033[0m - \033[92m{desc} (from {plugin.plugin_name()})\033[0m"
            )
        print()


class EnhancedCompleter(Completer):
    """结合内置补全器和插件补全功能的增强补全器"""

    def __init__(self, base_completer: Completer, plugin_manager: PluginManager):
        self.base_completer: Completer = base_completer
        self.plugin_manager: PluginManager = plugin_manager

    def get_completions(self, document, complete_event):
        # 获取当前输入的文本
        text_before_cursor = document.text_before_cursor.lstrip()

        # 只有当我们需要处理命令补全时才进行处理
        if text_before_cursor.startswith("/"):

            # 获取当前输入的命令前缀
            current_input = text_before_cursor
            # 检查是否需要动态补全
            if " " in current_input:
                # 将连续的空格替换为单个空格
                _input_one_space = " ".join(current_input.split())
                # 先尝试动态补全特定命令
                dynamic_cmds = self.plugin_manager.get_dynamic_cmds()
                for dynamic_cmd in dynamic_cmds:
                    if _input_one_space.startswith(dynamic_cmd):
                        # 使用 PluginManager 处理动态补全，通常是用于命令或子命令动态的参数值列表的补全
                        completions = self.plugin_manager.process_dynamic_completions(
                            dynamic_cmd, current_input
                        )
                        for completion_text, display_text in completions:
                            yield Completion(
                                completion_text,
                                start_position=0,
                                display=display_text,
                            )
                        return

                # 如果不是特定命令，检查一般命令 + 空格的情况, 通常是用于固定的下级子命令列表的补全
                cmd_parts = current_input.split(maxsplit=1)
                base_cmd = cmd_parts[0]

                # 获取插件命令补全
                plugin_completions_dict = self.plugin_manager.get_plugin_completions()

                # 如果命令存在于补全字典中，进行处理
                if base_cmd in plugin_completions_dict:
                    yield from self._process_command_completions(
                        base_cmd, current_input, plugin_completions_dict[base_cmd]
                    )
                    return
            # 处理直接命令补全 - 如果输入不包含空格，匹配整个命令
            for command in self.plugin_manager.get_all_commands_with_prefix(current_input):
                yield Completion(
                    command[len(current_input) :],
                    start_position=0,
                    display=command,
                )

        # 获取并返回基础补全器的补全
        if self.base_completer:
            for completion in self.base_completer.get_completions(
                document, complete_event
            ):
                yield completion

    def _process_command_completions(self, command, current_input, completions):
        """处理通用命令补全"""
        # 提取子命令前缀
        parts = current_input.split(maxsplit=1)
        cmd_prefix = ""
        if len(parts) > 1:
            cmd_prefix = parts[1].strip()

        # 对于任何命令，当子命令前缀为空或与补全选项匹配时，都显示补全
        for completion in completions:
            if cmd_prefix == "" or completion.startswith(cmd_prefix):
                # 只提供未输入部分作为补全
                remaining_text = completion[len(cmd_prefix) :]
                # 修复：设置 start_position 为 0，这样不会覆盖用户已输入的部分
                start_position = 0
                yield Completion(
                    remaining_text,
                    start_position=start_position,
                    display=completion,
                )

    async def get_completions_async(self, document, complete_event):
        """异步获取补全内容。

        这个方法在最新版本的prompt_toolkit中是必需的，
        它简单地调用同步版本并以异步方式yield结果。
        """
        for completion in self.get_completions(document, complete_event):
            yield completion


ARGS = None


def main():
    load_tokenizer()
    start_engine()

    ARGS = parse_arguments()

    if ARGS.lite:
        ARGS.product_mode = "lite"

    if ARGS.pro:
        ARGS.product_mode = "pro"

    if not ARGS.quick:
        initialize_system(
            InitializeSystemRequest(
                product_mode=ARGS.product_mode,
                skip_provider_selection=ARGS.skip_provider_selection,
                debug=ARGS.debug,
                quick=ARGS.quick,
                lite=ARGS.lite,
                pro=ARGS.pro,
            )
        )

    # Initialize plugin system
    # Add default plugin directory into global plugin dirs
    plugin_manager.load_global_plugin_dirs()
    plugin_manager.add_global_plugin_directory(os.path.join(os.path.dirname(__file__), "plugins"))

    # 加载保存的运行时配置
    plugin_manager.load_runtime_cfg()

    memory = get_memory()

    configure(f"product_mode:{ARGS.product_mode}")

    MODES = {
        "normal": "normal",
        "auto_detect": "nature language auto detect",
        "voice_input": "voice input",
    }

    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):
        event.app.exit()

    @kb.add("tab")
    def _(event):
        b = event.current_buffer
        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=False)

    @kb.add("c-g")
    def _(event):
        transcription = voice_input()
        if transcription:
            event.app.current_buffer.insert_text(transcription)

    @kb.add("c-k")
    def _(event):
        if "mode" not in memory:
            memory["mode"] = "auto_detect"

        current_mode = memory["mode"]
        if current_mode == "normal":
            memory["mode"] = "auto_detect"
        elif current_mode == "auto_detect":
            memory["mode"] = "voice_input"
        else:  # voice_input
            memory["mode"] = "normal"
        
        save_memory()
        event.app.invalidate()

    @kb.add("c-n")
    def _(event):
        if "human_as_model" not in memory["conf"]:
            memory["conf"]["human_as_model"] = "false"

        current_status = memory["conf"]["human_as_model"]
        new_status = "true" if current_status == "false" else "false"
        configure(f"human_as_model:{new_status}", skip_print=True)
        event.app.invalidate()

    # 应用插件的键盘绑定
    plugin_manager.apply_keybindings(kb)

    def get_bottom_toolbar():
        if "mode" not in memory:
            memory["mode"] = "auto_detect"
        mode = memory["mode"]
        human_as_model = memory["conf"].get("human_as_model", "false")
        if mode not in MODES:
            mode = "auto_detect"
        pwd = os.getcwd()
        pwd_parts = pwd.split(os.sep)
        if len(pwd_parts) > 3:
            pwd = os.sep.join(pwd_parts[-3:])

        # Add plugin information to toolbar
        plugin_info = (
            f"Plugins: {len(plugin_manager.plugins)}" if plugin_manager.plugins else ""
        )
        return f"Current Dir: {pwd} \nMode: {MODES[mode]}(ctrl+k) | Human as Model: {human_as_model}(ctrl+n) | {plugin_info}"

    # 创建一个继承Completer的增强补全器
    enhanced_completer = EnhancedCompleter(completer, plugin_manager)

    # Define the path for the history file
    history_file_path = os.path.join(os.getcwd(), ".auto-coder", "auto-coder.chat", "history", "command_history.txt")
    # Ensure the directory exists
    os.makedirs(os.path.dirname(history_file_path), exist_ok=True)

    session = PromptSession(
        history=FileHistory(history_file_path),  # Use FileHistory
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=False,
        completer=enhanced_completer,
        complete_while_typing=True,
        key_bindings=kb,
        bottom_toolbar=get_bottom_toolbar,
    )
    print(
        f"""
    \033[1;32m  ____ _           _          _         _               ____          _           
    / ___| |__   __ _| |_       / \  _   _| |_ ___        / ___|___   __| | ___ _ __ 
    | |   | '_ \ / _` | __|____ / _ \| | | | __/ _ \ _____| |   / _ \ / _` |/ _ \ '__|
    | |___| | | | (_| | ||_____/ ___ \ |_| | || (_) |_____| |__| (_) | (_| |  __/ |   
    \____|_| |_|\__,_|\__|   /_/   \_\__,_|\__\___/       \____\___/ \__,_|\___|_| 
                                                                        v{__version__}
    \033[0m"""
    )
    print("\033[1;34mType /help to see available commands.\033[0m\n")

    # Add plugin information to startup message
    if plugin_manager.plugins:
        print("\033[1;34mLoaded Plugins:\033[0m")
        for name, plugin in plugin_manager.plugins.items():
            print(f"  - {name} (v{plugin.version}): {plugin.description}")
        print()

    show_help()

    style = Style.from_dict(
        {
            "username": "#884444",
            "at": "#00aa00",
            "colon": "#0000aa",
            "pound": "#00aa00",
            "host": "#00ffff bg:#444400",
        }
    )

    new_prompt = ""

    # Create wrapped versions of functions that plugins want to intercept
    wrapped_functions = {}
    for func_name, original_func in original_functions.items():
        wrapped_functions[func_name] = plugin_manager.wrap_function(
            original_func, func_name
        )

    # Replace original functions with wrapped versions
    global ask, coding, chat, design, voice_input, auto_command, execute_shell_command, active_context
    ask = wrapped_functions.get("ask", ask)
    coding = wrapped_functions.get("coding", coding)
    chat = wrapped_functions.get("chat", chat)
    design = wrapped_functions.get("design", design)
    voice_input = wrapped_functions.get("voice_input", voice_input)
    auto_command = wrapped_functions.get("auto_command", auto_command)
    active_context = wrapped_functions.get("active_context", active_context)
    execute_shell_command = wrapped_functions.get(
        "execute_shell_command", execute_shell_command
    )

    while True:
        try:
            prompt_message = [
                ("class:username", "coding"),
                ("class:at", "@"),
                ("class:host", "auto-coder.chat"),
                ("class:colon", ":"),
                ("class:path", "~"),
                ("class:dollar", "$ "),
            ]

            if new_prompt:
                user_input = session.prompt(
                    FormattedText(prompt_message), default=new_prompt, style=style
                )
            else:
                user_input = session.prompt(FormattedText(prompt_message), style=style)
            new_prompt = ""
            
            if "mode" not in memory:                
                memory["mode"] = "auto_detect"

            # 处理 user_input 的空格
            if user_input:
                temp_user_input = user_input.lstrip()  # 去掉左侧空格
                if temp_user_input.startswith("/"):
                    user_input = temp_user_input

            # Check if this is a plugin command
            if user_input.startswith("/"):
                plugin_result = plugin_manager.process_command(user_input)
                if plugin_result:
                    plugin_name, handler, args = plugin_result
                    if handler:
                        handler(*args)
                        continue                                    
            if (
                memory["mode"] == "auto_detect"
                and user_input
                and not user_input.startswith("/")
            ):
                event_file, file_id = gengerate_event_file_path()
                configure(f"event_file:{event_file}")
                global_cancel.register_token(event_file)
                auto_command(user_input)

            elif memory["mode"] == "voice_input" and not user_input.startswith("/"):
                text = voice_input()
                if text:  # Check if text is not None
                    new_prompt = "/coding " + text

            elif user_input.startswith("/voice_input"):
                text = voice_input()
                if text:  # Check if text is not None
                    new_prompt = "/coding " + text

            elif user_input.startswith("/clear") or user_input.startswith("/cls"):
                print("\033c")                

            elif user_input.startswith("/add_files"):
                args = user_input[len("/add_files") :].strip().split()
                add_files(args)
            elif user_input.startswith("/remove_files"):
                file_names = user_input[len("/remove_files") :].strip().split(",")
                remove_files(file_names)
            elif user_input.startswith("/index/query"):
                query = user_input[len("/index/query") :].strip()
                index_query(query)

            elif user_input.startswith("/index/build"):
                event_file, file_id = gengerate_event_file_path()
                configure(f"event_file:{event_file}")
                global_cancel.register_token(event_file)
                index_build()

            elif user_input.startswith("/index/export"):
                export_path = user_input[len("/index/export") :].strip()
                index_export(export_path)

            elif user_input.startswith("/index/import"):
                import_path = user_input[len("/index/import") :].strip()
                index_import(import_path)

            elif user_input.startswith("/list_files"):
                list_files()

            elif user_input.startswith("/models"):
                query = user_input[len("/models") :].strip()
                handle_models_command(query, get_memory())                    

            elif user_input.startswith("/mode"):
                conf = user_input[len("/mode") :].strip()
                if not conf:
                    print(memory["mode"])
                else:
                    memory["mode"] = conf
                    save_memory()

            elif user_input.startswith("/conf/export"):
                from autocoder.common.conf_import_export import export_conf
                export_conf(os.getcwd(), user_input[len("/conf/export") :].strip() or ".")

            elif user_input.startswith("/plugins"):
                # 提取命令参数并交由 plugin_manager 处理
                args = user_input[len("/plugins") :].strip().split()
                result = plugin_manager.handle_plugins_command(args)
                print(result, end="")

            # Handle /conf and its subcommands like /conf /export, /conf /import
            elif user_input.startswith("/conf"):
                # Extract everything after "/conf"
                command_args = user_input[len("/conf"):].strip()
                # Call the handler from conf_command.py and print its string result
                result_message = handle_conf_command(command_args, memory)
                print(result_message)
            elif user_input.startswith("/revert"):
                revert()
            elif user_input.startswith("/commit"):
                query = user_input[len("/commit") :].strip()
                commit(query)
            elif user_input.startswith("/help"):
                query = user_input[len("/help") :].strip()
                if not query:
                    show_help()
                else:
                    help(query)

            elif user_input.startswith("/exclude_dirs"):
                dir_names = user_input[len("/exclude_dirs") :].strip().split(",")
                exclude_dirs(dir_names)

            elif user_input.startswith("/exclude_files"):
                query = user_input[len("/exclude_files") :].strip()
                exclude_files(query)           

            elif user_input.startswith("/exit"):
                raise EOFError()

            elif user_input.startswith("/coding"):
                event_file, file_id = gengerate_event_file_path()
                configure(f"event_file:{event_file}")
                global_cancel.register_token(event_file)
                query = user_input[len("/coding") :].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                    continue
                coding(query)                
            elif user_input.startswith("/chat"):
                event_file, file_id = gengerate_event_file_path()
                configure(f"event_file:{event_file}")
                global_cancel.register_token(event_file)
                query = user_input[len("/chat") :].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                else:
                    chat(query)

            elif user_input.startswith("/design"):
                query = user_input[len("/design") :].strip()
                if not query:
                    print("\033[91mPlease enter your design request.\033[0m")
                else:
                    design(query)

            elif user_input.startswith("/summon"):
                query = user_input[len("/summon") :].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                else:
                    summon(query)

            elif user_input.startswith("/lib"):
                args = user_input[len("/lib") :].strip().split()
                lib_command(args)

            elif user_input.startswith("/rules"):
                query = user_input[len("/rules") :].strip()
                rules(query)                    

            elif user_input.startswith("/mcp"):
                query = user_input[len("/mcp") :].strip()
                if not query:
                    print("Please enter your query.")
                else:
                    mcp(query)
                    
            elif user_input.startswith("/active_context"):
                query = user_input[len("/active_context") :].strip()
                active_context(query)

            elif user_input.startswith("/auto"):
                query = user_input[len("/auto") :].strip()
                auto_command(query)
            elif user_input.startswith("/debug"):
                code = user_input[len("/debug") :].strip()
                try:
                    result = eval(code)
                    print(f"Debug result: {result}")
                except Exception as e:
                    print(f"Debug error: {str(e)}")

            # elif user_input.startswith("/shell"):
            else:
                command = user_input
                if user_input.startswith("/shell"):
                    command = user_input[len("/shell") :].strip()
                    if not command:
                        print("Please enter a shell command to execute.")
                    else:
                        if command.startswith("/chat"):
                            event_file, file_id = gengerate_event_file_path()
                            global_cancel.register_token(event_file)
                            configure(f"event_file:{event_file}")
                            command = command[len("/chat") :].strip()
                            gen_and_exec_shell_command(command)
                        else:
                            execute_shell_command(command)

        except KeyboardInterrupt:
            continue
        except EOFError:
            try:
                # Shutdown all plugins before exiting
                plugin_manager.shutdown_all()                
                # save_memory()
                try:
                    if get_mcp_server():
                        get_mcp_server().stop()
                except Exception as e:
                    pass
                stop_engine()
            except Exception as e:
                print(
                    f"\033[91mAn error occurred while saving memory:\033[0m \033[93m{type(e).__name__}\033[0m - {str(e)}"
                )
            print("\n\033[93mExiting Chat Auto Coder...\033[0m")
            break
        except Exception as e:
            print(
                f"\033[91mAn error occurred:\033[0m \033[93m{type(e).__name__}\033[0m - {str(e)}"
            )
            if ARGS and ARGS.debug:
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    main()
