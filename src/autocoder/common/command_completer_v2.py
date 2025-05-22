import os
import shlex
from typing import Callable, Dict, Any, List, Iterable, Optional

import pydantic
from pydantic import BaseModel, SkipValidation
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

from autocoder.common import AutoCoderArgs
from autocoder.common.command_completer import FileSystemModel, MemoryConfig # Reuse models
from autocoder import models as models_module

# Define command structure in a more structured way if needed,
# but primarily rely on handlers for logic.
COMMAND_HIERARCHY = {
    "/add_files": {"/group": {"/add": {}, "/drop": {}, "/reset": {}, "/set": {}}, "/refresh": {}},
    "/remove_files": {"/all": {}},
    "/conf": {"/drop": {}, "/export": {}, "/import": {}, "/get": {}}, # Added list/get for clarity
    "/coding": {"/apply": {}, "/next": {}},
    "/chat": {"/new": {}, "/save": {}, "/copy": {}, "/mcp": {}, "/rag": {}, "/review": {}, "/learn": {}, "/no_context": {}},
    "/mcp": {"/add": {}, "/remove": {}, "/list": {}, "/list_running": {}, "/refresh": {}, "/info": {}},
    "/lib": {"/add": {}, "/remove": {}, "/list": {}, "/set-proxy": {}, "/refresh": {}, "/get": {}},
    "/models": {"/chat": {}, "/add": {}, "/add_model": {}, "/remove": {}, "/list": {}, "/speed": {}, "/speed-test": {}, "/input_price": {}, "/output_price": {}, "/activate": {}},
    "/auto": {},
    "/shell": {"/chat": {}},
    "/active_context": {"/list": {}, "/run": {}},
    "/index": {"/query": {}, "/build": {}, "/export": {}, "/import": {}},
    "/exclude_files": {"/list": {}, "/drop": {}},
    "/exclude_dirs": {}, # No specific subcommands shown in V1, treat as simple list
    "/commit": {}, # No specific subcommands shown in V1
    "/revert": {},
    "/ask": {},
    "/design": {"/svg": {}, "/sd": {}, "/logo": {}},
    "/summon": {},
    "/mode": {}, # Simple value completion
    "/voice_input": {},
    "/exit": {},
    "/help": {},
    "/list_files": {},
    "/clear": {},
    "/cls": {},
    "/debug": {},
    "/rules": {"/list": {}, "/get": {}, "/remove": {}, "/analyze": {}, "/commit": {}, "/help": {}},
}

