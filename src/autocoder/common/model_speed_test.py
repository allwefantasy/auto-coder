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
import pkg_resources
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Tuple
from pydantic import BaseModel

class ModelSpeedTestResult(BaseModel):
    model_name: str
    tokens_per_second: float
    first_token_time: float
    input_tokens_count: float
    generated_tokens_count: float
    input_tokens_cost: float
    generated_tokens_cost: float
    status: str
    error: Optional[str] = None

class SpeedTestResults(BaseModel):
    results: List[ModelSpeedTestResult]

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
    {{ content }}
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
    from autocoder.models import get_model_by_name
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
        model_info = get_model_by_name(model_name)

        times = []
        first_token_times = []
        tokens_per_seconds = []
        input_tokens_counts = []
        generated_tokens_counts = []
        
        input_tokens_costs = []
        generated_tokens_costs = []

        input_tokens_cost_per_m = model_info.get("input_price", 0.0) / 1000000
        output_tokens_cost_per_m = model_info.get("output_price", 0.0) / 1000000

        test_query = short_context_prompt.prompt()
        if enable_long_context:
            test_query = long_context_prompt.prompt()                
        
        content = ""
        for _ in range(test_rounds):
            start_time = time.time()
            first_token_received = False
            first_token_time = None
            last_meta = None
            input_tokens_count = 0
            generated_tokens_count = 0 
            input_tokens_cost = 0
            generated_tokens_cost = 0           
            for chunk,meta in llm.stream_chat_oai(conversations=[{
                "role": "user",
                "content": test_query
            }],delta_mode=True):
                content += chunk
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
                input_tokens_count = last_meta.input_tokens_count
                input_tokens_cost = input_tokens_count * input_tokens_cost_per_m
                generated_tokens_cost = generated_tokens_count * output_tokens_cost_per_m

                input_tokens_costs.append(input_tokens_cost)
                generated_tokens_costs.append(generated_tokens_cost)
                generated_tokens_counts.append(generated_tokens_count)
                input_tokens_counts.append(input_tokens_count)
            
            tokens_per_seconds.append(generated_tokens_count / (end_time - start_time))    
            times.append(end_time - start_time)
            
            
        avg_time = sum(times) / len(times)
        return {
            "tokens_per_second": sum(tokens_per_seconds) / len(tokens_per_seconds),
            "avg_time": avg_time,
            "min_time": min(times),
            "max_time": max(times),
            "first_token_time": sum(first_token_times) / len(first_token_times),
            "input_tokens_count": sum(input_tokens_counts) / len(input_tokens_counts),
            "generated_tokens_count": sum(generated_tokens_counts) / len(generated_tokens_counts),
            "success": True,
            "error": None,
            "input_tokens_cost": sum(input_tokens_costs) / len(input_tokens_costs),
            "generated_tokens_cost": sum(generated_tokens_costs) / len(generated_tokens_costs)
        }
    except Exception as e:
        return {
            "tokens_per_second": 0,
            "avg_time": 0,
            "min_time": 0,
            "max_time": 0,
            "first_token_time": 0,
            "input_tokens_count": 0,
            "generated_tokens_count": 0,
            "success": False,
            "error": str(e),
            "input_tokens_cost": 0.0,
            "generated_tokens_cost": 0.0
        }

def test_model_speed_wrapper(args: Tuple[str, str, int, bool]) -> Tuple[str, Dict[str, Any]]:
    """
    包装测试函数以适应线程池调用
    
    Args:
        args: (model_name, product_mode, test_rounds)的元组
        
    Returns:
        (model_name, test_results)的元组
    """
    model_name, product_mode, test_rounds,enable_long_context = args
    results = test_model_speed(model_name, product_mode, test_rounds,enable_long_context)
    return (model_name, results)


