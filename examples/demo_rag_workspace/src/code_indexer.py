
import os
import re
from typing import List, Dict, Any

class CodeIndexer:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.index = {}
        self.file_extensions = ['.py', '.java', '.js', '.ts', '.c', '.cpp', '.h', '.cs', '.go']
        
    def build_index(self):        
        for root, dirs, files in os.walk(self.root_dir):
            for file in files:
                if any(file.endswith(ext) for ext in self.file_extensions):
                    file_path = os.path.join(root, file)
                    self._index_file(file_path)
        
        print(f"索引构建完成，共索引了 {len(self.index)} 个文件")
        return self.index
    
    def _index_file(self, file_path: str):        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 提取文件中的类和函数定义
            classes = self._extract_classes(content)
            functions = self._extract_functions(content)
            
            # 存储到索引中
            rel_path = os.path.relpath(file_path, self.root_dir)
            self.index[rel_path] = {
                'classes': classes,
                'functions': functions,
                'size': len(content),
                'last_modified': os.path.getmtime(file_path)
            }
        except Exception as e:
            print(f"索引文件 {file_path} 时出错: {str(e)}")
    
    def _extract_classes(self, content: str) -> List[Dict[str, Any]]:
        classes = []
        # 简单的正则表达式匹配，实际项目中可能需要更复杂的解析
        class_pattern = r'class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            class_name = match.group(1)
            classes.append({
                'name': class_name,
                'position': match.start()
            })
        return classes
    
    def _extract_functions(self, content: str) -> List[Dict[str, Any]]:
        functions = []
        # 简单的正则表达式匹配，实际项目中可能需要更复杂的解析
        func_pattern = r'def\s+(\w+)'
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            functions.append({
                'name': func_name,
                'position': match.start()
            })
        return functions
    
    def search(self, query: str) -> List[Dict[str, Any]]:
        results = []
        query = query.lower()
        
        for file_path, file_info in self.index.items():
            # 检查文件名
            if query in file_path.lower():
                results.append({
                    'file': file_path,
                    'match_type': 'filename',
                    'relevance': 0.9
                })
                
            # 检查类名
            for cls in file_info['classes']:
                if query in cls['name'].lower():
                    results.append({
                        'file': file_path,
                        'match_type': 'class',
                        'class': cls['name'],
                        'relevance': 0.8
                    })
                    
            # 检查函数名
            for func in file_info['functions']:
                if query in func['name'].lower():
                    results.append({
                        'file': file_path,
                        'match_type': 'function',
                        'function': func['name'],
                        'relevance': 0.7
                    })
        
        # 按相关性排序
        results.sort(key=lambda x: x['relevance'], reverse=True)
        return results

# 使用示例
if __name__ == "__main__":
    indexer = CodeIndexer("./")
    indexer.build_index()
    results = indexer.search("monitor")
    for result in results:
        print(result)
