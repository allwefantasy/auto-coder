import os
import time
import json
import pyautogui
import numpy as np
from PIL import Image
import byzerllm
from loguru import logger
from typing import List, Dict, Tuple, Optional, Any, Union
import platform
from autocoder.common import AutoCoderArgs
from byzerllm.utils.client import code_utils

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
    def find_element(self, image_path: str, element_desc: str) -> str:
        """
        {{ image }}
        请在屏幕截图中找到以下描述的元素:
        {{ element_desc }}
        
        如果找到了，请返回该元素的bounding box坐标，使用 (xmin, ymin, xmax, ymax) 格式。
        如果没有找到，请明确说明。
        
        最后按如下格式返回：
        ```json
        {
            "found": true,  # 或 false
            "element": {
                "bounding_box": [xmin, ymin, xmax, ymax],
                "text": "元素上的文字或描述",
                "confidence": 0.95  # 置信度
            }
        }
        ```
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
        response = self.find_element.with_llm(self.vl_model).run(screenshot_path, element_desc)
        
        try:
            # 解析JSON结果
            result_json = code_utils.extract_code(response)[-1][1]
            result = json.loads(result_json)
            
            if result.get("found", False):
                element = result.get("element", {})
                bbox = element.get("bounding_box", [])
                
                if len(bbox) == 4:
                    # 计算中心点
                    center_x = int((bbox[0] + bbox[2]) / 2)
                    center_y = int((bbox[1] + bbox[3]) / 2)
                    
                    # 点击中心点
                    self.click(center_x, center_y)
                    logger.info(f"点击元素: {element.get('text', element_desc)}")
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
        
    def press_key(self, key: Union[str, List[str]]) -> None:
        """
        按下特定键或组合键
        
        Args:
            key: 键名或组合键列表，例如 'enter'、['ctrl', 'c']
        """
        if isinstance(key, list):
            logger.info(f"按下组合键: {'+'.join(key)}")
            pyautogui.hotkey(*key)
        else:
            logger.info(f"按下键: {key}")
            pyautogui.press(key)
            
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
                  支持的 action: screenshot, detect, click, drag, type, press, find, extract_text
            
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
                    element_desc = step.get('element')
                    image_path = step.get('image_path')
                    if not image_path:
                        # 自动截图
                        image_path = self.screenshot(f"auto_step_{i+1}.png")
                        
                    success = self.click_element(image_path, element_desc)
                    result['success'] = success
                    result['element'] = element_desc
                    
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
                    
                elif action == 'extract_text':
                    image_path = step.get('image_path')
                    region = step.get('region')
                    
                    if not image_path:
                        # 自动截图
                        image_path = self.screenshot(f"auto_step_{i+1}.png")
                        
                    text = self.extract_text(image_path, region)
                    result['text'] = text
                
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