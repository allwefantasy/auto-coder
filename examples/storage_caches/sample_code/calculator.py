
class Calculator:
    def __init__(self):
        self.history = []
        self.version = "2.0"  # 添加了版本信息
        
    def add(self, a: int, b: int) -> int:
        '''改进的加法函数'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        '''改进的减法函数'''
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
        
    def multiply(self, a: int, b: int) -> int:
        '''乘法函数'''
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
        
    def divide(self, a: int, b: int) -> float:
        '''除法函数'''
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
        
    def power(self, a: int, b: int) -> int:
        '''新增: 幂运算'''
        result = a ** b
        self.history.append(f"{a} ** {b} = {result}")
        return result
