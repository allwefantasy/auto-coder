import byzerllm

@byzerllm.prompt()
def generate_shell_script(user_input: str) -> str:
    """
    根据用户的输入生成一个 shell 脚本。
    
    用户输入: {{ user_input }}
    
    请生成一个适当的 shell 脚本来执行用户的请求。确保脚本是安全的，并且可以在 bash shell 中运行。
    脚本应该以 #!/bin/bash 开头，并包含必要的注释来解释每个步骤。
    """

def generate_shell_script(user_input: str, llm: byzerllm.ByzerLLM) -> str:
    result = generate_shell_script.with_llm(llm).run(user_input=user_input)
    return result