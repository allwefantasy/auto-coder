from autocoder.common.command_file_manager.manager import CommandManager

command_manager = CommandManager()

rendered_content = command_manager.read_command_file_with_render("tdd/hello.md", {"name": "威廉"})

print(rendered_content)