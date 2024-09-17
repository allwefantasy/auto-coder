import byzerllm
from byzerllm.utils.client import code_utils
from autocoder.common import detect_env


@byzerllm.prompt()
def _generate_shell_script(user_input: str) -> str:
    """
    环境信息如下:

    操作系统: {{ env_info.os_name }} {{ env_info.os_version }}
    Python版本: {{ env_info.python_version }}
    {%- if env_info.conda_env %}
    Conda环境: {{ env_info.conda_env }}
    {%- endif %}
    {%- if env_info.virtualenv %}
    虚拟环境: {{ env_info.virtualenv }}
    {%- endif %}
    {%- if env_info.has_bash %}
    支持Bash
    {%- else %}
    不支持Bash
    {%- endif %}

    根据用户的输入以及当前的操作系统生成合适的 shell 脚本。

    用户输入: {{ user_input }}

    请生成一个适当的 shell 脚本来执行用户的请求。确保脚本是安全的，并且可以在操作系统支持的 shell 中运行。
    脚本应该包含必要的注释来解释每个步骤。
    脚本内容请用如下方式返回：

    ```shell    
    # 你的 shell 脚本内容
    ```
    """
    return {
        "env_info": detect_env()
    }


def generate_shell_script(user_input: str, llm: byzerllm.ByzerLLM) -> str:
    result = _generate_shell_script.with_llm(llm).run(user_input=user_input)
    code = code_utils.extract_code(result)[0][1]
    return code
