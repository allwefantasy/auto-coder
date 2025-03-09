import os
import time
import json
import pyautogui
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import byzerllm
from loguru import logger
from typing import List, Dict, Tuple, Optional, Any, Union
import platform
from autocoder.common import AutoCoderArgs
from byzerllm.utils.client import code_utils
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import pydantic

class LoadingStatus(pydantic.BaseModel):
    should_wait: bool
    reason: str
class ComputerUse:
    """
    计算机交互工具类，提供以下功能：
    1. 屏幕截图
    2. 检测屏幕上的物体
    3. 鼠标点击
    4. 鼠标滑动
    5. 键盘输入
    """
    
    def __init__(
        self,
        llm: byzerllm.ByzerLLM,
        args: AutoCoderArgs,
        screenshot_dir: str = None,
        pause: float = 0.5  # 每次操作后的暂停时间
    ):
        """
        初始化计算机交互工具
        
        Args:
            llm: ByzerLLM 实例，用于视觉分析
            args: AutoCoderArgs 配置
            screenshot_dir: 截图保存目录，如果为 None 则使用 args.output
            pause: 每次操作后的暂停时间，单位为秒
        """
        self.llm = llm
        # 获取视觉模型子客户端
        if llm.get_sub_client("vl_model"):
            self.vl_model = llm.get_sub_client("vl_model")
        else:
            self.vl_model = self.llm
            
        self.args = args
        self.screenshot_dir = screenshot_dir or os.path.join(args.output, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # 设置 pyautogui 暂停时间
        pyautogui.PAUSE = pause
        
        # 获取系统信息
        self.system = platform.system()
        logger.info(f"运行于 {self.system} 系统")
        
        # 获取屏幕尺寸
        self.screen_width, self.screen_height = pyautogui.size()
        logger.info(f"屏幕尺寸: {self.screen_width}x{self.screen_height}")
        
        # 设置 pyautogui 的失败安全机制
        pyautogui.FAILSAFE = True  # 将鼠标移动到屏幕左上角会触发异常，中断程序
        
    def screenshot(self, filename: str = None) -> str:
        """
        截取屏幕并保存为图片
        
        Args:
            filename: 保存的文件名，如果为 None 则自动生成
            
        Returns:
            截图的保存路径
        """
        # 生成文件名
        if filename is None:
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            filename = f"screenshot_{timestamp}.png"
        
        # 确保文件名有扩展名
        if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            filename += '.png'
            
        # 完整路径
        filepath = os.path.join(self.screenshot_dir, filename)
        
        # 截屏
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        logger.info(f"屏幕截图已保存到 {filepath}")
        
        return filepath

    @byzerllm.prompt()
    def detect_objects(self, image_path: str) -> str:
        """
        {{ image }}
        请分析这张屏幕截图，识别出其中的各种界面元素(如按钮、输入框、菜单、图标等)，并给出每个元素的bounding box坐标。
        
        bouding box 使用 (xmin, ymin, xmax, ymax) 来表示，其中xmin, ymin: 表示矩形左上角的坐标
        xmax, ymax: 表示矩形右下角的坐标
        
        最后按如下格式返回：
        ```json
        {
            "objects": [
                {
                    "type": "button",  # 元素类型，如 button, input, icon, menu, text 等
                    "bounding_box": [xmin, ymin, xmax, ymax],
                    "text": "按钮上的文字或元素描述",
                    "confidence": 0.95  # 可选，置信度
                },
                ...
            ]
        }
        ```
        """
        image = byzerllm.Image.load_image_from_path(image_path)
        return {"image": image}
    
    @byzerllm.prompt()
    def find_elements(self, image_path: str, element_desc: str) -> str:
        """
        {{ image }}
    
        请在屏幕截图中找到所有符合以下描述的用户界面元素:
        <element_desc>
        {{ element_desc }}
        </element_desc>
        
        请考虑各种类型的UI元素，包括但不限于:
        - 按钮(button)
        - 输入框(input)
        - 下拉菜单(dropdown)
        - 复选框(checkbox)
        - 单选按钮(radio)
        - 标签(label)
        - 图标(icon)
        - 菜单项(menu item)
        - 导航栏(navigation)
        - 滑块(slider)
        
        请注意以下几点:
        1. 即使元素仅部分匹配描述，也请返回
        2. 对于文本元素，请尝试识别包含相似或相关文本的元素
        3. 考虑元素在界面中的上下文和位置关系
        4. 适应不同的视觉样式(包括深色/浅色主题)
        5. 如果找到多个匹配项，请全部返回并按置信度排序
        
        对于每个找到的元素，请提供以下信息:
        - bounding box坐标 (xmin, ymin, xmax, ymax),其中 xmin,ymin表示左上角坐标，xmax,ymax表示右下角坐标。
        - 元素类型(如按钮、输入框等)
        - 元素上的文本或描述
        - 匹配的置信度(0-1之间)
        
        最后按如下JSON格式返回:
        ```json
        {               
            "objects": [
                {
                    "type": "button",  // 元素类型
                    "bounding_box": [xmin, ymin, xmax, ymax],
                    "text": "元素上的文字或描述",
                    "confidence": 0.95  // 置信度，值越高表示匹配越确定
                },
                // 更多元素...
            ]
        }
        ```
        
        如果完全没有找到匹配的元素，请返回空objects数组:
        ```json
        {
            "objects": []
        }
        """
        image = byzerllm.Image.load_image_from_path(image_path)
        return {"image": image, "element_desc": element_desc}
        
    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> None:
        """
        在指定位置执行鼠标点击
        
        Args:
            x: 横坐标
            y: 纵坐标
            button: 鼠标按钮，可选 'left', 'right', 'middle'
            clicks: 点击次数
        """
        # 确保坐标在屏幕范围内
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))
        
        logger.info(f"鼠标点击: 坐标({x}, {y}), 按钮: {button}, 次数: {clicks}")
        pyautogui.click(x=x, y=y, button=button, clicks=clicks)
        
    def draw_bounding_box(self, image_path: str, bbox: List[int], element_desc: str, 
                         center_point: Optional[Tuple[int, int]] = None, 
                         confidence: Optional[float] = None) -> str:
        """
        在图像上绘制边界框、标签和中心点
        
        Args:
            image_path: 原始图像路径
            bbox: 边界框坐标 [x1, y1, x2, y2]
            element_desc: 元素描述
            center_point: 可选，中心点坐标 (x, y)
            confidence: 可选，置信度
            
        Returns:
            保存的带边界框图像路径
        """
        try:
            # 创建临时目录存储带框图片
            bbox_dir = os.path.join(self.screenshot_dir, "bboxes")
            os.makedirs(bbox_dir, exist_ok=True)
            
            # 生成新文件名
            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            bbox_image_path = os.path.join(bbox_dir, f"bbox_{timestamp}.png")
            
            # 加载原始图片
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            # 绘制矩形框
            draw.rectangle(
                [(bbox[0], bbox[1]), (bbox[2], bbox[3])],
                outline="red",
                width=3
            )
            
            # 如果提供了中心点，绘制中心点
            if center_point:
                cx, cy = center_point
                draw.ellipse(
                    [(cx-5, cy-5), (cx+5, cy+5)],
                    fill="blue"
                )
            
            # 准备标签文本
            if confidence is not None and isinstance(confidence, (int, float)):
                label_text = f"{element_desc} ({confidence:.2f})"
            else:
                label_text = element_desc
            
            # 设置文本位置
            text_x = bbox[0]
            text_y = max(0, bbox[1] - 20)  # 文本位于框上方
            
            # 绘制文本背景
            text_width = len(label_text) * 8  # 估算文本宽度
            draw.rectangle(
                [(text_x, text_y), (text_x + text_width, text_y + 20)],
                fill="yellow"
            )
            
            # 绘制文本
            draw.text(
                (text_x, text_y),
                label_text,
                fill="black"
            )
            
            # 在图片上添加时间戳和文件信息
            footer_text = f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')} | File: {os.path.basename(image_path)}"
            img_width, img_height = img.size
            footer_y = img_height - 20
            
            # 添加底部信息栏
            draw.rectangle(
                [(0, footer_y - 5), (img_width, img_height)],
                fill="black"
            )
            draw.text(
                (10, footer_y),
                footer_text,
                fill="white"
            )
            
            # 保存图片
            img.save(bbox_image_path)
            logger.info(f"已保存带边界框的图片: {bbox_image_path}")
            print(f"识别到元素 '{element_desc}' - 已保存边界框图片: {bbox_image_path}")
            
            return bbox_image_path
            
        except Exception as e:
            logger.error(f"绘制边界框时出错: {str(e)}")
            return None
    
    
    def click_element(self, screenshot_path: str, element_desc: str) -> bool:
        """
        查找并点击指定描述的元素
        
        Args:
            screenshot_path: 屏幕截图路径
            element_desc: 元素描述
            
        Returns:
            是否成功点击
        """
        # 查找元素
        response = self.find_elements.with_llm(self.vl_model).run(screenshot_path, element_desc)
        logger.info(f"查找元素结果: {response}")
        
        try:
            # 解析JSON结果
            result_json = code_utils.extract_code(response)[-1][1]
            result = json.loads(result_json)
            objects = result.get("objects", [])
            sorted_objects = sorted(objects, key=lambda x: x.get("confidence", 0), reverse=True)
                        
            for element in sorted_objects:
                bbox = element.get("bounding_box", [])
                
                if len(bbox) == 4:
                    # 计算中心点
                    center_x = int((bbox[0] + bbox[2]) / 2)
                    center_y = int((bbox[1] + bbox[3]) / 2)
                    
                    # 绘制边界框并保存图像
                    element_text = element.get('text', element_desc)
                    confidence = element.get('confidence', None)
                    
                    self.draw_bounding_box(
                        image_path=screenshot_path,
                        bbox=bbox,
                        element_desc=element_text,
                        center_point=(center_x, center_y),
                        confidence=confidence
                    )
                    
                    # 点击中心点
                    self.click(center_x, center_y)
                    logger.info(f"点击元素: {element_text}")
                    return True
            
            logger.warning(f"未找到元素: {element_desc}")
            return False
        
        except Exception as e:
            logger.error(f"解析查找结果时出错: {str(e)}")
            return False
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
        """
        从一个位置拖动到另一个位置
        
        Args:
            start_x: 起始位置X坐标
            start_y: 起始位置Y坐标
            end_x: 结束位置X坐标
            end_y: 结束位置Y坐标
            duration: 拖动持续时间，单位为秒
        """
        # 确保坐标在屏幕范围内
        start_x = max(0, min(start_x, self.screen_width - 1))
        start_y = max(0, min(start_y, self.screen_height - 1))
        end_x = max(0, min(end_x, self.screen_width - 1))
        end_y = max(0, min(end_y, self.screen_height - 1))
        
        logger.info(f"鼠标拖动: 从({start_x}, {start_y})到({end_x}, {end_y}), 持续时间: {duration}秒")
        
        # 移动到起始位置
        pyautogui.moveTo(start_x, start_y)
        # 拖动到目标位置
        pyautogui.dragTo(end_x, end_y, duration=duration)
        
    def scroll(self, x: int, y: int, clicks: int) -> None:
        """
        在指定位置滚动鼠标滚轮
        
        Args:
            x: 横坐标
            y: 纵坐标
            clicks: 滚动量，正数向上滚动，负数向下滚动
        """
        # 确保坐标在屏幕范围内
        x = max(0, min(x, self.screen_width - 1))
        y = max(0, min(y, self.screen_height - 1))
        
        direction = "上" if clicks > 0 else "下"
        logger.info(f"鼠标滚动: 坐标({x}, {y}), 方向: {direction}, 量: {abs(clicks)}")
        
        # 移动到指定位置
        pyautogui.moveTo(x, y)
        # 滚动
        pyautogui.scroll(clicks)
        
    def type_text(self, text: str, interval: float = 0.05) -> None:
        """
        模拟键盘输入文本
        
        Args:
            text: 要输入的文本
            interval: 按键间隔时间，单位为秒
        """
        logger.info(f"键盘输入: '{text}'")
        pyautogui.typewrite(text, interval=interval)
        
    def press_key(self, key):
        """
        按下指定的键或键组合
        
        Args:
            key: 键名或键组合列表，如'enter'或['ctrl', 'c']
        """
        try:
            if isinstance(key, list):
                # 处理组合键
                logger.info(f"按下组合键: {'+'.join(key)}")
                pyautogui.hotkey(*key)  # 使用hotkey方法处理组合键
            else:
                # 处理单个键
                logger.info(f"按下按键: {key}")
                pyautogui.press(key)
        except Exception as e:
            logger.error(f"按键操作失败: {str(e)}")
            raise
            
    def extract_text(self, screenshot_path: str, region: List[int] = None) -> str:
        """
        从屏幕截图中提取文本
        
        Args:
            screenshot_path: 屏幕截图路径
            region: 区域坐标 [xmin, ymin, xmax, ymax]，如果为None则处理整个截图
            
        Returns:
            提取的文本
        """
        if region is not None:
            # 裁剪指定区域
            img = Image.open(screenshot_path)
            cropped = img.crop(region)
            
            # 保存临时文件
            temp_path = os.path.join(self.screenshot_dir, "temp_region.png")
            cropped.save(temp_path)
            screenshot_path = temp_path
            
        @byzerllm.prompt()
        def extract_text_from_image(image_path: str) -> str:
            """
            {{ image }}
            请提取这张图片中的所有文本内容，保持原有布局和顺序。
            """
            image = byzerllm.Image.load_image_from_path(image_path)
            return {"image": image}
            
        # 调用VL模型提取文本
        result = extract_text_from_image.with_llm(self.vl_model).run(screenshot_path)
        return result
    
    def run_workflow(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行一系列操作步骤
        
        Args:
            steps: 操作步骤列表，每个步骤是一个字典，包含 'action' 和相关参数
                  支持的 action: screenshot, detect, click, find_and_click, type, press, 
                  drag, scroll, extract_text, ask_user, response_user, open_browser, should_wait_loading
            
        Returns:
            执行结果列表
        """
        results = []
        
        for i, step in enumerate(steps):
            try:
                action = step.get('action', '')
                logger.info(f"执行步骤 {i+1}: {action}")
                
                result = {'step': i+1, 'action': action, 'success': True}
                
                if action == 'screenshot':
                    filename = step.get('filename')
                    path = self.screenshot(filename)
                    result['path'] = path
                    result["should_verify"] = False

                elif action == 'focus_app':
                    app_name = step.get('app_name')
                    retry_count = step.get('retry_count', 3)
                    success = self.focus_app(app_name, retry_count)
                    result['success'] = success
                    result['app_name'] = app_name
                    
                elif action == 'detect':
                    image_path = step.get('image_path')
                    if not image_path:
                        # 自动截图
                        image_path = self.screenshot(f"auto_step_{i+1}.png")
                    
                    detection = self.detect_objects.with_llm(self.vl_model).run(image_path)
                    result_json = code_utils.extract_code(detection)[-1][1]
                    result['objects'] = json.loads(result_json)
                    
                elif action == 'click':
                    x = step.get('x')
                    y = step.get('y')
                    button = step.get('button', 'left')
                    clicks = step.get('clicks', 1)
                    
                    self.click(x, y, button, clicks)
                    result['coordinates'] = [x, y]
                    
                elif action == 'find_and_click':
                    element_desc = step.get('element_desc')
                    image_path = step.get('image_path')
                    if not image_path:
                        # 自动截图
                        image_path = self.screenshot(f"auto_step_{i+1}.png")
                        
                    success = self.click_element(image_path, element_desc)
                    result['success'] = success
                    result['element_desc'] = element_desc
                    
                elif action == 'drag':
                    start_x = step.get('start_x')
                    start_y = step.get('start_y')
                    end_x = step.get('end_x')
                    end_y = step.get('end_y')
                    duration = step.get('duration', 0.5)
                    
                    self.drag(start_x, start_y, end_x, end_y, duration)
                    result['from'] = [start_x, start_y]
                    result['to'] = [end_x, end_y]
                    
                elif action == 'type':
                    text = step.get('text', '')
                    interval = step.get('interval', 0.05)
                    
                    self.type_text(text, interval)
                    result['text'] = text
                    
                elif action == 'press':
                    key = step.get('key')
                    self.press_key(key)
                    result['key'] = key
                    
                elif action == 'scroll':
                    clicks = step.get('clicks')
                    x = step.get('x', None)
                    y = step.get('y', None)
                    
                    # 如果没有提供坐标，使用当前鼠标位置
                    current_pos = pyautogui.position()
                    if x is None:
                        x = current_pos.x
                    if y is None:
                        y = current_pos.y
                        
                    self.scroll(x, y, clicks)
                    result['coordinates'] = [x, y, clicks]
                    
                elif action == 'extract_text':
                    image_path = step.get('image_path')
                    region = step.get('region')
                    
                    if not image_path:
                        # 自动截图
                        image_path = self.screenshot(f"auto_step_{i+1}.png")
                        
                    text = self.extract_text(image_path, region)
                    result['text'] = text
                
                elif action == 'ask_user':                    
                    logger.info(f"需要询问用户: {question}")
                    question = step.get('question', '')
                    response = self.ask_user(question)
                    result['question'] = question
                    result['action_required'] = 'ask_user'
                    result['response'] = response
                    
                
                elif action == 'response_user':
                    logger.info(f"需要向用户显示: {response}")
                    response = step.get('response', '')
                    self.response_user(response)
                    result['response'] = response
                    result['action_required'] = 'response_user'                    
                
                elif action == 'open_browser':
                    browser_name = step.get('browser_name', 'chrome')                                        
                    browser_result = self.open_browser(browser_name)
                    result.update(browser_result)
                
                elif action == "wait_loading":
                    target = step.get('target')                                                          
                    
                    # 调用_should_wait_loading方法分析是否需要等待加载
                    wait_analysis = self.should_wait_loading(
                        target=target                        
                    )
                    
                    # 如果需要等待，自动等待一段时间
                    wait_times = 0
                    wait_time = 10

                    while wait_analysis.should_wait and wait_times < 10:
                        wait_times += 1
                        logger.info(f"系统正在加载中，自动等待 {wait_time} 秒...")
                        time.sleep(wait_time)
                        wait_analysis = self.should_wait_loading(
                            target=target                        
                        )
                        result['should_wait'] = wait_analysis.should_wait 
                        result['reason'] = wait_analysis.reason
                    result['should_wait'] = wait_analysis.should_wait
                    result['reason'] = wait_analysis.reason
                    result["should_verify"] = False
                        
                
                else:
                    logger.warning(f"未知操作: {action}")
                    result['success'] = False
                    result['error'] = f"未知操作: {action}"
                
                # 添加执行结果
                results.append(result)
                
                # 如果设置了等待时间
                if 'wait' in step:
                    wait_time = float(step['wait'])
                    logger.info(f"等待 {wait_time} 秒")
                    time.sleep(wait_time)
                    
            except Exception as e:
                logger.error(f"执行步骤 {i+1} 时出错: {str(e)}")
                results.append({
                    'step': i+1, 
                    'action': step.get('action', 'unknown'),
                    'success': False,
                    'error': str(e)
                })
                
                # 如果设置了出错继续
                if not step.get('continue_on_error', False):
                    break
                    
        return results
    

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
            
    def open_browser(self, browser_name="chrome", url=None):
        """
        打开指定的浏览器并可选择导航到URL。比直接使用系统命令更可靠的浏览器启动方式。
        
        Args:
            browser_name: 浏览器名称，默认为"chrome"，也支持"firefox"和"edge"等
            url: 可选参数，启动后要导航到的网址
            
        Returns:
            操作结果字典
        """
        import subprocess
        import platform
        import time
        
        system = platform.system()
        result = {"success": False, "message": ""}
        
        try:
            # 根据浏览器名称和操作系统打开浏览器
            if browser_name.lower() == "chrome":
                if system == 'Windows':
                    subprocess.Popen(['start', 'chrome'], shell=True)
                elif system == 'Darwin':  # macOS
                    subprocess.Popen(['open', '-a', 'Google Chrome'])
                elif system == 'Linux':
                    subprocess.Popen(['google-chrome'])
            elif browser_name.lower() == "firefox":
                if system == 'Windows':
                    subprocess.Popen(['start', 'firefox'], shell=True)
                elif system == 'Darwin':  # macOS
                    subprocess.Popen(['open', '-a', 'Firefox'])
                elif system == 'Linux':
                    subprocess.Popen(['firefox'])
            elif browser_name.lower() == "edge":
                if system == 'Windows':
                    subprocess.Popen(['start', 'msedge'], shell=True)
                elif system == 'Darwin':  # macOS
                    subprocess.Popen(['open', '-a', 'Microsoft Edge'])
                elif system == 'Linux':
                    subprocess.Popen(['microsoft-edge'])  

            result["success"] = True
            return result
        
        except Exception as e:
            result["message"] = f"启动{browser_name}浏览器时出错: {str(e)}"
            logger.error(f"启动{browser_name}浏览器时出错: {str(e)}")
            return result

    def element_exists(self, screenshot_path: str, element_desc: str) -> bool:
        """
        检查屏幕上是否存在指定描述的元素
        
        Args:
            screenshot_path: 屏幕截图路径
            element_desc: 元素描述
            
        Returns:
            元素是否存在
        """
        # 查找元素
        response = self.find_elements.with_llm(self.vl_model).run(screenshot_path, element_desc)
        logger.info(f"检查元素是否存在: {element_desc}")
        
        try:
            # 解析JSON结果
            result_json = code_utils.extract_code(response)[-1][1]
            result = json.loads(result_json)
            objects = result.get("objects", [])
            
            # 如果objects列表不为空，表示找到了元素
            exists = len(objects) > 0
            
            if exists:
                # 找到了元素，提供第一个匹配元素的信息
                best_match = sorted(objects, key=lambda x: x.get("confidence", 0), reverse=True)[0]
                confidence = best_match.get("confidence", 0)
                text = best_match.get("text", "")
                
                # 可选：绘制边界框并保存图片
                bbox = best_match.get("bounding_box", [])
                if len(bbox) == 4:
                    try:
                        # 计算中心点坐标
                        center_x = int((bbox[0] + bbox[2]) / 2)
                        center_y = int((bbox[1] + bbox[3]) / 2)
                        
                        # 绘制边界框
                        self.draw_bounding_box(
                            image_path=screenshot_path,
                            bbox=bbox,
                            element_desc=text or element_desc,
                            center_point=(center_x, center_y),
                            confidence=confidence
                        )
                    except Exception as e:
                        logger.error(f"绘制边界框时出错: {str(e)}")
                
                logger.info(f"找到元素 '{element_desc}', 置信度: {confidence}, 文本: '{text}'")
            else:
                logger.info(f"未找到元素 '{element_desc}'")
            
            return exists
            
        except Exception as e:
            logger.error(f"检查元素是否存在时出错: {str(e)}")
            return False
        
    @byzerllm.prompt()
    def _should_wait_loading(self, target: str) ->str:
        """        
        {{ current_screenshot }}
        
        考虑到诸如点击链接等动作，点击后不会立马发生屏幕变化，而用户期待看到的内容为：

        {{ target }}
        
        
        我们需要判断用户期待的内容是否已经出现。如果系统还处于加载状态，并且用户期待的内容还没有出现，请返回如下JSON格式：
        ```json
        {
            "should_wait": true,
            "reason": "判断是否处于加载状态分析理由"
        }
        ```

        如果用户期待的内容已经出现，请返回如下JSON格式：
        ```json
        {
            "should_wait": false,
            "reason": "判断是否处于加载状态分析理由"    
        }
        ```
        """  
        current_screenshot_path = self.screenshot(f"current_screenshot_{int(time.time())}.png")
        current_screenshot = byzerllm.Image.load_image_from_path(current_screenshot_path)
        return {
            "current_screenshot":current_screenshot,            
        }


    def should_wait_loading(self, target: str) -> LoadingStatus:
        """
        判断是否需要等待加载完成
        """
        response = self._should_wait_loading.with_llm(self.vl_model).with_return_type(LoadingStatus).run(target)        
        return response

    def focus_app(self, app_name: str, retry_count: int = 3) -> bool:
        """
        查找并聚焦指定的应用程序窗口
        
        Args:
            app_name: 应用程序名称或窗口标题的一部分
            retry_count: 重试次数，默认为3
            
        Returns:
            是否成功聚焦应用
        """
        logger.info(f"尝试聚焦应用: {app_name}")
        
        for attempt in range(retry_count):
            # 截取当前屏幕
            screenshot_path = self.screenshot(f"focus_app_{int(time.time())}.png")                        
                                                            
            # 查找元素并获取位置
            response = self.find_elements.with_llm(self.vl_model).run(screenshot_path, f"应用 {app_name},是否在屏幕上，比如标题栏，任务栏亦或者当前活动窗口")            
            try:
                result_json = code_utils.extract_code(response)[-1][1]
                result = json.loads(result_json)
                objects = result.get("objects", [])
                
                if objects:
                    # 找到匹配度最高的元素
                    best_match = sorted(objects, key=lambda x: x.get("confidence", 0), reverse=True)[0]
                    bbox = best_match.get("bounding_box", [])
                    
                    if len(bbox) == 4:
                        # 计算中心点
                        center_x = int((bbox[0] + bbox[2]) / 2)
                        center_y = int((bbox[1] + bbox[3]) / 2)
                        
                        # 点击应用窗口来聚焦
                        self.click(center_x, center_y)
                        logger.info(f"已点击 {app_name} 窗口，尝试聚焦")
                        
                        # 等待窗口获得焦点
                        time.sleep(0.5)
                        
                        # 再次截图以验证是否聚焦成功
                        verification_screenshot = self.screenshot(f"focus_app_verification_{int(time.time())}.png")
                        if self.element_exists(verification_screenshot, f"应用 {app_name} 是否在当前桌面"):
                            logger.info(f"成功聚焦应用: {app_name}")
                            return True
            except Exception as e:
                logger.error(f"聚焦应用时出错: {str(e)}")
            
            # 如果所有尝试都失败，等待一段时间后重试
            if attempt < retry_count - 1:
                logger.warning(f"聚焦 {app_name} 失败，将在1秒后重试 ({attempt+1}/{retry_count})")
                time.sleep(1)
        
        logger.error(f"无法聚焦应用: {app_name}，已达到最大重试次数")
        return False