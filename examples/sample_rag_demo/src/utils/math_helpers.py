# 数学辅助函数

def multiply(a, b):
    """计算两个数的乘积"""
    return a * b

def divide(a, b):
    """计算两个数的商"""
    if b == 0:
        raise ValueError("除数不能为零")
    return a / b

def is_even(n):
    """判断一个数是否为偶数"""
    return n % 2 == 0