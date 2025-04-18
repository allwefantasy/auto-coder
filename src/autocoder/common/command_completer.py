import os
import pydantic
from typing import Callable,Dict,Any # Added import
from pydantic import BaseModel,SkipValidation # Added import
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document

from autocoder import models as models_module # Import models module
from autocoder.common import AutoCoderArgs # Ensure AutoCoderArgs is imported

COMMANDS = {
    "/add_files": {
        "/group": {"/add": "", "/drop": "", "/reset": "", "set": ""},
        "/refresh": {},
    },
    "/designer": {
        "/svg": {},
        "/sd": {},
    },
    "/coding": {"/apply": {}, "/next": {}},
    "/chat": {"/new": {}, 
              "/save": {}, 
              "/copy":{}, 
              "/mcp": {}, 
              "/rag": {}, 
              "/review": {}, 
              "/learn": {},
              "/no_context": {}},
    "/mcp": {
        "/add": "",         
        "/remove": "",
        "/list": "",
        "/list_running": "",
        "/refresh": ""
    },
    "/lib": {
        "/add": "",
        "/remove": "",
        "/list": "",
        "/set-proxy": "",
        "/refresh": "",
        "/get": "",
    },
    "/models": {
        "/add": "",
        "/add_model": "",
        "/remove": "",
        "/list": "",
        "/speed": "",
        "/speed-test": "",
        "/input_price": "",
        "/output_price": "",       
    },
    "/auto": {     
    },
    "/shell": {
        "/chat": "",
    },
    "/active_context": {
        "/list": ""
    }
}


class Tag(pydantic.BaseModel):
    start_tag: str
    content: str
    end_tag: str


class FileSystemModel(pydantic.BaseModel):
    project_root: str
    get_all_file_names_in_project: SkipValidation[Callable]
    get_all_file_in_project: SkipValidation[Callable]
    get_all_dir_names_in_project: SkipValidation[Callable]
    get_all_file_in_project_with_dot: SkipValidation[Callable]
    get_symbol_list: SkipValidation[Callable]

class MemoryConfig(BaseModel):
    """
    A model to encapsulate memory configuration and operations.
    """
    get_memory_func: SkipValidation[Callable]
    save_memory_func: SkipValidation[Callable]

    class Config:
        arbitrary_types_allowed = True

