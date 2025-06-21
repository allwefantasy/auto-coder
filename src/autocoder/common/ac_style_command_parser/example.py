from autocoder.common.ac_style_command_parser.parser import CommandParser

p = CommandParser()

result = p.parse('/command "tdd/hello.md" name="威廉"')

print(result)