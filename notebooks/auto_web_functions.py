#!/usr/bin/env python


import os
import sys
import argparse
import json
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

import byzerllm
from autocoder.commands.auto_web import auto_web
from autocoder.common import AutoCoderArgs
from autocoder.common.computer_use import ComputerUse
from autocoder.utils.llms import get_single_llm
from byzerllm.utils.client import code_utils

def main():
    # 创建输出目录
    os.makedirs("./output", exist_ok=True)
        
    #doubao_vl
    #qvq_72b
    #or_sonnet37_chat 
    llm = get_single_llm("doubao_vl",product_mode="lite")
    # 创建配置
    auto_coder_args = AutoCoderArgs(
        output="./output"
    )
    
    computer_use = ComputerUse(llm,auto_coder_args,screenshot_dir="./output/screenshots")
    path = computer_use.screenshot()
    response = computer_use.find_elements.with_llm(llm).run(path, "当前vscode Chat面板的输入框")
    result_json = code_utils.extract_code(response)[-1][1]
    print(response)
    result = json.loads(result_json)
    objects = result.get("objects", [])    
    if objects:
        # 找到匹配度最高的元素
        best_match = sorted(objects, key=lambda x: x.get("confidence", 0), reverse=True)[0]
        bbox = best_match.get("bounding_box", [])        
        v  = computer_use.draw_bounding_box(path, bbox, "Cursor软件的关闭按钮")
        print(v)

if __name__ == "__main__":
    main() 