class CommandTextParser:
    def __init__(self, text: str, command: str):
        self.text = text
        self.pos = -1
        self.len = len(text)
        self.is_extracted = False
        self.current_word_start_pos = 0
        self.current_word_end_pos = 0
        self.in_current_sub_command = ""
        self.completions = []
        self.command = command
        self.current_hiararchy = COMMANDS[command]
        self.sub_commands = []
        self.tags = []

    def first_sub_command(self):
        if len(self.sub_commands) == 0:
            return None
        return self.sub_commands[0]

    def last_sub_command(self):
        if len(self.sub_commands) == 0:
            return None
        return self.sub_commands[-1]

    def peek(self) -> str:
        if self.pos + 1 < self.len:
            return self.text[self.pos + 1]
        return None

    def peek2(self) -> str:
        if self.pos + 2 < self.len:
            return self.text[self.pos + 2]
        return None

    def peek3(self) -> str:
        if self.pos + 3 < self.len:
            return self.text[self.pos + 3]
        return None

    def next(self) -> str:
        if self.pos < self.len - 1:
            self.pos += 1
            char = self.text[self.pos]
            return char
        return None

    def consume_blank(self):
        while (
            self.peek() == "\n"
            or self.peek() == " "
            or self.peek() == "\t"
            or self.peek() == "\r"
        ):
            self.next()

    def is_blank(self) -> bool:
        return (
            self.peek() == "\n"
            or self.peek() == " "
            or self.peek() == "\t"
            or self.peek() == "\r"
        )

    def is_sub_command(self) -> bool:
        backup_pos = self.pos
        self.consume_blank()
        try:
            if self.peek() == "/":
                current_sub_command = ""
                while (
                    self.peek() is not None
                    and self.peek() != " "
                    and self.peek() != "\n"
                ):
                    current_sub_command += self.next()

                if current_sub_command.count("/") > 1:
                    self.pos = backup_pos
                    return False
                return True
            return False
        finally:
            self.pos = backup_pos

    def consume_sub_command(self) -> str:
        backup_pos = self.pos
        self.consume_blank()
        current_sub_command = ""
        while self.peek() is not None and self.peek() != " " and self.peek() != "\n":
            current_sub_command += self.next()

        if self.peek() is None:
            self.is_extracted = True
            self.current_word_end_pos = self.pos + 1
            self.current_word_start_pos = self.current_word_end_pos - len(
                current_sub_command
            )
            self.in_current_sub_command = current_sub_command
        else:
            if current_sub_command in self.current_hiararchy:
                self.current_hiararchy = self.current_hiararchy[current_sub_command]
                self.sub_commands.append(current_sub_command)

        return current_sub_command

    def consume_command_value(self) -> str:
        current_word = ""
        while self.peek() is not None:
            v = self.next()
            if v == " ":
                current_word = ""
            else:
                current_word += v
        self.is_extracted = True
        self.current_word_end_pos = self.pos + 1
        self.current_word_start_pos = self.current_word_end_pos - \
            len(current_word)

    def previous(self) -> str:
        if self.pos > 1:
            return self.text[self.pos - 1]
        return None

    def is_start_tag(self) -> bool:
        backup_pos = self.pos
        tag = ""
        try:
            if self.peek() == "<" and self.peek2() != "/":
                while (
                    self.peek() is not None
                    and self.peek() != ">"
                    and not self.is_blank()
                ):
                    tag += self.next()
                if self.peek() == ">":
                    tag += self.next()
                    return True
                else:
                    return False
            return False
        finally:
            self.pos = backup_pos

    def consume_tag(self):
        start_tag = ""
        content = ""
        end_tag = ""

        # consume start tag
        self.current_word_start_pos = self.pos + 1
        while self.peek() is not None and self.peek() != ">" and not self.is_blank():
            start_tag += self.next()
        if self.peek() == ">":
            start_tag += self.next()
        self.current_word_end_pos = self.pos + 1
        tag = Tag(start_tag=start_tag, content=content, end_tag=end_tag)
        self.tags.append(tag)

        # consume content
        self.current_word_start_pos = self.pos + 1
        while self.peek() is not None and not (
            self.peek() == "<" and self.peek2() == "/"
        ):
            content += self.next()

        tag.content = content
        self.current_word_end_pos = self.pos + 1

        # consume end tag
        self.current_word_start_pos = self.pos + 1
        if self.peek() == "<" and self.peek2() == "/":
            while (
                self.peek() is not None and self.peek() != ">" and not self.is_blank()
            ):
                end_tag += self.next()
            if self.peek() == ">":
                end_tag += self.next()
        tag.end_tag = end_tag
        self.current_word_end_pos = self.pos + 1

        # check is finished
        if self.peek() is None:
            self.is_extracted = True

    def consume_coding_value(self) -> str:
        current_word = ""
        while self.peek() is not None and not self.is_start_tag():
            v = self.next()
            if v == " ":
                current_word = ""
            else:
                current_word += v
        if self.peek() is None:
            self.is_extracted = True

        self.current_word_end_pos = self.pos + 1
        self.current_word_start_pos = self.current_word_end_pos - \
            len(current_word)

    def current_word(self) -> str:
        return self.text[self.current_word_start_pos: self.current_word_end_pos]

    def get_current_word(self) -> str:
        return self.current_word()

    def get_sub_commands(self) -> list[str]:
        if self.get_current_word() and not self.get_current_word().startswith("/"):
            return []

        if isinstance(self.current_hiararchy, str):
            return []

        return [item for item in list(self.current_hiararchy.keys()) if item]

    def add_files(self):
        """
        for exmaple:
        /add_files file1 file2 file3
        /add_files /group/abc/cbd /group/abc/bc2
        /add_files /group1 /add xxxxx
        /add_files /group
        /add_files /group /add <groupname>
        /add_files /group /drop <groupname>
        /add_files /group <groupname>,<groupname>
        /add_files /refresh
        """

        while True:
            if self.pos == self.len - 1:
                break
            elif self.is_extracted:
                break
            elif self.is_sub_command():
                self.consume_sub_command()
            else:
                self.consume_command_value()

        return self

    def lib(self):
        """
        for example:
        /lib /add library_name
        /lib /remove library_name
        /lib /list
        /lib /set-proxy proxy_url
        /lib /refresh
        """

        while True:
            if self.pos == self.len - 1:
                break
            elif self.is_extracted:
                break
            elif self.is_sub_command():
                self.consume_sub_command()
            else:
                self.consume_command_value()

        return self

    def coding(self):
        while True:
            if self.pos == self.len - 1:
                break
            elif self.is_extracted:
                break
            elif self.is_sub_command():
                self.consume_sub_command()
            elif self.is_start_tag():
                self.consume_tag()
            else:
                self.consume_coding_value()