class CommandCompleterV2(Completer):
    """
    A more extensible command completer using a handler-based approach.
    """
    def __init__(self, commands: List[str], file_system_model: FileSystemModel, memory_model: MemoryConfig):
        self.base_commands = commands # Top-level commands starting with /
        self.file_system_model = file_system_model
        self.memory_model = memory_model

        # Data stores, initialized and refreshable
        self.all_file_names: List[str] = []
        self.all_files: List[str] = []
        self.all_dir_names: List[str] = []
        self.all_files_with_dot: List[str] = []
        self.symbol_list: List[Any] = [] # Use Any for SymbolItem structure from runner
        self.current_file_names: List[str] = []
        self.config_keys = list(AutoCoderArgs.model_fields.keys())
        self.group_names: List[str] = []
        self.lib_names: List[str] = []
        self.model_names: List[str] = [] # Assuming models can be fetched

        self.refresh_files() # Initial data load
        self._update_dynamic_data() # Load groups, libs etc.

        # Map command prefixes or patterns to handler methods
        self.command_handlers: Dict[str, Callable] = {
            "/": self._handle_base_command,
            "/add_files": self._handle_add_files,
            "/remove_files": self._handle_remove_files,
            "/exclude_dirs": self._handle_exclude_dirs,
            "/exclude_files": self._handle_exclude_files,
            "/conf": self._handle_conf,
            "/lib": self._handle_lib,
            "/mcp": self._handle_mcp,
            "/models": self._handle_models,
            "/active_context": self._handle_active_context,
            "/mode": self._handle_mode,
            "/chat": self._handle_text_with_symbols,
            "/coding": self._handle_text_with_symbols,
            "/auto": self._handle_text_with_symbols,
            "/ask": self._handle_text_with_symbols, # Treat like chat for @/@@
            "/summon": self._handle_text_with_symbols,
            "/design": self._handle_design,
            "/rules": self._handle_rules,
            # Add handlers for other commands if they need specific logic beyond @/@@
            # Default handler for plain text or commands not explicitly handled
            "default": self._handle_text_with_symbols,
        }

    def _update_dynamic_data(self):
        """Load or update data that changes during runtime (groups, libs, current files)."""
        self.current_file_names = self.memory_model.get_memory_func().get("current_files", {}).get("files", [])
        self.group_names = list(self.memory_model.get_memory_func().get("current_files", {}).get("groups", {}).keys())
        self.lib_names = list(self.memory_model.get_memory_func().get("libs", {}).keys())
        # In a real scenario, might fetch model names from models_module
        try:            
            self.model_names = [m.get("name","") for m in models_module.load_models()]
        except ImportError:
            self.model_names = [] # Fallback if models module not available

    def refresh_files(self):
        """Refresh file and symbol lists from the file system model."""
        self.all_file_names = self.file_system_model.get_all_file_names_in_project()
        self.all_files = self.file_system_model.get_all_file_in_project()
        self.all_dir_names = self.file_system_model.get_all_dir_names_in_project()
        self.all_files_with_dot = self.file_system_model.get_all_file_in_project_with_dot()
        self.symbol_list = self.file_system_model.get_symbol_list()
        self._update_dynamic_data() # Also refresh dynamic data


    # --- Main Completion Logic ---

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor(WORD=True)

        # Update dynamic data on each completion request
        self._update_dynamic_data()        

        if not text.strip(): # Empty input
            yield from self._handle_base_command(document, complete_event, word_before_cursor, text)
            return

        parts = text.split(maxsplit=1)
        first_word = parts[0]

        # 1. Handle Base Command Completion (e.g., typing "/")
        if first_word.startswith("/") and len(parts) == 1 and not text.endswith(" "):
             yield from self._handle_base_command(document, complete_event, word_before_cursor, text)

        # 2. Dispatch to Specific Command Handlers
        elif first_word in self.command_handlers:
            handler = self.command_handlers[first_word]
            yield from handler(document, complete_event, word_before_cursor, text)

        # 3. Handle Special Prefixes within general text or unhandled commands
        elif word_before_cursor.startswith("@") and not word_before_cursor.startswith("@@"):
             yield from self._handle_at_completion(document, complete_event, word_before_cursor, text)
        elif word_before_cursor.startswith("@@"):
             yield from self._handle_double_at_completion(document, complete_event, word_before_cursor, text)
        elif word_before_cursor.startswith("<"): # Potential tag completion
             yield from self._handle_img_tag(document, complete_event, word_before_cursor, text)

        # 4. Default Handler (for plain text or commands without specific handlers)
        else:
            handler = self.command_handlers.get("default")
            if handler:
                yield from handler(document, complete_event, word_before_cursor, text)


    # --- Handler Methods ---

    def _handle_base_command(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completion for top-level commands starting with '/'."""
        command_prefix = text.lstrip() # The word being typed
        for cmd in self.base_commands:
            if cmd.startswith(command_prefix):
                yield Completion(cmd, start_position=-len(command_prefix))

    def _handle_add_files(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /add_files command."""
        args_text = text[len("/add_files"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # Sub-command completion
        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
            for sub_cmd in COMMAND_HIERARCHY["/add_files"]:
                if sub_cmd.startswith(last_part):
                     yield Completion(sub_cmd, start_position=-len(last_part))

        # File/Group completion based on context
        if args_text.startswith("/group"):
            group_args_text = args_text[len("/group"):].lstrip()
            group_parts = group_args_text.split()
            group_last_part = group_parts[-1] if group_parts and not text.endswith(" ") else ""

            # Complete subcommands of /group
            if not group_args_text or (len(group_parts) == 1 and not text.endswith(" ")):
                 for group_sub_cmd in COMMAND_HIERARCHY["/add_files"]["/group"]:
                    if group_sub_cmd.startswith(group_last_part):
                         yield Completion(group_sub_cmd, start_position=-len(group_last_part))

            # Complete group names for /drop or direct use
            elif group_parts and group_parts[0] in ["/drop", "/set"] or len(group_parts) >= 1 and not group_parts[0].startswith("/"):
                 current_word_for_group = group_last_part
                 # Handle comma-separated group names
                 if "," in current_word_for_group:
                     current_word_for_group = current_word_for_group.split(",")[-1]

                 yield from self._complete_items(current_word_for_group, self.group_names)

        elif args_text.startswith("/refresh"):
            pass # No further completion needed

        # Default: File path completion
        else:
             yield from self._complete_file_paths(word, text)


    def _handle_remove_files(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /remove_files command."""
        # 'word' is document.get_word_before_cursor(WORD=True)

        # Complete /all subcommand
        if "/all".startswith(word):
            yield Completion("/all", start_position=-len(word))

        # Complete from current file paths (relative paths)
        relative_current_files = [os.path.relpath(f, self.file_system_model.project_root) for f in self.current_file_names]        
        yield from self._complete_items_with_in(word, relative_current_files)

        # Also complete from just the base filenames
        current_basenames = [os.path.basename(f) for f in self.current_file_names]
        # Avoid duplicates if basename is same as relative path (e.g., top-level file)
        unique_basenames = [b for b in current_basenames if b not in relative_current_files]
        yield from self._complete_items_with_in(word, unique_basenames)


    def _handle_exclude_dirs(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /exclude_dirs command."""
        args_text = text[len("/exclude_dirs"):].lstrip()
        current_word = args_text.split(",")[-1].strip()
        yield from self._complete_items(current_word, self.all_dir_names)

    def _handle_exclude_files(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /exclude_files command."""
        args_text = text[len("/exclude_files"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
             for sub_cmd in COMMAND_HIERARCHY["/exclude_files"]:
                 if sub_cmd.startswith(last_part):
                      yield Completion(sub_cmd, start_position=-len(last_part))

        elif parts and parts[0] == "/drop":
             current_word = last_part
             yield from self._complete_items(current_word, self.memory_model.get_memory_func().get("exclude_files", []))
        else:
             # Suggest prefix for regex
             if not last_part:
                 yield Completion("regex://", start_position=0)
             elif "regex://".startswith(last_part):
                 yield Completion("regex://", start_position=-len(last_part))


    def _handle_conf(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /conf command."""
        args_text = text[len("/conf"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""                
        # Complete subcommands like /drop, /export, /import, /list, /get
        if not args_text or (len(parts) == 1 and not text.endswith(" ") and ":" not in text):
            for sub_cmd in COMMAND_HIERARCHY["/conf"]:
                if sub_cmd.startswith(last_part):
                    yield Completion(sub_cmd, start_position=-len(last_part))
            # Also complete config keys directly
            yield from self._complete_config_keys(last_part, add_colon=False)

        # Complete config keys after /drop or /get
        elif parts and parts[0] in ["/drop", "/get"]:
            yield from self._complete_config_keys(last_part, add_colon=False)

        # Complete file paths after /export or /import
        elif parts and parts[0] in ["/export", "/import"]:
             yield from self._complete_file_paths(word, text) # Use word here as it's likely the path

        # Complete config keys for setting (key:value)
        elif ":" not in last_part:             
             yield from self._complete_config_keys(last_part, add_colon=True)

         # Complete values after colon
        elif ":" in args_text:
            key_part = args_text.split(":", 1)[0].strip()
            value_part = args_text.split(":", 1)[1].strip() if ":" in args_text else ""
            yield from self._complete_config_values(key_part, value_part)
            # Example: Complete enum values or suggest file paths for path-like keys
            pass # Placeholder for future value completions

    def _complete_config_values(self, key: str, value: str) -> Iterable[Completion]:
        """Helper to complete configuration values based on the key."""
        start_pos = -len(value)

        # Model name completion for keys containing "model"
        if key.endswith("_model") or key == "model":
            # Refresh model names if they can change dynamically
            # self.refresh_model_names()            
            for model_name in self.model_names:
                if model_name.startswith(value) or value==":":
                    yield Completion(model_name, start_position=start_pos)
            # If a model name matched, we might prioritize these completions.
            # Consider returning here if model names are the only relevant values.

        # Boolean value completion
        field_info = AutoCoderArgs.model_fields.get(key)
        if field_info and field_info.annotation == bool:
            if "true".startswith(value): yield Completion("true", start_position=start_pos)
            if "false".startswith(value): yield Completion("false", start_position=start_pos)
            # If boolean matched, we might prioritize these completions.
            # Consider returning here if boolean is the only relevant value type.

        # Add more value completions based on key type or name here
        # e.g., enums, file paths, specific string formats


    def _handle_lib(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /lib command."""
        args_text = text[len("/lib"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # Complete subcommands
        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
             for sub_cmd in COMMAND_HIERARCHY["/lib"]:
                 if sub_cmd.startswith(last_part):
                      yield Completion(sub_cmd, start_position=-len(last_part))

        # Complete lib names for add/remove/get
        elif parts and parts[0] in ["/add", "/remove", "/get"]:
             yield from self._complete_items(last_part, self.lib_names)

        # Complete proxy URL for set-proxy (less specific, maybe suggest http/https?)
        elif parts and parts[0] == "/set-proxy":
             if "http://".startswith(last_part): yield Completion("http://", start_position=-len(last_part))
             if "https://".startswith(last_part): yield Completion("https://", start_position=-len(last_part))


    def _handle_mcp(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /mcp command."""
        args_text = text[len("/mcp"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # Complete subcommands
        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
             for sub_cmd in COMMAND_HIERARCHY["/mcp"]:
                 if sub_cmd.startswith(last_part):
                      yield Completion(sub_cmd, start_position=-len(last_part))
        # Potentially complete server names after /remove, /refresh, /add if available


    def _handle_models(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /models command."""
        args_text = text[len("/models"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # Complete subcommands
        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
             for sub_cmd in COMMAND_HIERARCHY["/models"]:
                 if sub_cmd.startswith(last_part):
                      yield Completion(sub_cmd, start_position=-len(last_part))

        # Complete model names for add/remove/speed/input_price/output_price/activate/chat
        elif parts and parts[0] in ["/add", "/remove", "/speed", "/input_price", "/output_price", "/activate", "/chat"]:
             yield from self._complete_items(last_part, self.model_names)

        # Complete parameters for /add_model (e.g., name=, base_url=)
        elif parts and parts[0] == "/add_model":
             # Suggest common keys if the last part is empty or partially typed
             common_keys = ["name=", "model_type=", "model_name=", "base_url=", "api_key_path=", "description=", "is_reasoning="]
             yield from self._complete_items(last_part, common_keys)

        elif parts and parts[0] == "/speed-test":
             if "/long_context".startswith(last_part):
                 yield Completion("/long_context", start_position=-len(last_part))


    def _handle_active_context(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /active_context command."""
        args_text = text[len("/active_context"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # Complete subcommands
        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
             for sub_cmd in COMMAND_HIERARCHY["/active_context"]:
                 if sub_cmd.startswith(last_part):
                      yield Completion(sub_cmd, start_position=-len(last_part))

        # Complete action file names for /run
        elif parts and parts[0] == "/run":
            # Assuming action files are in 'actions' dir and end with .yml
            action_dir = "actions"
            if os.path.isdir(action_dir):
                 try:
                     action_files = [f for f in os.listdir(action_dir) if f.endswith(".yml")]
                     yield from self._complete_items(last_part, action_files)
                 except OSError:
                     pass # Ignore if cannot list dir


    def _handle_mode(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /mode command."""
        args_text = text[len("/mode"):].lstrip()
        modes = ["normal", "auto_detect", "voice_input"]
        yield from self._complete_items(args_text, modes)

    def _handle_design(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completions for /design command."""
        args_text = text[len("/design"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # Complete subcommands
        if not args_text or (len(parts) == 1 and not text.endswith(" ")):
             for sub_cmd in COMMAND_HIERARCHY["/design"]:
                 if sub_cmd.startswith(last_part):
                      yield Completion(sub_cmd, start_position=-len(last_part))

    def _handle_text_with_symbols(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles general text input, including @, @@, <img> tags and command-specific subcommands."""
        # Check for command-specific subcommands first
        parts = text.split(maxsplit=1)
        command = parts[0]
        if command in COMMAND_HIERARCHY:
            args_text = parts[1] if len(parts) > 1 else ""
            sub_parts = args_text.split()
            last_part = sub_parts[-1] if sub_parts and not text.endswith(" ") else ""

            # Complete subcommands if applicable
            if not args_text or (len(sub_parts) == 1 and not text.endswith(" ")):
                if isinstance(COMMAND_HIERARCHY[command], dict):
                    for sub_cmd in COMMAND_HIERARCHY[command]:
                        if sub_cmd.startswith(last_part):
                            yield Completion(sub_cmd, start_position=-len(last_part))

        # Now handle @, @@, <img> regardless of command (or if no command)
        if word.startswith("@") and not word.startswith("@@"):
             yield from self._handle_at_completion(document, complete_event, word, text)
        elif word.startswith("@@"):
             yield from self._handle_double_at_completion(document, complete_event, word, text)
        elif word.startswith("<"): # Potential tag completion
             yield from self._handle_img_tag(document, complete_event, word, text)

    def _handle_rules(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """处理 /rules 命令的补全，支持子命令和规则文件路径。同时支持 @ 和 @@ 符号。"""
        args_text = text[len("/rules"):].lstrip()
        parts = args_text.split()
        last_part = parts[-1] if parts and not text.endswith(" ") else ""

        # 补全子命令
        if not args_text or (len(parts) == 1 and not text.endswith(" ") and parts[0].startswith("/")):
            for sub_cmd in COMMAND_HIERARCHY["/rules"]:
                if sub_cmd.startswith(last_part):
                    yield Completion(sub_cmd, start_position=-len(last_part))
            return

        # 根据子命令补全参数
        if parts and parts[0] == "/list" or parts[0] == "/get" or parts[0] == "/remove":
            # 获取规则文件或目录补全，可以是通配符
            # 这里可以简单地提供文件路径补全
            yield from self._complete_file_paths(last_part, text)
            # 也可以添加常用通配符补全
            common_patterns = ["*.md", "*.rules", "*.txt"]
            for pattern in common_patterns:
                if pattern.startswith(last_part):
                    yield Completion(pattern, start_position=-len(last_part))
            return

        # 对于 /commit 子命令，补全 /query
        if parts and parts[0] == "/commit":
            if "/query".startswith(last_part):
                yield Completion("/query", start_position=-len(last_part))
            return

        # 支持 @ 和 @@ 符号的补全，不管当前命令是什么
        if word.startswith("@") and not word.startswith("@@"):
            yield from self._handle_at_completion(document, complete_event, word, text)
        elif word.startswith("@@"):
            yield from self._handle_double_at_completion(document, complete_event, word, text)


    # --- Symbol/Tag Handlers ---
    def _handle_at_completion(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completion for single '@' (file paths)."""
        name = word[1:]
        yield from self._complete_file_paths(name, text, is_symbol=True)

    def _handle_double_at_completion(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completion for double '@@' (symbols)."""
        name = word[2:]
        yield from self._complete_symbols(name)

    def _handle_img_tag(self, document: Document, complete_event: CompleteEvent, word: str, text: str) -> Iterable[Completion]:
        """Handles completion for <img> tags and paths within them."""
        image_extensions = (
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp",
            ".svg", ".ico", ".heic", ".heif", ".raw", ".cr2", ".nef", ".arw",
            ".dng", ".orf", ".rw2", ".pef", ".srw", ".eps", ".ai", ".psd", ".xcf",
        )

        # Basic tag completion
        if "<img".startswith(word):
            yield Completion("<img>", start_position=-len(word))
        if "</img".startswith(word):
            yield Completion("</img>", start_position=-len(word))

        # Path completion inside <img> tag
        # Find the last opening <img> tag that isn't closed yet
        last_open_img = text.rfind("<img>")
        last_close_img = text.rfind("</img>")

        if last_open_img != -1 and (last_close_img == -1 or last_close_img < last_open_img):
            path_prefix = text[last_open_img + len("<img>"):]
            current_path_word = document.get_word_before_cursor(WORD=True) # Path part being typed

            # Only complete if cursor is within the tag content
            if document.cursor_position > last_open_img + len("<img>"):

                search_dir = os.path.dirname(path_prefix) if os.path.dirname(path_prefix) else "."
                file_basename = os.path.basename(current_path_word)

                try:
                    if os.path.isdir(search_dir):
                        for item in os.listdir(search_dir):
                            full_path = os.path.join(search_dir, item)
                            # Suggest directories or image files matching the prefix
                            if item.startswith(file_basename):
                                if os.path.isdir(full_path):
                                     relative_path = os.path.relpath(full_path, ".") # Use relative path
                                     yield Completion(relative_path + os.sep, start_position=-len(current_path_word), display=item + "/")
                                elif item.lower().endswith(image_extensions):
                                     relative_path = os.path.relpath(full_path, ".") # Use relative path
                                     yield Completion(relative_path, start_position=-len(current_path_word), display=item)
                except OSError:
                    pass # Ignore errors listing directories


    # --- Helper Methods ---

    def _complete_items_with_in(self, word: str, items: Iterable[str]) -> Iterable[Completion]:
        """Generic helper to complete a word from a list of items."""        
        for item in items:
            if item and word in item:
                yield Completion(item, start_position=-len(word))

    def _complete_items(self, word: str, items: Iterable[str]) -> Iterable[Completion]:
        """Generic helper to complete a word from a list of items."""
        if word is None: 
            word = ""
        for item in items:
            if item and item.startswith(word):
                yield Completion(item, start_position=-len(word))

    def _complete_config_keys(self, word: str, add_colon: bool = False) -> Iterable[Completion]:
        """Helper to complete configuration keys."""
        suffix = ":" if add_colon else ""
        for key in self.config_keys:
            if key.startswith(word):
                yield Completion(key + suffix, start_position=-len(word))        

    def _complete_file_paths(self, name: str, text: str, is_symbol: bool = False) -> Iterable[Completion]:
        """Helper to complete file paths (@ completion or general path)."""
        if name is None: name = ""
        start_pos = -len(name)

        # Prioritize active files if triggered by @
        if is_symbol:
            for file_path in self.current_file_names:
                rel_path = os.path.relpath(file_path, self.file_system_model.project_root)
                display_name = self._get_display_path(file_path)
                if name in rel_path or name in os.path.basename(file_path):
                     yield Completion(rel_path, start_position=start_pos, display=f"{display_name} (active)")

        # General file path completion (relative paths with dot)
        if name.startswith("."):
            yield from self._complete_items(name, self.all_files_with_dot)
            return # Don't mix with other completions if starting with .

        # Complete base file names
        yield from self._complete_items(name, self.all_file_names)

        # Complete full paths (if name is part of the path)
        for file_path in self.all_files:
             rel_path = os.path.relpath(file_path, self.file_system_model.project_root)
             if name and name in rel_path and file_path not in self.current_file_names: # Avoid duplicates if already shown as active
                 display_name = self._get_display_path(file_path)
                 yield Completion(rel_path, start_position=start_pos, display=display_name)


    def _complete_symbols(self, name: str) -> Iterable[Completion]:
        """Helper to complete symbols (@@ completion)."""
        if name is None: name = ""
        start_pos = -len(name)
        for symbol in self.symbol_list:
            # Assuming symbol has attributes symbol_name, file_name, symbol_type
            if name in symbol.symbol_name:
                file_name = symbol.file_name                
                display_name = self._get_display_path(file_name)                
                display_text = f"{symbol.symbol_name} ({display_name}/{symbol.symbol_type})"
                completion_text = f"{symbol.symbol_name} ({file_name}/{symbol.symbol_type})"
                yield Completion(completion_text, start_position=start_pos, display=display_text)

    def _get_display_path(self, file_path: str, max_parts: int = 3) -> str:
        """Helper to create a shorter display path."""
        try:
            # Use relative path for display consistency
            rel_path = os.path.relpath(file_path, self.file_system_model.project_root)
            parts = rel_path.split(os.sep)
            if len(parts) > max_parts:
                return os.path.join("...", *parts[-max_parts:])
            return rel_path
        except ValueError: # Handle cases where paths are not relative (e.g., different drives on Windows)
            parts = file_path.split(os.sep)
            if len(parts) > max_parts:
                 return os.path.join("...", *parts[-max_parts:])
            return file_path