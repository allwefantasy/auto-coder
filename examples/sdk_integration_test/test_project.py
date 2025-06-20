#!/usr/bin/env python3
"""
SDK 集成测试项目

用于验证 Auto-Coder SDK 的功能是否正常工作
"""

def hello_world():
    """简单的Hello World函数"""
    print("Hello, World!")

def calculate_sum(a, b):
    """计算两个数的和"""
    return a + b

def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

if __name__ == "__main__":
    hello_world()
    print(f"Sum: {calculate_sum(3, 5)}")
    print(f"Fibonacci(10): {fibonacci(10)}") 