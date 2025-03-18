import byzerllm
from byzerllm.utils.client import code_utils
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common import detect_env,AutoCoderArgs
from autocoder.common import shells
from autocoder.common.printer import Printer
from typing import Dict,Union

@byzerllm.prompt()
def _generate_shell_script(user_input: str) -> str:
    """
    环境信息如下:

    操作系统: {{ env_info.os_name }} {{ env_info.os_version }}
    操作系统发行版: {{ os_distribution }}
    Python版本: {{ env_info.python_version }}
    终端类型: {{ env_info.shell_type }}
    终端编码: {{ env_info.shell_encoding }}
    当前用户: {{ current_user }}
    
    {%- if shell_type %}
    脚本类型：{{ shell_type }}
    {%- endif %}

    {%- if env_info.conda_env %}
    Conda环境: {{ env_info.conda_env }}
    {%- endif %}
    {%- if env_info.virtualenv %}
    虚拟环境: {{ env_info.virtualenv }}
    {%- endif %}    

    根据用户的输入以及当前的操作系统和终端类型以及脚本类型生成脚本，
    注意只能生成一个shell脚本，不要生成多个。    

    用户输入: {{ user_input }}

    请生成一个适当的脚本来执行用户的请求。确保脚本是安全的,并且可以在当前Shell环境中运行。
    脚本应该包含必要的注释来解释每个步骤。
    脚本内容请用如下方式返回:

    ```script    
    # 你的 script 脚本内容
    ```
    """
    env_info = detect_env() 
    shell_type = "bash"
    if shells.is_running_in_cmd():
        shell_type = "cmd"
    elif shells.is_running_in_powershell():
        shell_type = "powershell"
    return {
        "env_info": env_info,
        "shell_type": shell_type,
        "shell_encoding": shells.get_terminal_encoding(),
        "os_distribution": shells.get_os_distribution(),
        "current_user": shells.get_current_username()
    }


def generate_shell_script(args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM,byzerllm.SimpleByzerLLM]) -> str:
    # 获取 prompt 内容
    prompt = _generate_shell_script.prompt(user_input=args.query)
    if llm.get_sub_client("chat_model"):
        shell_llm = llm.get_sub_client("chat_model")                
    else:
        shell_llm = llm
    
    # 构造对话上下文
    conversations = [{"role": "user", "content": prompt}]
    
    # 使用 stream_out 进行输出
    printer = Printer()
    title = printer.get_message_from_key("generating_shell_script")
    result, _ = stream_out(
        shell_llm.stream_chat_oai(conversations=conversations, delta_mode=True),
        model_name=llm.default_model_name,
        title=title,
        args=args       
    )
    
    # 提取代码块
    code = code_utils.extract_code(result)[-1][1]
    return code
