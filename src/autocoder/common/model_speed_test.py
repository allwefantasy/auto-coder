import time
import byzerllm
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from autocoder.common.printer import Printer
from autocoder import models as models_module
from autocoder.utils.llms import get_single_llm

def test_model_speed(model_name: str, product_mode: str, test_rounds: int = 3) -> Dict[str, Any]:
    """
    测试单个模型的速度
    
    Args:
        model_name: 模型名称
        product_mode: 产品模式 (lite/pro)
        test_rounds: 测试轮数
        
    Returns:
        Dict包含测试结果:
            - avg_time: 平均响应时间
            - min_time: 最小响应时间
            - max_time: 最大响应时间
            - first_token_time: 首token时间
            - success: 是否测试成功
            - error: 错误信息(如果有)
    """
    try:
        llm = get_single_llm(model_name, product_mode)
        test_query = "Hello, can you help me test the response speed?"
        times = []
        first_token_times = []
        
        for _ in range(test_rounds):
            start_time = time.time()
            first_token_received = False
            first_token_time = None
            
            for chunk in llm.stream_chat_oai([{
                "role": "user",
                "content": test_query
            }]):
                current_time = time.time()
                if not first_token_received:
                    first_token_time = current_time - start_time
                    first_token_received = True
                    first_token_times.append(first_token_time)
            
            end_time = time.time()
            times.append(end_time - start_time)
        
        return {
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "first_token_time": sum(first_token_times) / len(first_token_times),
            "success": True,
            "error": None
        }
    except Exception as e:
        return {
            "avg_time": 0,
            "min_time": 0,
            "max_time": 0,
            "first_token_time": 0,
            "success": False,
            "error": str(e)
        }

from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple

def test_model_speed_wrapper(args: Tuple[str, str, int]) -> Tuple[str, Dict[str, Any]]:
    """
    包装测试函数以适应线程池调用
    
    Args:
        args: (model_name, product_mode, test_rounds)的元组
        
    Returns:
        (model_name, test_results)的元组
    """
    model_name, product_mode, test_rounds = args
    results = test_model_speed(model_name, product_mode, test_rounds)
    return (model_name, results)

def run_speed_test(product_mode: str, test_rounds: int = 3, max_workers: Optional[int] = None) -> None:
    """
    运行所有已激活模型的速度测试
    
    Args:
        product_mode: 产品模式 (lite/pro)
        test_rounds: 每个模型测试的轮数
        max_workers: 最大线程数,默认为None(ThreadPoolExecutor会自动设置)
    """
    printer = Printer()
    console = Console()
    
    # 获取所有模型
    models_data = models_module.load_models()
    active_models = [m for m in models_data if "api_key" in m] if product_mode == "lite" else models_data
    
    if not active_models:
        printer.print_in_terminal("models_no_active", style="yellow")
        return
        
    # 创建结果表格
    table = Table(
        title=printer.get_message_from_key("models_speed_test_results"),
        show_header=True,
        header_style="bold magenta",
        show_lines=True
    )
    
    table.add_column("Model", style="cyan", width=30)
    table.add_column("Avg Time(s)", style="green", width=15)
    table.add_column("Min Time(s)", style="blue", width=15)
    table.add_column("Max Time(s)", style="yellow", width=15)
    table.add_column("First Token(s)", style="magenta", width=15)
    table.add_column("Status", style="red", width=20)
    
    # 准备测试参数
    test_args = [(model["name"], product_mode, test_rounds) for model in active_models]
    
    # 使用线程池并发测试
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        printer.print_in_terminal("models_testing_start", style="yellow")
        
        # 提交所有测试任务并获取future对象
        future_to_model = {executor.submit(test_model_speed_wrapper, args): args[0] 
                          for args in test_args}
        
        # 收集结果
        for future in future_to_model:
            model_name = future_to_model[future]
            printer.print_in_terminal("models_testing", style="yellow", name=model_name)
            
            try:
                _, results = future.result()
                
                if results["success"]:
                    status = "✓"
                    table.add_row(
                        model_name,
                        f"{results['avg_time']:.2f}",
                        f"{results['min_time']:.2f}",
                        f"{results['max_time']:.2f}",
                        f"{results['first_token_time']:.2f}",
                        status
                    )
                    
                    # 更新模型的平均速度
                    models_module.update_model_speed(model_name, results['avg_time'])
                else:
                    status = f"✗ ({results['error']})"
                    table.add_row(
                        model_name,
                        "-",
                        "-",
                        "-",
                        "-",
                        status
                    )
            except Exception as e:
                table.add_row(
                    model_name,
                    "-",
                    "-",
                    "-",
                    "-",
                    f"✗ (Thread error: {str(e)})"
                )
    
    console.print(Panel(table, border_style="blue"))