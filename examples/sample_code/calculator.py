# examples/sample_code/calculator.py

def add(a, b):
    """Adds two numbers."""
    return a + b

def subtract(a, b):
    """Subtracts second number from first."""
    return a - b

class SimpleCalculator:
    def multiply(self, a, b):
        """Multiplies two numbers."""
        return a * b

    def divide(self, a, b):
        """Divides first number by second. Handles division by zero."""
        if b == 0:
            return "Error: Cannot divide by zero"
        return a / b

# Example usage (optional)
if __name__ == "__main__":
    print(f"Addition: {add(5, 3)}")
    print(f"Subtraction: {subtract(10, 4)}")
    calc = SimpleCalculator()
    print(f"Multiplication: {calc.multiply(6, 7)}")
    print(f"Division: {calc.divide(8, 2)}")
    print(f"Division by zero: {calc.divide(5, 0)}")