def run_speed_test(product_mode: str, test_rounds: int = 3, max_workers: Optional[int] = None, enable_long_context: bool = False) -> SpeedTestResults:
    """
    运行所有已激活模型的速度测试
    
    Args:
        product_mode: 产品模式 (lite/pro)
        test_rounds: 每个模型测试的轮数
        max_workers: 最大线程数,默认为None(ThreadPoolExecutor会自动设置)
        enable_long_context: 是否启用长文本上下文测试
    
    Returns:
        SpeedTestResults: 包含所有模型测试结果的pydantic模型
    """
    # 获取所有模型
    models_data = models_module.load_models()
    active_models = [m for m in models_data if "api_key" in m] if product_mode == "lite" else models_data
    
    if not active_models:
        return SpeedTestResults(results=[])
    
    # 准备测试参数
    test_args = [(model["name"], product_mode, test_rounds, enable_long_context) for model in active_models]
    
    # 存储结果用于排序
    results_list = []
    
    # 使用线程池并发测试
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有测试任务并获取future对象
        future_to_model = {executor.submit(test_model_speed_wrapper, args): args[0] 
                          for args in test_args}
        
        # 收集结果
        for future in future_to_model:
            model_name = future_to_model[future]
            
            try:
                _, results = future.result()
                
                if results["success"]:
                    status = "✓"
                    results_list.append((
                        results['tokens_per_second'],
                        ModelSpeedTestResult(
                            model_name=model_name,
                            tokens_per_second=results['tokens_per_second'],
                            first_token_time=results['first_token_time'],
                            input_tokens_count=results['input_tokens_count'],
                            generated_tokens_count=results['generated_tokens_count'],
                            status=status,
                            input_tokens_cost=results['input_tokens_cost'],
                            generated_tokens_cost=results['generated_tokens_cost'],                            
                        )
                    ))
                    try:
                        # 更新模型的平均速度
                        models_module.update_model_speed(model_name, results['tokens_per_second'])
                    except Exception:
                        pass
                else:                    
                    results_list.append((
                        0,
                        ModelSpeedTestResult(
                            model_name=model_name,
                            tokens_per_second=0,
                            first_token_time=0,
                            input_tokens_count=0,
                            generated_tokens_count=0,
                            status=f"✗ {results['error']}",
                            error=results['error'],
                            input_tokens_cost=0.0,
                            generated_tokens_cost=0.0
                        )
                    ))
            except Exception as e:
                results_list.append((
                    0,
                    ModelSpeedTestResult(
                        model_name=model_name,
                        tokens_per_second=0,
                        first_token_time=0,
                        input_tokens_count=0,
                        generated_tokens_count=0,
                        status=f"✗ {str(e)}",
                        error=str(e),
                        input_tokens_cost=0.0,
                        generated_tokens_cost=0.0
                    )
                ))

    # 按速度排序
    results_list.sort(key=lambda x: x[0], reverse=True)
    
    return SpeedTestResults(results=[result[1] for result in results_list])

def render_speed_test_in_terminal(product_mode: str, test_rounds: int = 3, max_workers: Optional[int] = None,enable_long_context: bool = False) -> None:
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
    table.add_column("Tokens/s", style="green", width=15)
    table.add_column("First Token(s)", style="magenta", width=15)
    table.add_column("Input Tokens", style="magenta", width=15)
    table.add_column("Generated Tokens", style="magenta", width=15)            
    table.add_column("Input Tokens Cost", style="yellow", width=15)
    table.add_column("Generated Tokens Cost", style="yellow", width=15)
    table.add_column("Status", style="red", width=20)
    
    # 准备测试参数
    test_args = [(model["name"], product_mode, test_rounds, enable_long_context) for model in active_models]
    
    # 存储结果用于排序
    results_list = []
    
    # 使用线程池并发测试
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        printer.print_in_terminal("models_testing_start", style="yellow")
        
        # 提交所有测试任务并获取future对象
        future_to_model = {executor.submit(test_model_speed_wrapper, args): args[0] 
                          for args in test_args}
        
        # 收集结果
        completed = 0
        total = len(future_to_model)
        for future in future_to_model:
            completed += 1
            printer.print_in_terminal("models_testing_progress", style="yellow", completed=completed, total=total)
            model_name = future_to_model[future]
            printer.print_in_terminal("models_testing", style="yellow", name=model_name)
            
            try:
                _, results = future.result()
                
                if results["success"]:
                    status = "✓"
                    results['status'] = status
                    results_list.append((
                        results['tokens_per_second'],
                        model_name,
                        results
                    ))                  
                    try:  
                        # 更新模型的平均速度
                        models_module.update_model_speed(model_name, results['tokens_per_second'])
                    except Exception as e:
                        pass
                else:
                    status = f"✗ ({results['error']})"
                    results_list.append((
                        0,
                        model_name,
                        {"tokens_per_second":0,"avg_time": 0, "input_tokens_count":0, "generated_tokens_count":0, "min_time": 0, "max_time": 0, "first_token_time": 0, "input_tokens_cost": 0.0, "generated_tokens_cost": 0.0, "status": status}
                    ))
            except Exception as e:
                results_list.append((
                    0,
                    model_name,
                        {"tokens_per_second":0,"avg_time": 0, "input_tokens_count":0, "generated_tokens_count":0, "min_time": 0, "max_time": 0, "first_token_time": 0, "input_tokens_cost": 0.0, "generated_tokens_cost": 0.0, "status": f"✗ ({str(e)})"}
                ))

    # 按速度排序
    results_list.sort(key=lambda x: x[0], reverse=True)
    
    # 添加排序后的结果到表格
    for tokens_per_second, model_name, results in results_list:        
        table.add_row(
            model_name,  
            f"{tokens_per_second:.2f}",
            f"{results['first_token_time']:.2f}",
            f"{results['input_tokens_count']}",
            f"{results['generated_tokens_count']}",
            f"{results['input_tokens_cost']:.4f}",
            f"{results['generated_tokens_cost']:.4f}",            
            results['status']
        )        
    
    console.print(Panel(table, border_style="blue"))