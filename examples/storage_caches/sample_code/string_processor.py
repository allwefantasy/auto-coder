
class StringProcessor:
    @staticmethod
    def reverse(text: str) -> str:
        '''反转字符串'''
        return text[::-1]
    
    @staticmethod
    def capitalize(text: str) -> str:
        '''首字母大写'''
        return text.capitalize()
    
    @staticmethod
    def count_words(text: str) -> int:
        '''计算单词数量'''
        return len(text.split())
    
    @staticmethod
    def format_name(first_name: str, last_name: str) -> str:
        '''格式化姓名'''
        return f"{last_name}, {first_name}"
