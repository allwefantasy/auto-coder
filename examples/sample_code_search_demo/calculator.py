
class Calculator:
    def __init__(self):
        self.history = []
        
    def add(self, a: int, b: int) -> int:
        '''加法函数'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        '''减法函数'''
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
