import os
import time
import json
from typing import Dict, List, Any, Optional, Tuple
import pydantic
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

import byzerllm
from autocoder.common import AutoCoderArgs
from autocoder.common.computer_use import ComputerUse
from autocoder.common.printer import Printer
from autocoder.utils import llms as llms_utils
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.result_manager import ResultManager
from autocoder.common import git_utils
from autocoder.common.global_cancel import global_cancel
from byzerllm.utils.client import code_utils


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
    
    @byzerllm.prompt()
    def _command_readme(self) -> Dict[str, str]:
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
        <name>detect_objects</name>
        <description>
          分析图片，检测其中的各种界面元素（如按钮、输入框、链接等）并返回它们的位置和描述。
          对于需要点击或与特定界面元素交互的场景非常有用。
        </description>
        <usage>
         该方法需要一个图片路径参数，通常是通过 screenshot() 函数获取的截图。
         
         使用例子：
         detect_objects(image_path="screenshot.png")
         
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
        <name>type_text</name>
        <description>
          模拟键盘输入文本。适用于需要在输入框中输入内容的场景。
        </description>
        <usage>
         该方法需要以下参数：
         1. text: 要输入的文本内容
         2. interval (可选): 每个字符之间的时间间隔，默认为0.05秒
         
         使用例子：
         type_text(text="Hello World")
         type_text(text="慢速输入", interval=0.2)  # 较慢的输入速度
        </usage>
        </command>

        <command>
        <name>press_key</name>
        <description>
          按下指定的键盘按键。适用于需要按特殊键(如回车、Tab等)的场景。
        </description>
        <usage>
         该方法需要一个key参数，指定要按下的键名称。
         
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
         press_key(key="enter")  # 按回车键
         press_key(key="ctrl+a")  # 全选
         press_key(key="alt+tab")  # 切换窗口
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
        </commands>
        '''        

    @byzerllm.prompt()
    def analyze_task(self, request: AutoWebRequest) -> Dict[str, str]:
        """
        图片是当前屏幕截图。
        {{ image }}

        我需要你帮我分析用户的网页自动化任务请求，并生成可执行的步骤。
        
        用户请求：{{request.user_input}}
        
        {% if request.context %}
        上下文信息：{{request.context}}
        {% endif %}
                
        
        请分析用户的请求，并生成一系列浏览器自动化操作步骤。支持的操作类型包括：
        
        <commands>
        {{ web_tools_readme }}
        </commands>
        
        请返回以下JSON格式的响应：
        ```json
        {
            "actions": [
                {
                    "action": "操作类型",
                    "parameters": {
                        "参数1": "值1",
                        "参数2": "值2"
                    },
                    "description": "该步骤的描述",
                    "expected_outcome": "执行该操作后期望看到的结果"
                }
            ],
            "explanation": "对整体方案的解释",
            "additional_info": "任何其他相关信息",
            "suggested_next_steps": ["建议的后续步骤1", "建议的后续步骤2"]
        }
        ```
        
        为了更好地完成用户请求，请确保：
        1. 操作步骤是逻辑合理的
        2. 必要时包含截图和检测步骤，以便获取页面状态
        3. 在点击或输入前确认元素位置
        4. 添加适当的等待时间（通过wait参数）
        5. 包含足够详细的描述，帮助用户理解每一步
        6. 为每个步骤提供明确的expected_outcome，描述执行该操作后期望看到的结果，方便验证
        
        如果无法确定具体坐标，请使用find_and_click操作通过文本描述查找元素。
        
        请确保每个步骤都有一个合理的期望结果，以便我们可以验证操作是否成功。
        """
        image = byzerllm.Image.load_image_from_path(request.screenshot_path)
        return {
            "request": request,
            "web_tools_readme": self._command_readme.prompt(),
            "image": image
        }

    @byzerllm.prompt()
    def verify_action_result(self, action: WebAction, result: Dict[str, Any], screenshot_path: str) -> Dict[str, str]:
        """
        图片是当前屏幕截图。
        {{ image }}
        
        我需要验证一个Web自动化操作的执行结果是否符合预期。

        执行的操作:
        ```json
        {{ action_json }}
        ```

        操作的期望结果:
        {{ action.expected_outcome }}

        操作的实际执行结果:
        ```json
        {{ result_json }}
        ```        

        请分析操作的实际执行结果和当前屏幕状态，判断操作是否达成了预期效果。

        返回以下JSON格式的验证结果:
        ```json
        {
            "success": true或false,                  // 操作是否成功达成预期效果
            "analysis": "详细分析当前屏幕和操作结果",  // 分析当前屏幕和操作结果
            "reason": "成功或失败的原因",             // 操作成功或失败的原因
            "suggestion": "如果失败，建议的下一步操作"  // 如果操作失败，建议的下一步操作
        }
        ```
        """
        image = byzerllm.Image.load_image_from_path(screenshot_path)
        return {
            "action_json": json.dumps(action.model_dump(), ensure_ascii=False, indent=2),
            "action": action,
            "result_json": json.dumps(result, ensure_ascii=False, indent=2),
            "image": image
        }

    @byzerllm.prompt()
    def analyze_execution_result(self, task: AutoWebRequest, execution_history: List[Dict], screenshot_path: str) -> Dict[str, str]:
        """
        图片是当前屏幕截图。
        {{ image }}

        我需要你分析网页自动化任务的执行历史和当前屏幕状态，确定下一步行动计划。
        
        原始任务:
        {{ task.user_input }}
        
        执行历史:
        ```json
        {{ execution_history_json }}
        ```        
        请根据执行历史和当前屏幕状态，分析目前的情况并确定接下来的步骤。
        
        返回以下JSON格式的响应:
        ```json
        {
            "current_status": "当前任务进展状态",
            "analysis": "详细分析当前情况",
            "completed": true或false,  // 任务是否已完成
            "actions": [  // 如果任务未完成，需要执行的后续操作
                {
                    "action": "操作类型",
                    "parameters": {
                        "参数1": "值1",
                        "参数2": "值2"
                    },
                    "description": "该步骤的描述",
                    "expected_outcome": "执行该操作后期望看到的结果"
                }
            ],
            "explanation": "对后续计划的解释",
            "overall_status": "总体任务状态评估"
        }
        ```
        
        请确保:
        1. 准确评估当前任务进展
        2. 如果遇到错误或意外情况，提供恢复策略
        3. 如果任务已完成，明确说明完成的标志
        4. 提供清晰的后续操作步骤（如果需要）
        """
        image = byzerllm.Image.load_image_from_path(screenshot_path)
        return {
            "task": task,
            "execution_history_json": json.dumps(execution_history, ensure_ascii=False, indent=2),
            "image": image
        }

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
            # 特殊处理ask_user操作
            if action.action == "ask_user":
                question = action.parameters.get("question", "")
                answer = self.ask_user(question)
                screenshot_path = self.computer.screenshot(f"after_ask_user_{int(time.time())}.png")
                return ActionResult(
                    success=True,
                    action=action,
                    screenshot_path=screenshot_path,
                    result={"success": True, "answer": answer}
                )
            
            # 特殊处理response_user操作
            if action.action == "response_user":
                message = action.parameters.get("response", "")
                self.response_user(message)
                screenshot_path = self.computer.screenshot(f"after_response_user_{int(time.time())}.png")
                return ActionResult(
                    success=True,
                    action=action,
                    screenshot_path=screenshot_path,
                    result={"success": True, "message": message}
                )
            
            # 构建工作流步骤
            step = {
                "action": action.action,
                **action.parameters
            }
            
            # 执行步骤并获取结果
            step_results = self.computer.run_workflow([step])
            
            # 执行后截图
            screenshot_path = self.computer.screenshot(f"after_{action.action}_{int(time.time())}.png")
            
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
                screenshot_path = self.computer.screenshot(f"error_{action.action}_{int(time.time())}.png")
            except:
                screenshot_path = None
                
            return ActionResult(
                success=False,
                action=action,
                screenshot_path=screenshot_path,
                error=str(e)
            )

    def verify_result(self, action_result: ActionResult) -> Dict[str, Any]:
        """
        验证操作结果是否符合预期
        
        Args:
            action_result: 操作执行结果
            
        Returns:
            验证结果
        """
        # 如果操作已经失败，不需要验证
        if not action_result.success:
            return {
                "success": False,
                "analysis": f"操作执行失败: {action_result.error}",
                "reason": action_result.error,
                "suggestion": "检查操作参数或尝试不同的方法"
            }
        
        # 如果没有预期结果或截图，则无法验证
        if not action_result.action.expected_outcome or not action_result.screenshot_path:
            return {
                "success": True,
                "analysis": "无法验证结果，缺少预期结果或截图",
                "reason": "缺少验证所需信息",
                "suggestion": "继续执行下一步"
            }
        
        # 使用 LLM 验证结果
        verification = self.verify_action_result.with_llm(self.llm).run(
            action=action_result.action,
            result=action_result.result,
            screenshot_path=action_result.screenshot_path
        )
        
        # 解析验证结果
        try:
            verification_json = code_utils.extract_code(verification)[-1][1]
            return json.loads(verification_json)
        except Exception as e:
            logger.error(f"解析验证结果时出错: {str(e)}")
            return {
                "success": True,  # 默认继续执行
                "analysis": "无法解析验证结果",
                "reason": str(e),
                "suggestion": "继续执行下一步"
            }

    def run_adaptive_flow(self, request: AutoWebRequest, max_iterations: int = 10) -> AutoWebResponse:
        """
        运行自适应的自动化流程，根据执行结果动态调整后续计划
        
        Args:
            request: 初始请求
            max_iterations: 最大迭代次数，防止无限循环
            
        Returns:
            最终响应结果
        """
        console = Console()
        
        # 初始状态：获取当前屏幕截图
        initial_screenshot = self.computer.screenshot("initial_state.png")
        if not request.screenshot_path:
            request.screenshot_path = initial_screenshot
        
        # 分析任务并生成初始计划
        response = self.analyze_task.with_llm(self.llm).run(request=request)
        try:
            json_content = code_utils.extract_code(response)[-1][1]
            plan = AutoWebResponse.model_validate_json(json_content)
        except Exception as e:
            logger.error(f"解析任务分析结果时出错: {str(e)}")
            console.print(Panel(
                Text(f"解析任务分析结果时出错: {str(e)}", style="red"),
                title="❌ 错误",
                border_style="red"
            ))
            return AutoWebResponse(
                explanation=f"解析任务分析结果时出错: {str(e)}",
                overall_status="failed"
            )
        
        # 执行历史
        execution_history = []
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            if global_cancel.cancelled:
                self.printer.print_in_terminal(
                    "operation_cancelled",
                    style="yellow"
                )
                return AutoWebResponse(
                    explanation="操作已取消",
                    overall_status="cancelled",
                    actions=[]
                )
            
            # 如果没有更多操作，认为任务完成
            if not plan.actions:
                console.print(Panel(
                    Text(plan.explanation or "任务完成", style="green"),
                    title="✅ 完成",
                    border_style="green"
                ))
                plan.overall_status = "completed"
                return plan
            
            # 执行当前计划中的第一个操作
            action = plan.actions[0]
            self.printer.print_in_terminal(
                "executing_step",
                style="blue",
                step=iterations,
                description=action.description or action.action
            )
            
            # 执行操作
            action_result = self.execute_action(action)
            
            # 验证结果
            verification = self.verify_result(action_result)
            
            # 记录执行历史
            execution_record = {
                "step": iterations,
                "action": action.model_dump(),
                "result": action_result.model_dump(exclude={"action"}),
                "verification": verification
            }
            execution_history.append(execution_record)
            
            # 如果验证失败，需要重新规划
            if not verification.get("success", False):
                self.printer.print_in_terminal(
                    "action_verification_failed",
                    style="yellow",
                    action=action.action,
                    reason=verification.get("reason", "未知原因")
                )
                
                # 获取当前屏幕状态
                current_screenshot = action_result.screenshot_path or self.computer.screenshot("current_state.png")
                
                # 基于执行历史和当前状态进行分析
                analysis_result = self.analyze_execution_result.with_llm(self.llm).run(
                    task=request,
                    execution_history=execution_history,
                    screenshot_path=current_screenshot
                )
                
                try:
                    # 解析分析结果
                    analysis_json = code_utils.extract_code(analysis_result)[-1][1]
                    new_plan = json.loads(analysis_json)
                    
                    # 更新计划
                    if new_plan.get("completed", False):
                        # 任务已完成
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
                        plan = AutoWebResponse(
                            actions=[WebAction.model_validate(a) for a in new_plan.get("actions", [])],
                            explanation=new_plan.get("explanation", ""),
                            additional_info=new_plan.get("analysis", ""),
                            overall_status=new_plan.get("current_status", "in_progress")
                        )
                        
                        self.printer.print_in_terminal(
                            "replanned_actions",
                            style="blue",
                            count=len(plan.actions)
                        )
                
                except Exception as e:
                    logger.error(f"解析分析结果时出错: {str(e)}")
                    # 如果无法解析，默认继续执行下一个操作
                    plan.actions = plan.actions[1:]
            else:
                # 验证成功，移除已执行的操作
                plan.actions = plan.actions[1:]
                self.printer.print_in_terminal(
                    "action_succeeded",
                    style="green",
                    action=action.action
                )
        
        # 达到最大迭代次数
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

    def ask_user(self, question: str) -> str:
        """
        向用户提问，获取用户输入
        
        Args:
            question: 问题内容
            
        Returns:
            用户的回答
        """
        console = Console()
        
        # 创建一个醒目的问题面板
        question_text = Text(question, style="bold cyan")
        question_panel = Panel(
            question_text,
            title="[bold yellow]Web Automation Question[/bold yellow]",
            border_style="blue",
            expand=False
        )
        
        # 显示问题面板
        console.print(question_panel)
        
        # 获取用户输入
        try:
            from prompt_toolkit import PromptSession
            session = PromptSession(message=self.printer.get_message_from_key('web_automation_ask_user', default="Your answer: "))
            answer = session.prompt()
        except (ImportError, KeyboardInterrupt):
            # 降级到标准输入或处理中断
            answer = input("Your answer: ")
        
        # 记录交互
        self.save_to_memory_file(
            query=question,
            response=answer
        )
        
        return answer

    def response_user(self, response: str) -> str:
        """
        直接向用户显示消息，无需等待用户输入
        
        Args:
            response: 要显示的消息内容
            
        Returns:
            显示的消息内容
        """
        console = Console()
        
        # 创建一个醒目的消息面板
        message_text = Text(response, style="italic")
        message_panel = Panel(
            message_text,
            title="",
            border_style="green",
            expand=False
        )
        
        # 显示消息面板
        console.print(message_panel)
        
        # 记录交互
        self.save_to_memory_file(
            query="system_message",
            response=response
        )
        
        return response


# 消息配置
MESSAGES = {
    "auto_web_analyzing": "正在分析网页自动化任务...",
    "auto_web_analyzed": "网页自动化任务分析完成",
    "executing_web_action": "执行操作: {action} - {description}",
    "executing_step": "执行步骤 {step}: {description}",
    "operation_cancelled": "操作已取消",
    "element_not_found": "未找到元素: {element}",
    "analyzing_results": "分析执行结果...",
    "next_steps_determined": "已确定下一步操作",
    "max_iterations_reached": "已达到最大迭代次数 ({max_iterations})",
    "action_verification_failed": "操作验证失败: {action} - {reason}",
    "action_succeeded": "操作成功: {action}",
    "replanned_actions": "已重新规划 {count} 个操作",
    "web_automation_ask_user": "您的回答: "  # 新增消息
}

# 注册消息
Printer.register_messages(MESSAGES)


def auto_web(user_input: str, screenshot_path: Optional[str] = None, context: Optional[str] = None, args: Optional[AutoCoderArgs] = None):
    """
    执行网页自动化操作的入口函数
    
    Args:
        user_input: 用户输入的指令
        screenshot_path: 可选的截图路径
        context: 可选的上下文信息
        args: 可选的配置参数
    """
    from autocoder.utils.llms import get_default_llm
    
    # 使用默认参数或提供的参数
    if args is None:
        from autocoder.common.cli_args import default_autocoder_args
        args = default_autocoder_args()
    
    # 初始化LLM
    llm = get_default_llm(args)
    
    # 创建请求
    request = AutoWebRequest(
        user_input=user_input,
        context=context,
        screenshot_path=screenshot_path
    )
    
    # 初始化自动化工具
    tuner = AutoWebTuner(llm=llm, args=args)
    
    # 执行自适应的自动化流程
    response = tuner.run_adaptive_flow(request)
    
    return response 