class CommandCompleter(Completer):
    def __init__(self, commands, file_system_model: FileSystemModel, memory_model: MemoryConfig):
        self.commands = commands
        self.file_system_model = file_system_model
        self.memory_model = memory_model
        self.all_file_names = file_system_model.get_all_file_names_in_project()
        self.all_files = self.file_system_model.get_all_file_in_project()
        self.all_dir_names = self.file_system_model.get_all_dir_names_in_project()
        self.all_files_with_dot = self.file_system_model.get_all_file_in_project_with_dot()
        self.symbol_list = self.file_system_model.get_symbol_list()
        # Refresh model names if they can change dynamically (optional)
        self.all_model_names = [m['name'] for m in models_module.load_models()]
        self.all_model_names = [m['name'] for m in models_module.load_models()] # Load model names
        self.current_file_names = []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if len(words) > 0:
            if words[0] == "/mode":
                left_word = text[len("/mode"):]
                for mode in ["normal", "auto_detect", "voice_input"]:
                    if mode.startswith(left_word.strip()):
                        yield Completion(mode, start_position=-len(left_word.strip()))

            if words[0] == "/add_files":
                new_text = text[len("/add_files"):]
                parser = CommandTextParser(new_text, words[0])
                parser.add_files()
                current_word = parser.current_word()

                if parser.last_sub_command() == "/refresh":
                    return

                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

                if parser.first_sub_command() == "/group" and (
                    parser.last_sub_command() == "/group"
                    or parser.last_sub_command() == "/drop"
                ):
                    group_names = self.memory_model.memory["current_files"]["groups"].keys()
                    if "," in current_word:
                        current_word = current_word.split(",")[-1]

                    for group_name in group_names:
                        if group_name.startswith(current_word):
                            yield Completion(
                                group_name, start_position=-len(current_word)
                            )

                if parser.first_sub_command() != "/group":
                    if current_word and current_word.startswith("."):
                        for file_name in self.all_files_with_dot:
                            if file_name.startswith(current_word):
                                yield Completion(
                                    file_name, start_position=-
                                    len(current_word)
                                )
                    else:
                        for file_name in self.all_file_names:
                            if file_name.startswith(current_word):
                                yield Completion(
                                    file_name, start_position=-
                                    len(current_word)
                                )
                        for file_name in self.all_files:
                            if current_word and current_word in file_name:
                                yield Completion(
                                    file_name, start_position=-
                                    len(current_word)
                                )            
            elif words[0] == "/remove_files":
                new_words = text[len("/remove_files"):].strip().split(",")

                is_at_space = text[-1] == " "
                last_word = new_words[-2] if len(new_words) > 1 else ""
                current_word = new_words[-1] if new_words else ""

                if is_at_space:
                    last_word = current_word
                    current_word = ""

                # /remove_files /all [cursor] or /remove_files /all p[cursor]
                if not last_word and not current_word:
                    if "/all".startswith(current_word):
                        yield Completion("/all", start_position=-len(current_word))
                    for file_name in self.current_file_names:
                        yield Completion(file_name, start_position=-len(current_word))

                # /remove_files /a[cursor] or /remove_files p[cursor]
                if current_word:
                    if "/all".startswith(current_word):
                        yield Completion("/all", start_position=-len(current_word))
                    for file_name in self.current_file_names:
                        if current_word and current_word in file_name:
                            yield Completion(
                                file_name, start_position=-len(current_word)
                            )
            elif words[0] == "/exclude_dirs":
                new_words = text[len("/exclude_dirs"):].strip().split(",")
                current_word = new_words[-1]

                for file_name in self.all_dir_names:
                    if current_word and current_word in file_name:
                        yield Completion(file_name, start_position=-len(current_word))

            elif words[0] == "/lib":
                new_text = text[len("/lib"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()

                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

                if parser.last_sub_command() in ["/add", "/remove", "/get"]:
                    for lib_name in self.memory_model.memory.get("libs", {}).keys():
                        if lib_name.startswith(current_word):
                            yield Completion(
                                lib_name, start_position=-len(current_word)
                            )
            elif words[0] == "/mcp":
                new_text = text[len("/mcp"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()
                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))
            elif words[0] == "/models":
                new_text = text[len("/models"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()
                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))            

            elif words[0] == "/active_context":
                new_text = text[len("/active_context"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()
                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

            elif words[0] == "/conf":
                new_words = text[len("/conf"):].strip().split()
                is_at_space = text[-1] == " "
                last_word = new_words[-2] if len(new_words) > 1 else ""
                current_word = new_words[-1] if new_words else ""
                completions = []

                if is_at_space:
                    last_word = current_word
                    current_word = ""

                # /conf /drop [curor] or /conf /drop p[cursor]
                if last_word == "/drop":
                    completions = [
                        field_name
                        for field_name in self.memory_model.memory["conf"].keys()
                        if field_name.startswith(current_word)
                    ]
                # /conf [curosr]
                elif not last_word and not current_word:
                    completions = [
                        "/drop"] if "/drop".startswith(current_word) else []
                    completions += [
                        field_name + ":"
                        for field_name in AutoCoderArgs.model_fields.keys()
                        if field_name.startswith(current_word)
                    ]
                # /conf p[cursor]
                elif not last_word and current_word:
                    completions = [
                        "/drop"] if "/drop".startswith(current_word) else []
                    completions += [
                        field_name + ":"
                        for field_name in AutoCoderArgs.model_fields.keys()
                        if field_name.startswith(current_word)
                    ]
                # /conf key:[cursor] or /conf key:v[cursor]
                elif ":" in text: # Check if colon exists anywhere after /conf
                    parts = text[len("/conf"):].strip().split(":", 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value_part = parts[1] # This is the part after the colon

                        # Determine the word being completed (part after colon)
                        # Find the start of the current word after the colon
                        space_pos = value_part.rfind(" ")
                        if space_pos != -1:
                            current_value_word = value_part[space_pos + 1:]
                        else:
                            current_value_word = value_part

                        # Model name completion
                        if "model" in key:
                            for model_name in self.all_model_names:
                                if model_name.startswith(current_value_word):
                                    yield Completion(model_name, start_position=-len(current_value_word))
                            # Prioritize model completion if key matches
                            return # Exit after providing model completions

                        # Boolean completion
                        bool_keys = {name for name, field in AutoCoderArgs.model_fields.items() if field.annotation == bool}
                        if key in bool_keys:
                            if "true".startswith(current_value_word):
                                yield Completion("true", start_position=-len(current_value_word))
                            if "false".startswith(current_value_word):
                                yield Completion("false", start_position=-len(current_value_word))
                            # Prioritize boolean completion if key matches
                            return # Exit after providing boolean completions

                        # Add other value completions based on key if needed here

                        # No specific value completions matched, so no yield from here
                        return # Exit if we were trying value completion

                # Default completion for keys or /drop if no value completion logic was triggered above
                for completion in completions:
                     # Adjust start_position based on whether we are completing key or /drop
                     yield Completion(completion, start_position=-len(current_word))

            elif words[0] in ["/chat", "/coding","/auto"]:
                image_extensions = (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".bmp",
                    ".tiff",
                    ".tif",
                    ".webp",
                    ".svg",
                    ".ico",
                    ".heic",
                    ".heif",
                    ".raw",
                    ".cr2",
                    ".nef",
                    ".arw",
                    ".dng",
                    ".orf",
                    ".rw2",
                    ".pef",
                    ".srw",
                    ".eps",
                    ".ai",
                    ".psd",
                    ".xcf",
                )
                new_text = text[len(words[0]):]
                parser = CommandTextParser(new_text, words[0])

                parser.coding()
                current_word = parser.current_word()

                if len(new_text.strip()) == 0 or new_text.strip() == "/":
                    for command in parser.get_sub_commands():
                        if command.startswith(current_word):
                            yield Completion(command, start_position=-len(current_word))

                all_tags = parser.tags

                if current_word.startswith("@"):
                    name = current_word[1:]
                    target_set = set()

                    for file_name in self.current_file_names:
                        base_file_name = os.path.basename(file_name)
                        if name in base_file_name:
                            target_set.add(base_file_name)
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)
                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name} (in active files)",
                            )

                    for file_name in self.all_file_names:
                        if file_name.startswith(name) and file_name not in target_set:
                            target_set.add(file_name)

                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)

                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name}",
                            )

                    for file_name in self.all_files:
                        if name in file_name and file_name not in target_set:
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)
                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name}",
                            )

                if current_word.startswith("@@"):
                    name = current_word[2:]
                    for symbol in self.symbol_list:
                        if name in symbol.symbol_name:
                            file_name = symbol.file_name
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else symbol.symbol_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)
                            yield Completion(
                                f"{symbol.symbol_name}(location: {relative_path})",
                                start_position=-len(name),
                                display=f"{symbol.symbol_name} ({display_name}/{symbol.symbol_type})",
                            )

                tags = [tag for tag in parser.tags]

                if current_word.startswith("<"):
                    name = current_word[1:]
                    for tag in ["<img>", "</img>"]:
                        if all_tags and all_tags[-1].start_tag == "<img>":
                            if tag.startswith(name):
                                yield Completion(
                                    "</img>", start_position=-len(current_word)
                                )
                        elif tag.startswith(name):
                            yield Completion(tag, start_position=-len(current_word))

                if tags and tags[-1].start_tag == "<img>" and tags[-1].end_tag == "":
                    raw_file_name = tags[0].content
                    file_name = raw_file_name.strip()
                    parent_dir = os.path.dirname(file_name)
                    file_basename = os.path.basename(file_name)
                    search_dir = parent_dir if parent_dir else "."
                    for root, dirs, files in os.walk(search_dir):
                        # 只处理直接子目录
                        if root != search_dir:
                            continue

                        # 补全子目录
                        for dir in dirs:
                            full_path = os.path.join(root, dir)
                            if full_path.startswith(file_name):
                                relative_path = os.path.relpath(
                                    full_path, search_dir)
                                yield Completion(
                                    relative_path,
                                    start_position=-len(file_basename),
                                )

                        # 补全文件
                        for file in files:
                            if file.lower().endswith(
                                image_extensions
                            ) and file.startswith(file_basename):
                                full_path = os.path.join(root, file)
                                relative_path = os.path.relpath(
                                    full_path, search_dir)
                                yield Completion(
                                    relative_path,
                                    start_position=-len(file_basename),
                                )

                        # 只处理一层子目录，然后退出循环
                        break        

            elif not words[0].startswith("/"):                
                image_extensions = (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".bmp",
                    ".tiff",
                    ".tif",
                    ".webp",
                    ".svg",
                    ".ico",
                    ".heic",
                    ".heif",
                    ".raw",
                    ".cr2",
                    ".nef",
                    ".arw",
                    ".dng",
                    ".orf",
                    ".rw2",
                    ".pef",
                    ".srw",
                    ".eps",
                    ".ai",
                    ".psd",
                    ".xcf",
                )
                new_text = text
                parser = CommandTextParser(new_text, "/auto")

                parser.coding()
                current_word = parser.current_word()

                if len(new_text.strip()) == 0 or new_text.strip() == "/":
                    for command in parser.get_sub_commands():
                        if command.startswith(current_word):
                            yield Completion(command, start_position=-len(current_word))

                all_tags = parser.tags

                if current_word.startswith("@"):
                    name = current_word[1:]
                    target_set = set()

                    for file_name in self.current_file_names:
                        base_file_name = os.path.basename(file_name)
                        if name in base_file_name:
                            target_set.add(base_file_name)
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)
                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name} (in active files)",
                            )

                    for file_name in self.all_file_names:
                        if file_name.startswith(name) and file_name not in target_set:
                            target_set.add(file_name)

                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)

                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name}",
                            )

                    for file_name in self.all_files:
                        if name in file_name and file_name not in target_set:
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)
                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name}",
                            )

                if current_word.startswith("@@"):
                    name = current_word[2:]
                    for symbol in self.symbol_list:
                        if name in symbol.symbol_name:
                            file_name = symbol.file_name
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else symbol.symbol_name
                            )
                            relative_path = os.path.relpath(
                                file_name, self.file_system_model.project_root)
                            yield Completion(
                                f"{symbol.symbol_name}(location: {relative_path})",
                                start_position=-len(name),
                                display=f"{symbol.symbol_name} ({display_name}/{symbol.symbol_type})",
                            )

                tags = [tag for tag in parser.tags]

                if current_word.startswith("<"):
                    name = current_word[1:]
                    for tag in ["<img>", "</img>"]:
                        if all_tags and all_tags[-1].start_tag == "<img>":
                            if tag.startswith(name):
                                yield Completion(
                                    "</img>", start_position=-len(current_word)
                                )
                        elif tag.startswith(name):
                            yield Completion(tag, start_position=-len(current_word))

                if tags and tags[-1].start_tag == "<img>" and tags[-1].end_tag == "":
                    raw_file_name = tags[0].content
                    file_name = raw_file_name.strip()
                    parent_dir = os.path.dirname(file_name)
                    file_basename = os.path.basename(file_name)
                    search_dir = parent_dir if parent_dir else "."
                    for root, dirs, files in os.walk(search_dir):
                        # 只处理直接子目录
                        if root != search_dir:
                            continue

                        # 补全子目录
                        for dir in dirs:
                            full_path = os.path.join(root, dir)
                            if full_path.startswith(file_name):
                                relative_path = os.path.relpath(
                                    full_path, search_dir)
                                yield Completion(
                                    relative_path,
                                    start_position=-len(file_basename),
                                )

                        # 补全文件
                        for file in files:
                            if file.lower().endswith(
                                image_extensions
                            ) and file.startswith(file_basename):
                                full_path = os.path.join(root, file)
                                relative_path = os.path.relpath(
                                    full_path, search_dir)
                                yield Completion(
                                    relative_path,
                                    start_position=-len(file_basename),
                                )

                        # 只处理一层子目录，然后退出循环
                        break
            else:
                for command in self.commands:
                    if command.startswith(text):
                        yield Completion(command, start_position=-len(text))

        else:
            for command in self.commands:
                if command.startswith(text):
                    yield Completion(command, start_position=-len(text))

    def update_current_files(self, files):
        self.current_file_names = [f for f in files]


    def refresh_files(self):
        self.all_file_names = self.file_system_model.get_all_file_names_in_project()
        self.all_files = self.file_system_model.get_all_file_in_project()
        self.all_dir_names = self.file_system_model.get_all_dir_names_in_project()
        self.all_files_with_dot = self.file_system_model.get_all_file_in_project_with_dot()
        self.symbol_list = self.file_system_model.get_symbol_list()