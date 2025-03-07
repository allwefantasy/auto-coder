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


class AutoWebTuner:
    """
    基于大模型的网页自动化工具
    
    该类使用ComputerUse工具集实现浏览器操作，从用户指令中自动解析需要执行的操作，
    并生成详细的执行步骤，最后执行并返回结果。
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
         1. image_path: 图片路径，如果为None则自动截图
         2. element_desc: 元素的文本描述，例如"登录按钮"、"搜索框"等
         
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
        <name>run_workflow</name>
        <description>
          执行一系列预定义的操作步骤。适用于需要执行多个连续操作的场景。
        </description>
        <usage>
         该方法接受一个steps参数，是一个包含操作步骤的列表。
         每个步骤是一个字典，包含action字段和相应的参数。
         
         支持的action类型与前面介绍的命令相同。
         
         使用例子：
         run_workflow(steps=[
             {"action": "screenshot", "filename": "start.png"},
             {"action": "find_and_click", "element_desc": "搜索框"},
             {"action": "type_text", "text": "自动化测试"},
             {"action": "press_key", "key": "enter", "wait": 2},
             {"action": "screenshot", "filename": "result.png"}
         ])
         
         每个步骤都可以包含wait字段，指定操作后的等待时间（秒）。
         
         返回值：
         包含每个步骤执行结果的列表
        </usage>
        </command>
        </commands>
        '''        

    @byzerllm.prompt()
    def analyze_task(self, request: AutoWebRequest) -> Dict[str, str]:
        """
        我需要你帮我分析用户的网页自动化任务请求，并生成可执行的步骤。
        
        用户请求：{{request.user_input}}
        
        {% if request.context %}
        上下文信息：{{request.context}}
        {% endif %}
        
        {% if request.screenshot_path %}
        用户提供了当前屏幕截图路径：{{request.screenshot_path}}
        {% endif %}
        
        请分析用户的请求，并生成一系列浏览器自动化操作步骤。支持的操作类型包括：
        
        <commands>
        {{ self._command_readme() }}
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
                    "description": "该步骤的描述"
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
        
        如果无法确定具体坐标，请使用find_and_click操作通过文本描述查找元素。
                
        """
        return {
            "task": request,
            "web_tools_readme": self._command_readme.prompt()
        }

    @byzerllm.prompt()
    def analyze_execution_result(self, content: str) -> Dict[str, str]:
        """
        我刚刚执行了以下网页自动化操作：
        
        {{content}}
        
        请根据执行结果分析当前状态，并生成下一步操作建议。你可以提供以下几种响应：
        
        1. 如果需要继续执行更多步骤以完成用户请求，请提供详细的操作步骤
        2. 如果任务已经完成，请提供结果总结和分析
        3. 如果执行过程中遇到问题，请分析问题并提供解决方案
        
        请使用与之前相同的JSON格式：
        ```json
        {
            "actions": [...],
            "explanation": "...",
            "additional_info": "...",
            "suggested_next_steps": [...]
        }
        ```
        
        如果任务已完成，请将actions数组留空。
        
        """
        return {"content": content}

    def analyze_web_task(self, request: AutoWebRequest) -> AutoWebResponse:
        """
        分析网页自动化任务并生成操作步骤
        
        Args:
            request: 自动化任务请求
             
        Returns:
            生成的响应，包含操作步骤
        """
        # 准备提示
        prompt = self.analyze_task.with_llm(self.llm).run(request=request)
        conversations = [{"role": "user", "content": prompt}]
        
        # 使用LLM分析任务
        self.printer.print_in_terminal(
            "auto_web_analyzing",
            style="blue"
        )
        
        model_name = ",".join(llms_utils.get_llm_names(self.llm))
        result, _ = stream_out(
            self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
            model_name=model_name,
            title="正在分析网页自动化任务...",
            final_title="网页自动化任务分析完成",
            display_func=lambda content: "正在分析用户的网页自动化需求..."
        )
        
        # 保存对话
        conversations.append({"role": "assistant", "content": result})
        
        # 解析返回的JSON
        try:
            json_content = code_utils.extract_code(result)
            if json_content and len(json_content) > 0:
                json_str = json_content[-1][1]
                response_dict = json.loads(json_str)
                response = AutoWebResponse(**response_dict)
            else:
                # 无法提取JSON，创建一个带有错误解释的响应
                response = AutoWebResponse(
                    explanation="无法从LLM响应中提取有效的JSON格式。请尝试重新描述您的请求。"
                )
        except Exception as e:
            logger.error(f"解析LLM响应时出错: {str(e)}")
            response = AutoWebResponse(
                explanation=f"解析响应时出错: {str(e)}。请尝试重新描述您的请求。"
            )
        
        # 保存对话记录到记忆文件
        self.save_to_memory_file(
            query=request.user_input,
            response=response.model_dump_json(indent=2)
        )
        
        return response
    
    def execute_web_actions(self, actions: List[WebAction]) -> List[Dict[str, Any]]:
        """
        执行网页自动化操作步骤
        
        Args:
            actions: 要执行的操作列表
              
        Returns:
            执行结果列表
        """
        results = []
        console = Console()
        
        for i, action in enumerate(actions):
            if global_cancel.cancelled:
                self.printer.print_in_terminal(
                    "operation_cancelled",
                    style="yellow"
                )
                break
                
            description = action.description or f"步骤 {i+1}"
            self.printer.print_in_terminal(
                "executing_web_action",
                style="blue",
                action=action.action,
                description=description
            )
            
            try:
                # 构建工作流步骤
                step = {
                    "action": action.action,
                    **action.parameters
                }
                
                # 执行步骤并获取结果
                step_results = self.computer.run_workflow([step])
                
                if step_results and len(step_results) > 0:
                    result = step_results[0]
                    results.append({
                        "step": i+1,
                        "action": action.action,
                        "success": result.get("success", True),
                        "result": result,
                        "description": action.description
                    })
                else:
                    results.append({
                        "step": i+1,
                        "action": action.action,
                        "success": False,
                        "result": None,
                        "description": action.description,
                        "error": "执行步骤返回空结果"
                    })
            except Exception as e:
                logger.error(f"执行操作 {action.action} 时出错: {str(e)}")
                results.append({
                    "step": i+1,
                    "action": action.action,
                    "success": False,
                    "error": str(e),
                    "description": action.description
                })
        
        return results
    
    def run_continuous_flow(self, request: AutoWebRequest, max_iterations: int = 5) -> AutoWebResponse:
        """
        运行连续的自动化流程，根据结果自动调整后续步骤
        
        Args:
            request: 初始请求
            max_iterations: 最大迭代次数，防止无限循环
             
        Returns:
            最终响应结果
        """
        response = self.analyze_web_task.with_llm(self.llm).return_type(AutoWebResponse).run(request=request)
        iterations = 1
        
        # 检查是否需要继续
        while response.actions and iterations < max_iterations:
            iterations += 1
            
            # 执行操作
            results = self.execute_web_actions(response.actions)
            result_content = json.dumps(results, ensure_ascii=False, indent=2)
            
            # 准备新的上下文
            prompt = self.analyze_execution_result.with_llm(self.llm).run(content=result_content)
            conversations = [{"role": "user", "content": prompt}]
            
            # 获取LLM对执行结果的分析和下一步建议
            printer = Printer()
            title = printer.get_message_from_key("analyzing_results")
            final_title = printer.get_message_from_key("next_steps_determined")
            
            model_name = ",".join(llms_utils.get_llm_names(self.llm))
            result, _ = stream_out(
                self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
                model_name=model_name,
                title=title,
                final_title=final_title,
                display_func=lambda content: "分析执行结果..."
            )
            
            # 解析LLM的响应
            try:
                json_content = code_utils.extract_code(result)
                if not json_content or len(json_content) == 0:
                    break
                    
                json_str = json_content[-1][1]
                new_response_dict = json.loads(json_str)
                new_response = AutoWebResponse(**new_response_dict)
                
                # 如果没有更多操作，结束循环
                if not new_response.actions:
                    console = Console()
                    console.print(Panel(
                        Text(new_response.explanation or "任务完成"),
                        title="✅ 完成",
                        border_style="green",
                        padding=(1, 2)
                    ))
                    response = new_response
                    break
                
                # 更新响应和操作
                response = new_response
                
            except Exception as e:
                logger.error(f"解析LLM响应时出错: {str(e)}")
                break
        
        # 如果达到最大迭代次数
        if iterations >= max_iterations:
            self.printer.print_in_terminal(
                "max_iterations_reached",
                style="yellow",
                max_iterations=max_iterations
            )
        
        return response

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


# 消息配置
MESSAGES = {
    "auto_web_analyzing": "正在分析网页自动化任务...",
    "auto_web_analyzed": "网页自动化任务分析完成",
    "executing_web_action": "执行操作: {action} - {description}",
    "operation_cancelled": "操作已取消",
    "element_not_found": "未找到元素: {element}",
    "analyzing_results": "分析执行结果...",
    "next_steps_determined": "已确定下一步操作",
    "max_iterations_reached": "已达到最大迭代次数 ({max_iterations})"
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
    
    # 执行连续的自动化流程
    response = tuner.run_continuous_flow(request)
    
    return response 