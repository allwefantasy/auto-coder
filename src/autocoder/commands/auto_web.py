import os
import time
import json
from typing import Dict, List, Any, Optional, Union
import pydantic
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

import byzerllm
from autocoder.common import AutoCoderArgs
from autocoder.common.computer_use import ComputerUse
from autocoder.common.printer import Printer
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.result_manager import ResultManager
from autocoder.common import git_utils
from autocoder.common.global_cancel import global_cancel
from byzerllm.utils.client import code_utils
from autocoder.common import detect_env
from autocoder.common import shells


class WebAction(pydantic.BaseModel):
    """网页自动化操作"""
    action: str
    parameters: Dict[str, Any] = {}
    description: Optional[str] = None
    expected_outcome: Optional[str] = None  # 新增: 期望的操作结果


class ActionResult(pydantic.BaseModel):
    """Action执行结果"""
    success: bool
    action: WebAction
    screenshot_path: Optional[str] = None
    result: Dict[str, Any] = {}
    error: Optional[str] = None


class AutoWebRequest(pydantic.BaseModel):
    """自动化网页操作请求"""
    user_input: str
    context: Optional[str] = None
    screenshot_path: Optional[str] = None


class AutoWebResponse(pydantic.BaseModel):
    """自动化网页操作响应"""
    actions: List[WebAction] = []
    explanation: Optional[str] = None
    additional_info: Optional[str] = None
    suggested_next_steps: Optional[List[str]] = None
    overall_status: Optional[str] = None  # 新增: 整体任务状态


