import time
import byzerllm
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from autocoder.common.printer import Printer
from autocoder import models as models_module
from autocoder.utils.llms import get_single_llm
import byzerllm

byzerllm_content = ""
try:
    byzerllm_conten_path = pkg_resources.resource_filename(
        "autocoder", "data/byzerllm.md"
    )
    with open(byzerllm_conten_path, "r",encoding="utf-8") as f:
        byzerllm_content = f.read()
except FileNotFoundError:
    pass

@byzerllm.prompt()
def long_context_prompt() -> str:
    '''
    下面是我们提供的一份文档：
    <document>
    {content}
    </document>
    
    请根据上述文档，实现用户的需求：

    <query>
    我想开发一个翻译程序，使用prompt 函数实现。
    </query>
    '''
    return {
        "content": byzerllm_content
    }

@byzerllm.prompt()
def short_context_prompt() -> str:
    '''
    Hello, can you help me test the response speed?
    '''
    return {}

def test_model_speed(model_name: str, 
                    product_mode: str, 
                    test_rounds: int = 3,
                    enable_long_context: bool = False
                    ) -> Dict[str, Any]:
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

        times = []
        first_token_times = []
        test_query = short_context_prompt.prompt()
        if enable_long_context:
            test_query = long_context_prompt.prompt()
        
        for _ in range(test_rounds):
            start_time = time.time()
            first_token_received = False
            first_token_time = None
            last_meta = None
            for chunk,meta in llm.stream_chat_oai([{
                "role": "user",
                "content": test_query
            }]):
                last_meta = meta                
                current_time = time.time()
                if not first_token_received:
                    first_token_time = current_time - start_time
                    first_token_received = True
                    first_token_times.append(first_token_time)
            
            end_time = time.time()            
            generated_tokens_count = 0
            if last_meta:                
                generated_tokens_count = last_meta.generated_tokens_count
            times.append(end_time - start_time)
            
        avg_time = sum(times) / len(times)
        return {
            "tokens_per_second": generated_tokens_count / avg_time,
            "avg_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "first_token_time": sum(first_token_times) / len(first_token_times),
            "success": True,
            "error": None
        }
    except Exception as e:
        return {
            "tokens_per_second": 0,
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
    
    table.add_column("Tokens/s", style="green", width=15)
    table.add_column("First Token(s)", style="magenta", width=15)
    table.add_column("Model", style="cyan", width=30)
    table.add_column("Avg Time(s)", style="green", width=15)
    table.add_column("Min Time(s)", style="blue", width=15)
    table.add_column("Max Time(s)", style="yellow", width=15)    
    table.add_column("Status", style="red", width=20)
    
    # 准备测试参数
    test_args = [(model["name"], product_mode, test_rounds) for model in active_models]
    
    # 存储结果用于排序
    results_list = []
    
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
                    results_list.append((
                        results['tokens_per_second'],
                        model_name,
                        results
                    ))
                    
                    # 更新模型的平均速度
                    models_module.update_model_speed(model_name, results['avg_time'])
                else:
                    status = f"✗ ({results['error']})"
                    results_list.append((
                        0,
                        model_name,
                        {"avg_time": 0, "min_time": 0, "max_time": 0, "first_token_time": 0}
                    ))
            except Exception as e:
                results_list.append((
                    0,
                    model_name,
                    {"avg_time": 0, "min_time": 0, "max_time": 0, "first_token_time": 0}
                ))

    # 按速度排序
    results_list.sort(key=lambda x: x[0], reverse=True)
    
    # 添加排序后的结果到表格
    for tokens_per_second, model_name, results in results_list:
        if tokens_per_second > 0:
            table.add_row(
                f"{tokens_per_second:.2f}",
                f"{results['first_token_time']:.2f}",
                model_name,
                f"{results['avg_time']:.2f}",
                f"{results['min_time']:.2f}",
                f"{results['max_time']:.2f}",
                "✓"
            )
        else:
            table.add_row(
                "-",
                "-",
                model_name,
                "-",
                "-",
                "-",
                f"✗ (Error occurred)"
            )
    
    console.print(Panel(table, border_style="blue"))