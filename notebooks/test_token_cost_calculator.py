import time
import os
from typing import List, Dict, Any, Optional

import byzerllm
from byzerllm import MetaHolder
from loguru import logger
from autocoder.utils.llms import get_single_llm
from autocoder.common.token_cost_caculate import TokenCostCalculator, TokenUsageStats

# 配置日志格式
logger.remove()
logger.add(
    lambda msg: print(msg),
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# 全局测试统计
TOTAL_STATS = {
    "total_tests": 0,
    "total_tokens": 0,
    "total_cost": 0.0,
    "total_time": 0.0,
    "tests": []
}

# ==================== 提示函数定义 ====================

@byzerllm.prompt()
def simple_prompt_test() -> str:
    """
    解释Python中的类和对象

    请包括以下内容：
    1. 类和对象的基本概念
    2. 类的定义方式
    3. 对象的创建和使用
    4. 类属性和实例属性的区别
    5. 方法和特殊方法
    6. 简单的例子
    """

@byzerllm.prompt()
def complex_prompt_test() -> str:
    """
    分析以下Python代码片段，找出潜在的性能问题和改进建议:
    
    ```python
    def calculate_fibonacci(n):
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        else:
            return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
            
    def find_all_fibonacci_less_than(limit):
        result = []
        i = 0
        while True:
            fib = calculate_fibonacci(i)
            if fib >= limit:
                break
            result.append(fib)
            i += 1
        return result
    
    # 计算小于1000的所有斐波那契数
    fibonacci_numbers = find_all_fibonacci_less_than(1000)
    print(fibonacci_numbers)
    ```
    
    请提供详细的代码审查，包括:
    1. 识别现有代码中的性能瓶颈
    2. 提出优化方案
    3. 重写优化后的代码
    4. 分析优化前后的时间复杂度对比
    """

@byzerllm.prompt()
def python_intro() -> str:
    """
    什么是Python?
    
    请简要介绍Python编程语言的主要特点和应用场景。
    """

@byzerllm.prompt()
def list_comprehension() -> str:
    """
    解释Python中的列表推导式
    
    请详细说明列表推导式的语法、优势和常见用例，并提供示例代码。
    """

@byzerllm.prompt()
def exception_handling() -> str:
    """
    如何在Python中处理异常?
    
    请介绍Python异常处理的完整流程，包括try-except-else-finally结构，以及自定义异常的创建方法。
    提供实际的示例代码和最佳实践。
    """

# ==================== 测试函数 ====================

def test_token_usage_stats_model():
    """测试TokenUsageStats模型的基本功能"""
    print("\n" + "="*50)
    print("测试 TokenUsageStats 模型")
    print("="*50)
    
    # 创建一个TokenUsageStats实例
    stats = TokenUsageStats(
        input_tokens=100,
        output_tokens=50,
        input_cost=0.0001,
        output_cost=0.0002
    )
    
    # 测试计算属性
    print(f"输入Token: {stats.input_tokens}")
    print(f"输出Token: {stats.output_tokens}")
    print(f"总Token数: {stats.total_tokens}")
    print(f"输入成本: ${stats.input_cost:.6f}")
    print(f"输出成本: ${stats.output_cost:.6f}")
    print(f"总成本: ${stats.total_cost:.6f}")
    
    # 测试模型序列化
    print("\n模型Json序列化:")
    print(stats.model_dump_json(indent=2))
    
    return stats

def run_prompt_test(
    prompt_func, 
    description: str, 
    llm: byzerllm.ByzerLLM, 
    calculator: TokenCostCalculator,
    show_output: bool = True,
    output_length: int = 100
) -> Dict[str, Any]:
    """
    运行提示测试的通用函数
    
    Args:
        prompt_func: 提示函数
        description: 测试描述
        llm: ByzerLLM实例
        calculator: TokenCostCalculator实例
        show_output: 是否显示输出内容
        output_length: 显示的输出内容长度
        
    Returns:
        Dict: 测试结果字典
    """
    # 创建MetaHolder实例
    meta_holder = MetaHolder()
    
    # 记录开始时间
    start_time = time.monotonic()
    
    # 执行LLM调用
    logger.info(f"执行LLM调用，提示: '{description}'")
    result = prompt_func.with_llm(llm).with_meta(meta_holder).run()
    
    # 记录结束时间
    end_time = time.monotonic()
    elapsed_time = end_time - start_time
    
    # 获取token使用统计
    operation_name = f"Test: {description}"
    stats = calculator.track_token_usage(
        llm=llm,
        meta_holder=meta_holder,
        operation_name=operation_name,
        start_time=start_time,
        end_time=end_time,
        product_mode="lite"
    )
    
    # 打印结果摘要
    print(f"\n测试结果: {description}")
    print(f"输入Token: {stats.input_tokens}")
    print(f"输出Token: {stats.output_tokens}")
    print(f"总Token数: {stats.total_tokens}")
    print(f"总成本: ${stats.total_cost:.6f}")
    print(f"执行时间: {elapsed_time:.2f}秒")
    
    if show_output and result:
        print(f"\n输出内容前{output_length}个字符:")
        print(f"{result[:output_length]}...")
    
    # 更新全局统计
    TOTAL_STATS["total_tests"] += 1
    TOTAL_STATS["total_tokens"] += stats.total_tokens
    TOTAL_STATS["total_cost"] += stats.total_cost
    TOTAL_STATS["total_time"] += elapsed_time
    TOTAL_STATS["tests"].append({
        "description": description,
        "tokens": stats.total_tokens,
        "cost": stats.total_cost,
        "time": elapsed_time
    })
    
    return {
        "description": description,
        "result": result,
        "stats": stats,
        "elapsed_time": elapsed_time
    }

def test_token_calculator_with_simple_prompt():
    """使用简单提示测试TokenCostCalculator"""
    print("\n" + "="*50)
    print("测试 TokenCostCalculator - 简单提示")
    print("="*50)
    
    # 获取LLM实例
    llm = get_single_llm("v3_chat", product_mode="lite")
    logger.info("成功初始化LLM")
    
    # 创建TokenCostCalculator实例
    calculator = TokenCostCalculator(logger_name="TestCalculator")
    logger.info("成功初始化TokenCostCalculator")
    
    # 使用通用函数运行测试
    result = run_prompt_test(
        prompt_func=simple_prompt_test,
        description="解释Python中的类和对象",
        llm=llm,
        calculator=calculator
    )
    
    return result

def test_token_calculator_with_complex_prompt():
    """使用复杂提示测试TokenCostCalculator"""
    print("\n" + "="*50)
    print("测试 TokenCostCalculator - 复杂提示")
    print("="*50)
    
    # 获取LLM实例
    llm = get_single_llm("v3_chat", product_mode="lite")
    
    # 创建TokenCostCalculator实例
    calculator = TokenCostCalculator(logger_name="TestCalculator")
    
    # 使用通用函数运行测试
    result = run_prompt_test(
        prompt_func=complex_prompt_test,
        description="复杂的Fibonacci代码分析",
        llm=llm,
        calculator=calculator
    )
    
    return result

def test_multiple_operations_cumulative_stats():
    """测试多个操作的累计统计功能"""
    print("\n" + "="*50)
    print("测试多个操作的累计统计")
    print("="*50)
    
    # 获取LLM实例
    llm = get_single_llm("v3_chat", product_mode="lite")
    
    # 创建TokenCostCalculator实例
    calculator = TokenCostCalculator(logger_name="TestCalculator")
    
    # 定义多个简单提示对应的函数和描述
    test_cases = [
        (python_intro, "什么是Python?"),
        (list_comprehension, "解释Python中的列表推导式"),
        (exception_handling, "如何在Python中处理异常?")
    ]
    
    # 存储所有操作的统计信息
    all_results = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0
    total_time = 0.0
    
    # 为每个提示执行LLM调用
    for i, (prompt_func, desc) in enumerate(test_cases, 1):
        print(f"\n测试 {i}/{len(test_cases)}: {desc}")
        
        # 使用通用函数运行测试，不显示输出内容
        result = run_prompt_test(
            prompt_func=prompt_func,
            description=desc,
            llm=llm,
            calculator=calculator,
            show_output=False
        )
        
        # 累加统计
        all_results.append(result)
        total_input_tokens += result["stats"].input_tokens
        total_output_tokens += result["stats"].output_tokens
        total_cost += result["stats"].total_cost
        total_time += result["elapsed_time"]
    
    # 打印累计结果
    print("\n" + "-"*40)
    print("累计统计结果:")
    print("-"*40)
    print(f"操作总数: {len(test_cases)}")
    print(f"累计输入Token: {total_input_tokens}")
    print(f"累计输出Token: {total_output_tokens}")
    print(f"累计总Token: {total_input_tokens + total_output_tokens}")
    print(f"累计总成本: ${total_cost:.6f}")
    print(f"总执行时间: {total_time:.2f}秒")
    
    # 打印各个操作的统计
    print("\n各操作明细:")
    for i, result in enumerate(all_results, 1):
        desc = result["description"]
        stats = result["stats"]
        print(f"\n{i}. '{desc}'")
        print(f"   输入Token: {stats.input_tokens}")
        print(f"   输出Token: {stats.output_tokens}")
        print(f"   总Token: {stats.total_tokens}")
        print(f"   成本: ${stats.total_cost:.6f}")
        print(f"   时间: {result['elapsed_time']:.2f}秒")
    
    return all_results

def test_model_info_retrieval():
    """测试模型信息获取功能"""
    print("\n" + "="*50)
    print("测试模型信息获取")
    print("="*50)
    
    # 获取LLM实例
    llm = get_single_llm("v3_chat", product_mode="lite")
    
    # 创建TokenCostCalculator实例
    calculator = TokenCostCalculator(logger_name="TestCalculator")
    
    # 获取模型信息
    model_name, model_info_map = calculator.get_model_info(llm, product_mode="lite")
    
    # 打印模型信息
    print(f"模型名称: {model_name}")
    print("\n价格信息:")
    
    for name, info in model_info_map.items():
        print(f"\n模型: {name}")
        print(f"  输入价格 (每百万token): ${info.get('input_price', 0.0)}")
        print(f"  输出价格 (每百万token): ${info.get('output_price', 0.0)}")
    
    return model_name, model_info_map

def print_summary():
    """打印测试摘要"""
    print("\n" + "="*70)
    print(f"测试摘要")
    print("="*70)
    print(f"总测试数: {TOTAL_STATS['total_tests']}")
    print(f"总Token数: {TOTAL_STATS['total_tokens']}")
    print(f"总成本: ${TOTAL_STATS['total_cost']:.6f}")
    print(f"总执行时间: {TOTAL_STATS['total_time']:.2f}秒")
    
    # 计算每个测试的成本占比
    if TOTAL_STATS['total_cost'] > 0:
        print("\n各测试成本占比:")
        for test in TOTAL_STATS['tests']:
            percentage = (test['cost'] / TOTAL_STATS['total_cost']) * 100
            print(f"- {test['description']}: ${test['cost']:.6f} ({percentage:.1f}%)")
    
    # 保存测试报告到文件
    report_path = os.path.join(os.path.dirname(__file__), "token_cost_test_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("Token计费计算器测试报告\n")
        f.write("="*50 + "\n\n")
        f.write(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"总测试数: {TOTAL_STATS['total_tests']}\n")
        f.write(f"总Token数: {TOTAL_STATS['total_tokens']}\n")
        f.write(f"总成本: ${TOTAL_STATS['total_cost']:.6f}\n")
        f.write(f"总执行时间: {TOTAL_STATS['total_time']:.2f}秒\n\n")
        
        f.write("各测试详情:\n")
        for i, test in enumerate(TOTAL_STATS['tests'], 1):
            f.write(f"\n{i}. {test['description']}\n")
            f.write(f"   Token数: {test['tokens']}\n")
            f.write(f"   成本: ${test['cost']:.6f}\n")
            f.write(f"   时间: {test['time']:.2f}秒\n")
    
    print(f"\n测试报告已保存到: {report_path}")

def main():
    """主函数，运行所有测试"""
    print("="*70)
    print("Token计费计算器功能测试")
    print("="*70)
    print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 运行基础测试
        test_token_usage_stats_model()
        test_model_info_retrieval()
        
        # 运行提示测试
        test_token_calculator_with_simple_prompt()
        test_token_calculator_with_complex_prompt()
        test_multiple_operations_cumulative_stats()
        
        # 打印摘要
        print_summary()
        
        print("\n" + "="*70)
        print(f"所有测试完成 - 结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        if TOTAL_STATS['total_tests'] > 0:
            print_summary()
    except Exception as e:
        print(f"\n\n测试过程中出错: {e}")
        if TOTAL_STATS['total_tests'] > 0:
            print_summary()
        raise

if __name__ == "__main__":
    main() 