class AutoWebTuner:
    """
    基于大模型的网页自动化工具

    该类使用ComputerUse工具集实现浏览器操作，从用户指令中自动解析需要执行的操作，
    并生成详细的执行步骤，验证每一步执行结果，最后执行并返回结果。
    """

    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        """
        初始化

        Args:
            llm: 用于分析和生成操作的大语言模型
            args: 自动编码器参数
        """
        self.llm = llm
        self.args = args
        self.printer = Printer()

        # 初始化ComputerUse工具
        self.computer = ComputerUse(llm=llm, args=args)

        # 记录执行历史
        self.execution_history = []

        self.init_request = None
        self.current_plan = None

        self.current_action = None
        self.current_action_result = None

    @byzerllm.prompt()
    def _guide_readme(self) -> str:
        """        
        <guide>
        1. 在使用chrome浏览器的时候,如果在某个网页需要进行登录等动作时，请使用 ask_user 函数请求用户帮你登录，然后你再做之后的动作。
        </guide>
        """

    @byzerllm.prompt()
    def _command_readme(self) -> str:
        '''
        你有如下函数可供使用：

        <commands>

        <command>
        <name>screenshot</name>
        <description>
          截取当前屏幕并保存为图片。可以用来获取当前屏幕状态，为后续的元素检测和操作提供基础。
        </description>
        <usage>
         该方法可以接受一个可选的 filename 参数，用于指定保存的文件名。
         如果不指定，会自动生成一个包含时间戳的文件名。

         使用例子：
         screenshot()  # 使用自动生成的文件名
         screenshot(filename="my_screenshot.png")  # 使用指定的文件名

         返回值：
         保存的截图文件路径
        </usage>
        </command>

        <command>
        <name>detect</name>
        <description>
          分析图片，检测其中的各种界面元素（如按钮、输入框、链接等）并返回它们的位置和描述。
          对于需要点击或与特定界面元素交互的场景非常有用。
        </description>
        <usage>
         该方法需要一个image_path参数，通常是通过 screenshot() 函数获取的截图。

         使用例子：
         detect(image_path="screenshot.png")

         返回值：
         JSON格式的检测结果，包含检测到的界面元素列表及其边界框坐标和描述：
         {
             "objects": [
                 {
                     "type": "button",
                     "bounding_box": [x1, y1, x2, y2],
                     "text": "登录按钮"
                 },
                 ...
             ]
         }
        </usage>
        </command>

        <command>
        <name>click</name>
        <description>
          在指定坐标处点击鼠标。适用于已知元素坐标的场景。
        </description>
        <usage>
         该方法需要以下参数：
         1. x: 点击位置的X坐标
         2. y: 点击位置的Y坐标
         3. button (可选): 使用哪个鼠标按钮，可以是'left'(默认),'right'或'middle'
         4. clicks (可选): 点击次数，默认为1

         使用例子：
         click(x=100, y=200)  # 在(100,200)处左键单击
         click(x=100, y=200, button='right')  # 右键点击
         click(x=100, y=200, clicks=2)  # 双击
        </usage>
        </command>

        <command>
        <name>find_and_click</name>
        <description>
          查找并点击符合描述的界面元素。适用于不知道确切坐标，但知道元素描述的情况。
          内部会先截取屏幕图像，然后使用视觉模型查找元素，最后点击找到的元素中心位置。
        </description>
        <usage>
         该方法需要以下参数：
         1. element_desc: 元素的文本描述，例如"登录按钮"、"搜索框"等
         2. image_path: 图片路径，如果为None则自动截图

         使用例子：
         find_and_click(element_desc="登录按钮")  # 自动截图并查找点击
         find_and_click(image_path="screenshot.png", element_desc="提交按钮")

         返回值：
         布尔值，表示是否成功找到并点击了元素
        </usage>
        </command>

        <command>
        <name>type</name>
        <description>
          模拟键盘输入文本。适用于需要在输入框中输入内容的场景。
        </description>
        <usage>
         该方法需要以下参数：
         1. text: 要输入的文本内容
         2. interval (可选): 每个字符之间的时间间隔，默认为0.05秒

         使用例子：
         type(text="Hello World")
         type(text="慢速输入", interval=0.2)  # 较慢的输入速度
        </usage>
        </command>

        <command>
        <name>press</name>
        <description>
          按下指定的键盘按键
        </description>
        <usage>
         该方法需要一个key参数，支持数组和字符串。如果是字符串相当于直接输入该字符串，如果是数组相当于按下组合键。

         支持的键包括:
         - 'enter', 'return'
         - 'tab'
         - 'space'
         - 'backspace'
         - 'esc', 'escape'
         - 方向键: 'up', 'down', 'left', 'right'
         - 功能键: 'f1', 'f2', ..., 'f12'
         - 组合键: 'ctrl+c', 'ctrl+v', 'alt+tab'等

         使用例子：
         press(key="text")  # 输入 text 文本
         press(key=["enter"])  # 按回车键
         press(key=["ctrl", "a"])  # 全选
         press(key=["alt", "tab"])  # 切换窗口
        </usage>
        </command>

        <command>
        <name>drag</name>
        <description>
          从一个位置拖动到另一个位置。适用于拖拽操作，如滑块、拖动文件等。
        </description>
        <usage>
         该方法需要以下参数：
         1. start_x: 起始点X坐标
         2. start_y: 起始点Y坐标
         3. end_x: 终点X坐标
         4. end_y: 终点Y坐标
         5. duration (可选): 拖动持续时间，默认0.5秒

         使用例子：
         drag(start_x=100, start_y=200, end_x=300, end_y=400)
         drag(start_x=100, start_y=200, end_x=300, end_y=400, duration=1)  # 较慢的拖动
        </usage>
        </command>

        <command>
        <name>scroll</name>
        <description>
          在当前鼠标位置滚动滚轮。适用于网页滚动等场景。
        </description>
        <usage>
         该方法需要以下参数：
         1. clicks: 滚动的单位数量，正数向下滚动，负数向上滚动
         2. x (可选): 滚动时鼠标的X坐标，默认为当前位置
         3. y (可选): 滚动时鼠标的Y坐标，默认为当前位置

         使用例子：
         scroll(clicks=10)  # 向下滚动10个单位
         scroll(clicks=-5)  # 向上滚动5个单位
         scroll(clicks=10, x=500, y=500)  # 在指定位置滚动
        </usage>
        </command>

        <command>
        <name>extract_text</name>
        <description>
          从屏幕截图中提取文本内容。适用于需要读取屏幕上文本信息的场景。
        </description>
        <usage>
         该方法需要以下参数：
         1. image_path: 图片路径，如果为None则自动截图
         2. region (可选): 提取区域[x1,y1,x2,y2]，默认为整个图片

         使用例子：
         extract_text()  # 自动截图并提取所有文本
         extract_text(image_path="screenshot.png")  # 从指定图片提取文本
         extract_text(image_path="screenshot.png", region=[100,100,300,200])  # 从指定区域提取

         返回值：
         提取到的文本内容
        </usage>
        </command>

        <command>
        <name>wait_loading</name>
        <description>
        给定一个目标，等待目标出现。
        </description>
        <usage>
         该方法需要以下参数：           
         1. target: 执行完动作后，用户期待看到的东西。

         使用例子：
         wait_loading(
             target="搜索列表页面"
         )

         该函数无返回。

         此功能特别适用于执行完点击等需要等待一会的函数，避免操作完后立马就校验结果但系统还处于加载状态而导致误判。
        </usage>
        </command>

        <command>
        <name>ask_user</name>
        <description>
          向用户提问并获取回答。适用于需要用户输入信息或确认的场景。
        </description>
        <usage>
         该方法需要一个question参数，指定要向用户提出的问题。

         使用例子：
         ask_user(question="请输入您的用户名")
         ask_user(question="是否继续操作？(yes/no)")

         返回值：
         用户输入的文本内容
        </usage>
        </command>

        <command>
        <name>response_user</name>
        <description>
          向用户显示消息。适用于需要向用户提供反馈或信息的场景，但不需要用户响应。
        </description>
        <usage>
         该方法需要一个response参数，指定要向用户显示的消息内容。

         使用例子：
         response_user(response="正在搜索网页...")
         response_user(response="操作完成，请等待页面加载")

         该方法不等待用户输入，只是显示信息。
        </usage>
        </command>

        <command>
        <name>open_browser</name>
        <description>
          打开指定的浏览器并
        </description>
        <usage>
         该方法支持以下参数：
         1. browser_name: 浏览器名称，默认为"chrome"，也支持"firefox"和"edge"等         

         推荐统一使用chrome浏览器。

         使用例子：
         open_browser(browser_name="chrome")
         open_browser(browser_name="firefox")
        </usage>
        </command>

        <command>
        <name>focus_app</name>
        <description>
          查找并聚焦指定的应用程序窗口。
          这在需要确保某个应用程序处于活跃状态后才能进行后续操作时非常有用。
        </description>
        <usage>
          该方法需要一个app_name参数，表示要聚焦的应用程序名称或窗口标题的一部分。
          可选的retry_count参数表示重试次数，默认为3。

          使用例子：
          focus_app(app_name="Chrome")  # 聚焦Chrome浏览器
          focus_app(app_name="记事本", retry_count=5)  # 聚焦记事本，并增加重试次数

          返回值：
          布尔值，表示是否成功聚焦应用
        </usage>
        </command>
        </commands>
        '''

    @byzerllm.prompt()
    def analyze_task(self, request: AutoWebRequest) -> str:
        """
        图片是当前屏幕截图。
        {{ screenshot }}

        我是一个专业的网页自动化助手。我能帮助用户执行各种网页操作，包括点击按钮、输入文本、导航网页等。

        当前用户环境信息如下:
        <os_info>
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
        </os_info>

        你有如下函数可供使用：
        {{ command_readme }}

        {{ guide_readme }}

        用户请求:
        {{ request.user_input }}

        {% if request.context %}
        上下文信息:
        {{ request.context }}
        {% endif %}

        请我为用户制定一个详细的自动化操作计划，包括每一步需要执行的具体动作。

        对于每个操作，我需要提供:
        1. 要执行的动作类型
        2. 动作的参数（如坐标、文本内容等）
        3. 动作的目的描述
        4. 期望的结果
        5. 如果需要用户交互，请使用ask_user或response_user操作。

        我的回答必须以下面的JSON格式返回:
        ```json
        {
            "explanation": "对整体任务的简要解释",
            "actions": [
                {
                    "action": "动作类型",
                    "parameters": {
                        "参数1": "值1",
                        "参数2": "值2"
                    },
                    "description": "这个动作的目的描述",
                    "expected_outcome": "执行此动作后预期看到的结果"
                },
                {
                    "action": "第二个动作",
                    ...
                }
            ],
            "additional_info": "任何额外信息或建议",
            "suggested_next_steps": ["完成当前任务后可能的后续步骤1", "后续步骤2"]
        }
        ```
        """
        env_info = detect_env()
        shell_type = "bash"
        if shells.is_running_in_cmd():
            shell_type = "cmd"
        elif shells.is_running_in_powershell():
            shell_type = "powershell"

        data = {
            "command_readme": self._command_readme.prompt(),
            "user_input": request.user_input,
            "available_commands": self._command_readme.prompt(),
            "env_info": env_info,
            "shell_type": shell_type,
            "shell_encoding": shells.get_terminal_encoding(),
            "os_distribution": shells.get_os_distribution(),
            "current_user": shells.get_current_username(),
            "guide_readme": self._guide_readme.prompt()
        }
        if request.screenshot_path:
            image = byzerllm.Image.load_image_from_path(
                request.screenshot_path)
            data["screenshot"] = image
        return {"request": request, **data}

    @byzerllm.prompt()
    def verify_action_result(self) -> str:
        """
        图片是当前屏幕截图。
        {{ image }}

        你有如下函数可供使用：
        {{ command_readme }}

        {{ guide_readme }}

        用户请求:
        {{ request.user_input }}


        当前的规划是:
        ```json
        {{ plan }}
        ```
        
        执行历史:
        {% for record in execution_history %}
        步骤 {{ record.step }}:
        - 动作: {{ record.action.action }}
        - 描述: {{ record.action.description or "无描述" }}
        - 结果: {{ "成功" if record.result.success else "失败" }}
        {% if not record.result.success and record.result.error %}
        - 错误: {{ record.result.error }}
        {% endif %}
        {% if record.verification %}
        - 验证: {{ "通过" if record.verification.success else "未通过" }}
        - 原因: {{ record.verification.reason }}
        {% endif %}

        {% endfor %}

        你当前执行的最后一个操作为:
        ```json
        {{ action_json }}
        ```

        该操作的期望结果:
        {{ action.expected_outcome }}

        操作的实际执行结果:
        ```json
        {{ result_json }}
        ```        

        请根据前面的信息以及截图，判断当前操作是否达成了预期效果。                

        返回以下JSON格式的验证结果:
        ```json
        {
            "success": true或false,                  // 操作是否成功达成预期效果
            "analysis": "详细分析当前屏幕和操作结果",  // 分析当前屏幕和操作结果
            "reason": "成功或失败的原因",             // 操作成功或失败的原因
            "suggestion": "如果失败，建议的下一步操作"  // 如果操作失败，建议的下一步操作
        }
        ```

        如果你觉得需要调整自动执行计划，请将success设置为false，并提供详细的分析和建议,触发后续的执行计划的修改。
        """
        screenshot_path = self.current_action_result.screenshot_path
        action = self.current_action
        result = self.current_action_result.result
        plan = self.current_plan.model_dump()
        image = byzerllm.Image.load_image_from_path(screenshot_path)
        return {
            "action_json": json.dumps(action.model_dump(), ensure_ascii=False, indent=2),
            "action": action,
            "result_json": json.dumps(result, ensure_ascii=False, indent=2),
            "image": image,
            "plan": plan,
            "execution_history": self.execution_history,
            "request": self.init_request
        }

    @byzerllm.prompt()
    def analyze_execution_result(self) -> str:
        """
        {{ screenshot }}

        图片是当前屏幕截图。

        当前用户环境信息如下:
        <os_info>
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
        </os_info>

        你有如下函数可供使用：
        {{ command_readme }}

        {{ guide_readme }}

        我需要分析当前的网页自动化执行情况并确定后续步骤。        

        当前的自动化计划是:
        ```json
        {{ plan }}
        ```

        执行历史:
        {% for record in execution_history %}
        步骤 {{ record.step }}:
        - 动作: {{ record.action.action }}
        - 描述: {{ record.action.description or "无描述" }}
        - 结果: {{ "成功" if record.result.success else "失败" }}
        {% if not record.result.success and record.result.error %}
        - 错误: {{ record.result.error }}
        {% endif %}
        {% if record.verification %}
        - 验证: {{ "通过" if record.verification.success else "未通过" }}
        - 原因: {{ record.verification.reason }}
        {% endif %}

        {% endfor %}

        原始任务:
        {{ task.user_input }}

        请根据当前屏幕状态和执行历史，分析任务完成情况并确定下一步骤。如果任务已经完成，请明确说明。如果任务未完成，请提供新的操作计划。
        请以JSON格式返回结果:
        ```json
        {
            "completed": true或false,
            "current_status": "任务当前状态描述",
            "analysis": "详细分析",
            "actions": [
                {
                    "action": "动作类型",
                    "parameters": {
                        "参数1": "值1",
                        "参数2": "值2"
                    },
                    "description": "这个动作的目的描述",
                    "expected_outcome": "执行此动作后预期看到的结果"
                }
            ]
        }
        ```
        """
        screenshot_path = self.computer.screenshot()
        plan = self.current_plan.model_dump()
        image = byzerllm.Image.load_image_from_path(screenshot_path)
        data = {
            "env_info": detect_env(),
            "shell_type": "bash",
            "shell_encoding": shells.get_terminal_encoding(),
            "os_distribution": shells.get_os_distribution(),
            "current_user": shells.get_current_username(),
            "command_readme": self._command_readme.prompt(),
            "guide_readme": self._guide_readme.prompt(),
            "plan": plan
        }
        if screenshot_path:
            image = byzerllm.Image.load_image_from_path(screenshot_path)
            data["screenshot"] = image
        return {"task": self.init_request, "execution_history": self.execution_history, **data}

    def execute_action(self, action: WebAction) -> ActionResult:
        """
        执行单个网页自动化操作

        Args:
            action: 要执行的操作

        Returns:
            操作执行结果
        """                
        self.printer.print_in_terminal(
            "executing_web_action",
            style="blue",
            action=action.action,
            description=action.description or ""
        )

        try:            
            # 构建工作流步骤
            step = {
                "action": action.action,
                **action.parameters
            }

            # 执行步骤并获取结果
            step_results = self.computer.run_workflow([step])
                            
            # 执行后截图
            screenshot_path = self.computer.screenshot(
                f"after_{action.action}_{int(time.time())}.png")

            if step_results and len(step_results) > 0:
                result = step_results[0]
                return ActionResult(
                    success=result.get("success", True),
                    action=action,
                    screenshot_path=screenshot_path,
                    result=result
                )
            else:
                return ActionResult(
                    success=False,
                    action=action,
                    screenshot_path=screenshot_path,
                    error="执行步骤返回空结果"
                )

        except Exception as e:
            logger.error(f"执行操作 {action.action} 时出错: {str(e)}")
            # 尝试截图记录错误状态
            try:
                screenshot_path = self.computer.screenshot(
                    f"error_{action.action}_{int(time.time())}.png")
            except:
                screenshot_path = None

            return ActionResult(
                success=False,
                action=action,
                screenshot_path=screenshot_path,
                error=str(e)
            )

    def run_adaptive_flow(self, request: AutoWebRequest, max_iterations: int = 1000, debug: bool = False) -> AutoWebResponse:
        """
        运行自适应的网页自动化流程

        Args:
            request: 自动化请求
            max_iterations: 最大迭代次数
            debug: 是否开启调试模式，设为True时每一步会要求用户确认

        Returns:
            操作响应
        """
        console = Console()
        self.printer.print_in_terminal("auto_web_analyzing", style="blue")

        # 获取初始截图
        if not request.screenshot_path:
            screenshot_path = self.computer.screenshot()
            request.screenshot_path = screenshot_path

        # 记录执行历史
        self.execution_history = []
        self.init_request = request
        # 添加时间统计
        start_time = time.time()

        # 使用LLM分析任务并生成操作计划
        logger.info(f"开始分析任务: '{request.user_input}'")
        console.print("正在分析任务，请稍候...", style="italic blue")
        analysis = self.analyze_task.with_llm(self.llm).run(request)        
        logger.info(f"LLM分析任务结果: {analysis}")

        # 打印LLM分析任务的耗时
        analysis_time = time.time() - start_time
        logger.info(f"任务分析完成，LLM耗时: {analysis_time:.2f}s")
        console.print(f"任务分析完成，LLM耗时: {analysis_time:.2f}s", style="green")

        try:
            # 解析JSON结果
            analysis_json = code_utils.extract_code(analysis)[-1][1]
            plan_dict = json.loads(analysis_json)
            logger.debug(
                f"解析后的操作计划: {json.dumps(plan_dict, ensure_ascii=False, indent=2)}")

            # 转换为AutoWebResponse对象
            plan = AutoWebResponse(
                explanation=plan_dict.get("explanation", ""),
                actions=[WebAction.model_validate(
                    a) for a in plan_dict.get("actions", [])],
                additional_info=plan_dict.get("additional_info", ""),
                suggested_next_steps=plan_dict.get("suggested_next_steps", []),
                overall_status="in_progress"
            )
            self.current_plan = plan

            logger.info(f"生成的操作计划包含 {len(plan.actions)} 个步骤")
            for i, action in enumerate(plan.actions):
                logger.info(
                    f"步骤 {i+1}: {action.action} - {action.description}")

            self.printer.print_in_terminal("auto_web_analyzed", style="green")
            console.print(Panel(
                Text(plan.explanation, style="italic"),
                title="📋 自动化计划",
                border_style="blue"
            ))

        except Exception as e:
            logger.error(f"解析LLM响应失败: {str(e)}")
            return AutoWebResponse(
                explanation=f"无法解析LLM响应: {str(e)}",
                overall_status="failed"
            )

        # 开始执行操作
        iterations = 0
        while iterations < max_iterations:
            iterations += 1
            logger.info(f"开始执行迭代 {iterations}/{max_iterations}")

            # 检查是否需要取消操作
            global_cancel.check_and_raise(token=self.args.event_file)

            # 如果没有更多操作，认为任务完成
            if not plan.actions:
                logger.info("没有更多操作，任务完成")
                console.print(Panel(
                    Text(plan.explanation or "任务完成", style="green"),
                    title="✅ 完成",
                    border_style="green"
                ))
                plan.overall_status = "completed"
                return plan

            # 执行当前计划中的第一个操作
            action = plan.actions[0]
            logger.info(f"准备执行动作: {action.action}")
            logger.info(f"动作描述: {action.description}")
            logger.info(
                f"动作参数: {json.dumps(action.parameters, ensure_ascii=False)}")

            self.printer.print_in_terminal(
                "executing_step",
                style="blue",
                step=iterations,
                description=action.description or action.action
            )

            # 调试模式：如果开启调试，在每一步询问用户是否继续
            if debug:
                question = f"是否执行步骤 {iterations}: {action.action} - {action.description}? (yes/no/quit)"
                answer = self.computer.ask_user(question)

                if answer.lower() == "quit":
                    logger.info("用户选择退出调试模式")
                    return AutoWebResponse(
                        explanation="用户在调试模式中选择退出",
                        overall_status="cancelled",
                        actions=[]
                    )
                elif answer.lower() != "yes":
                    # 用户选择跳过当前步骤
                    logger.info(f"用户选择跳过步骤: {action.action}")
                    plan.actions = plan.actions[1:]
                    continue

                logger.info("用户确认执行当前步骤")

            # 执行操作
            logger.info(f"开始执行动作: {action.action}")
            action_start = time.time()
            self.current_action = action
            action_result = self.execute_action(action)
            self.current_action_result = action_result
            action_time = time.time() - action_start
            logger.info(f"动作执行完成，耗时: {action_time:.2f}s")
            logger.info(f"执行结果: {'成功' if action_result.success else '失败'}")

            if action_result.error:
                logger.error(f"执行错误: {action_result.error}")

            # 验证结果
            if action_result.result.get("should_verify", True):
                logger.info("开始验证执行结果")
                verification_start = time.time()
                verification_result = self.verify_action_result.with_llm(self.llm).run()
                verification_time = time.time() - verification_start
                logger.info(f"结果验证完成，LLM耗时: {verification_time:.2f}s")
                logger.debug(f"验证结果: {verification_result}")

                console.print(
                    f"结果验证完成，LLM耗时: {verification_time:.2f}s", style="cyan")

                try:
                    verification_json = code_utils.extract_code(
                        verification_result)[-1][1]
                    verification = json.loads(verification_json)
                    logger.info(
                        f"验证结果: {'成功' if verification.get('success', False) else '失败'}")
                    if 'reason' in verification:
                        logger.info(f"验证理由: {verification['reason']}")
                except Exception as e:
                    logger.error(f"解析验证结果失败: {str(e)}")
                    verification = {"success": False,
                                    "reason": f"验证结果解析失败: {str(e)}"}
            else:
                verification = {"success": True, "reason": "验证成功"}

            # 记录执行历史
            execution_record = {
                "step": iterations,
                "action": action.model_dump(),
                "result": action_result.model_dump(exclude={"action"}),
                "verification": verification
            }
            self.execution_history.append(execution_record)
            logger.debug(f"已添加执行记录 #{iterations}")

            # 如果验证失败，需要重新规划
            if not verification.get("success", False):
                logger.info(f"验证失败: {verification.get('reason', '未知原因')}")
                self.printer.print_in_terminal(
                    "action_verification_failed",
                    style="yellow",
                    action=action.action,
                    reason=verification.get("reason", "未知原因")
                )

                # 基于执行历史和当前状态进行分析
                logger.info("开始重新规划")
                analysis_start = time.time()
                analysis_result = self.analyze_execution_result.with_llm(self.llm).run()
                analysis_time = time.time() - analysis_start
                logger.info(f"重新规划完成，LLM耗时: {analysis_time:.2f}s")
                logger.debug(f"重新规划结果: {analysis_result}")

                console.print(
                    f"重新规划完成，LLM耗时: {analysis_time:.2f}s", style="magenta")

                try:
                    # 解析分析结果
                    analysis_json = code_utils.extract_code(
                        analysis_result)[-1][1]
                    new_plan = json.loads(analysis_json)
                    logger.debug(
                        f"新计划: {json.dumps(new_plan, ensure_ascii=False, indent=2)}")

                    # 更新计划
                    if new_plan.get("completed", False):
                        # 任务已完成
                        logger.info("分析结果: 任务已完成")
                        console.print(Panel(
                            Text(new_plan.get("analysis", "任务已完成"), style="green"),
                            title="✅ 完成",
                            border_style="green"
                        ))
                        return AutoWebResponse(
                            explanation=new_plan.get("analysis", "任务已完成"),
                            overall_status="completed",
                            actions=[]
                        )
                    else:
                        # 继续执行新计划
                        logger.info("更新操作计划")
                        plan = AutoWebResponse(
                            actions=[WebAction.model_validate(
                                a) for a in new_plan.get("actions", [])],
                            explanation=new_plan.get("explanation", ""),
                            additional_info=new_plan.get("analysis", ""),
                            overall_status=new_plan.get(
                                "current_status", "in_progress")
                        )

                        logger.info(f"新计划包含 {len(plan.actions)} 个步骤")
                        for i, action in enumerate(plan.actions):
                            logger.info(
                                f"新步骤 {i+1}: {action.action} - {action.description}")

                        self.printer.print_in_terminal(
                            "replanned_actions",
                            style="blue",
                            count=len(plan.actions)
                        )

                except Exception as e:
                    logger.error(f"解析分析结果时出错: {str(e)}")
                    # 如果无法解析，默认继续执行下一个操作
                    logger.info("无法解析新计划，默认移除当前操作并继续")
                    plan.actions = plan.actions[1:]
            else:
                # 验证成功，移除已执行的操作
                logger.info("验证成功，继续执行下一步")
                plan.actions = plan.actions[1:]
                self.printer.print_in_terminal(
                    "action_succeeded",
                    style="green",
                    action=action.action
                )

            # 调试模式：添加手动暂停
            if debug:
                self.computer.response_user(f"完成步骤 {iterations}，按Enter继续...")
                input()

        # 达到最大迭代次数
        logger.warning(f"达到最大迭代次数 ({max_iterations})，未能完成任务")
        self.printer.print_in_terminal(
            "max_iterations_reached",
            style="yellow",
            max_iterations=max_iterations
        )

        return AutoWebResponse(
            explanation=f"达到最大迭代次数 ({max_iterations})，未能完成任务",
            overall_status="max_iterations_reached",
            actions=[]
        )

    def save_to_memory_file(self, query: str, response: str):
        """保存对话到记忆文件"""
        memory_dir = os.path.join(".auto-coder", "memory")
        os.makedirs(memory_dir, exist_ok=True)
        file_path = os.path.join(memory_dir, "web_automation_history.json")

        # 创建新的消息对象
        timestamp = str(int(time.time()))

        # 加载现有对话或创建新的
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    existing_conv = json.load(f)
                except Exception:
                    existing_conv = {"history": {}, "conversations": []}
        else:
            existing_conv = {"history": {}, "conversations": []}

        # 添加新记录
        existing_conv["conversations"].append({
            "user_message": query,
            "system_response": response,
            "timestamp": timestamp
        })

        # 保存更新的对话
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_conv, f, ensure_ascii=False, indent=2)


def auto_web(llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], user_input: str, 
             screenshot_path: Optional[str] = None, 
             context: Optional[str] = None, 
             args: Optional[AutoCoderArgs] = None, debug: bool = False):
    """
    执行网页自动化操作的入口函数

    Args:
        llm: ByzerLLM实例，用于分析和生成操作
        user_input: 用户输入的指令
        screenshot_path: 可选的截图路径
        context: 可选的上下文信息
        args: 可选的配置参数
        debug: 是否开启调试模式，设为True时每一步会要求用户确认
    """

    # 创建请求
    request = AutoWebRequest(
        user_input=user_input,
        context=context,
        screenshot_path=screenshot_path
    )

    # 初始化自动化工具
    tuner = AutoWebTuner(llm=llm, args=args)

    # 执行自适应的自动化流程
    response = tuner.run_adaptive_flow(request, debug=debug)

    return response
