from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document
import pydantic
import os

COMMANDS = {
    "/add_files": {"/group": {"/add": "", "/drop": ""}, "/refresh": {}},
    "/coding": {},
    "/chat": {},
    "/lib": {
        "/add": "",
        "/remove": "",
        "/list": "",
        "/set-proxy": "",
        "/refresh": "",
        "/get": "",
    },
}


class Tag(pydantic.BaseModel):
    start_tag: str
    content: str
    end_tag: str


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
        self.current_word_start_pos = self.current_word_end_pos - len(current_word)

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
        self.current_word_start_pos = self.current_word_end_pos - len(current_word)

    def current_word(self) -> str:
        return self.text[self.current_word_start_pos : self.current_word_end_pos]

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
