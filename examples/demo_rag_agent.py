"""
演示 LongContextRAG 工具的使用
展示如何在 BaseAgent 中使用 SearchTool 和 RecallTool
"""
import os
import argparse
import shutil
from loguru import logger
import byzerllm
from typing import Dict, Any, List, Union, Optional

from autocoder.agent.base_agentic.base_agent import BaseAgent
from autocoder.agent.base_agentic.types import AgentRequest
from autocoder.common import AutoCoderArgs
from autocoder.common import SourceCodeList, SourceCode
from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules
from autocoder.rag.tools import register_search_tool, register_recall_tool

# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description="演示 LongContextRAG 工具的使用")    
    parser.add_argument("--model", type=str, default="v3_chat",
                        help="使用的LLM模型")
    parser.add_argument("--product_mode", type=str, default="lite",
                        help="产品模式")
    parser.add_argument("--event_file", type=str, default="",
                        help="事件文件路径")
    return parser.parse_args()

# 准备演示环境
def prepare_demo_environment():    
    base_dir = os.path.join(os.getcwd(), "demo_rag_workspace")  
    
    # 创建示例源代码文件
    os.makedirs(os.path.join(base_dir, "src"), exist_ok=True)
    with open(os.path.join(base_dir, "src", "file_monitor.py"), "w") as f:
        f.write("""
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback=None):
        self.callback = callback
        
    def on_modified(self, event):
        if not event.is_directory:
            print(f"文件被修改: {event.src_path}")
            if self.callback:
                self.callback(event.src_path)
                
    def on_created(self, event):
        if not event.is_directory:
            print(f"文件被创建: {event.src_path}")
            if self.callback:
                self.callback(event.src_path)
                
    def on_deleted(self, event):
        if not event.is_directory:
            print(f"文件被删除: {event.src_path}")
            if self.callback:
                self.callback(event.src_path)

class FileMonitor:
    def __init__(self, path, callback=None):
        self.path = path
        self.observer = Observer()
        self.handler = FileChangeHandler(callback)
        self.running = False
        
    def start(self):
        self.observer.schedule(self.handler, self.path, recursive=True)
        self.observer.start()
        self.running = True
        print(f"开始监控目录: {self.path}")
        
    def stop(self):
        if self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False
            print(f"停止监控目录: {self.path}")
            
    def is_running(self):
        return self.running

# 使用示例
if __name__ == "__main__":
    def on_file_change(file_path):
        print(f"检测到文件变化: {file_path}")
        
    monitor = FileMonitor("./", on_file_change)
    try:
        monitor.start()
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
""")
    
    with open(os.path.join(base_dir, "src", "code_indexer.py"), "w") as f:
        f.write("""
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
""")
    
    # 创建示例文档文件
    os.makedirs(os.path.join(base_dir, "docs"), exist_ok=True)
    with open(os.path.join(base_dir, "docs", "file_monitor_guide.md"), "w") as f:
        f.write("""
# 文件监控系统使用指南

## 概述

文件监控系统用于实时监控目录中的文件变化，并在文件被创建、修改或删除时触发回调函数。

## 主要功能

1. 监控指定目录及其子目录中的文件变化
2. 支持自定义回调函数处理文件变化事件
3. 可以启动和停止监控

## 使用方法

### 初始化监控器

```python
from file_monitor import FileMonitor

# 创建监控器实例
monitor = FileMonitor("/path/to/directory", callback_function)
```

### 启动监控

```python
# 启动监控
monitor.start()
```

### 停止监控

```python
# 停止监控
monitor.stop()
```

### 检查监控状态

```python
# 检查监控是否正在运行
is_running = monitor.is_running()
```

## 注意事项

1. 监控器使用 watchdog 库实现，确保已安装该依赖
2. 回调函数应该是轻量级的，避免在回调中执行耗时操作
3. 在程序退出前记得调用 stop() 方法停止监控
""")
    
    with open(os.path.join(base_dir, "docs", "code_indexer_guide.md"), "w") as f:
        f.write("""
# 代码索引器使用指南

## 概述

代码索引器用于构建代码库的索引，支持按关键词搜索代码中的类、函数和文件。

## 主要功能

1. 索引多种编程语言的源代码文件
2. 提取代码中的类和函数定义
3. 支持按关键词搜索代码库

## 使用方法

### 初始化索引器

```python
from code_indexer import CodeIndexer

# 创建索引器实例
indexer = CodeIndexer("/path/to/code/directory")
```

### 构建索引

```python
# 构建代码索引
indexer.build_index()
```

### 搜索代码

```python
# 按关键词搜索
results = indexer.search("keyword")

# 处理搜索结果
for result in results:
    print(result)
```

## 支持的文件类型

代码索引器支持以下文件类型：
- Python (.py)
- Java (.java)
- JavaScript (.js)
- TypeScript (.ts)
- C (.c)
- C++ (.cpp, .h)
- C# (.cs)
- Go (.go)

## 注意事项

1. 索引构建过程可能较慢，特别是对于大型代码库
2. 搜索结果按相关性排序，文件名匹配的相关性最高
3. 当前实现使用简单的正则表达式匹配，可能无法处理复杂的代码结构
""")
    
    logger.info(f"创建演示环境于: {base_dir}")
    return base_dir

def main():
    # 解析参数
    args = parse_args()
    
    # 准备演示环境
    source_dir = prepare_demo_environment()
    os.chdir(source_dir)    
    
    logger.info(f"已准备演示环境: {source_dir}")    
    
    # 1. 初始化FileMonitor（必须最先进行）
    try:        
        monitor = FileMonitor(source_dir)
        if not monitor.is_running():
            monitor.start()
            logger.info(f"文件监控已启动: {source_dir}")
        else:
            logger.info(f"文件监控已在运行中: {monitor.root_dir}")
    except Exception as e:
        logger.error(f"初始化文件监控出错: {e}")
    
    # 2. 加载规则文件
    try:        
        rules = get_rules(source_dir)
        logger.info(f"已加载规则: {len(rules)} 条")
    except Exception as e:
        logger.error(f"加载规则出错: {e}")
    
    # 3. 加载tokenizer (必须在前两步之后)
    from autocoder.auto_coder_runner import load_tokenizer
    load_tokenizer()
    logger.info("Tokenizer加载完成")
    
    # 4. 初始化LLM
    from autocoder.utils.llms import get_single_llm
    llm = get_single_llm(args.model, product_mode=args.product_mode)
    logger.info(f"LLM初始化完成: {llm.default_model_name}")
    
    # 5. 配置AutoCoderArgs        
    agent_args = AutoCoderArgs(
        source_dir=source_dir,
        model=args.model,
        product_mode=args.product_mode,
        event_file=args.event_file or os.path.join(source_dir, "events.json"),        
        doc_dir=source_dir  # 设置文档目录，供RAG工具使用
    )
    
    # 准备源代码列表
    files = SourceCodeList(sources=[
        SourceCode(
            module_name="src/file_monitor.py",
            source_code=open(os.path.join(source_dir, "src", "file_monitor.py")).read()
        ), 
        SourceCode(
            module_name="src/code_indexer.py",
            source_code=open(os.path.join(source_dir, "src", "code_indexer.py")).read()
        ),
        SourceCode(
            module_name="docs/file_monitor_guide.md",
            source_code=open(os.path.join(source_dir, "docs", "file_monitor_guide.md")).read()
        ),
        SourceCode(
            module_name="docs/code_indexer_guide.md",
            source_code=open(os.path.join(source_dir, "docs", "code_indexer_guide.md")).read()
        )
    ])
    
    # 6. 创建一个自定义Agent来演示RAG工具的使用
    from autocoder.rag.long_context_rag import LongContextRAG
    class RAGDemoAgent(BaseAgent):
        """
        演示用的Agent，展示SearchTool和RecallTool的使用
        """
        def __init__(self, name: str, 
            llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], 
            files: SourceCodeList, 
            args: AutoCoderArgs, 
            conversation_history: Optional[List[Dict[str, Any]]] = None):
            super().__init__(name, llm, files, args, conversation_history, default_tools_list=["read_file"])
            self.rag = LongContextRAG(llm=llm, args=args, path=args.source_dir)
            # 注册RAG工具
            # register_search_tool()
            register_recall_tool()
            
    # 7. 创建Agent实例
    rag_demo_agent = RAGDemoAgent(
        name="RAGDemoAgent",
        llm=llm,
        files=SourceCodeList(sources=[]),
        args=agent_args,
        conversation_history=[]
    )    

    rag_demo_agent.who_am_i('''
    我是一个基于知识库的智能助手，我的核心能力是通过检索增强生成（RAG）技术来回答用户问题。

    我的工作流程如下：
    1. 当用户提出问题时，我会首先理解问题的核心意图和关键信息需求
    2. 我会从多个角度分析问题，确定最佳的检索策略和关键词    
    4. 我会多次使用召回工具 recall 获取与问题最相关的详细内容，如果有必要我可能还会使用 read_file 来获得更完整的细信息，直到我觉得信息已经足够回答用户了。
    5. 我会综合分析检索到的信息，确保信息的完整性和相关性
    6. 我会持续从不同角度进行搜索和召回，直到我确信已经获取了足够的信息来回答用户问题
    7. 我会基于检索到的信息生成准确、全面且有条理的回答

    我的优势：
    - 我不依赖于预训练知识，而是直接从最新的知识库中获取信息
    - 我能够提供基于事实的、有出处的回答，并且可以引用源代码和文档
    - 我能够处理复杂的技术问题，特别是与代码实现相关的问题
    - 我会清晰地区分哪些信息来自知识库，哪些是我的推理或建议

    在回答问题时，我会：
    - 明确指出信息的来源（如文件路径等）
    - 优先使用知识库中的信息，避免生成可能不准确的内容
    - 当知识库中没有足够信息时，我会坦诚告知用户，并提供基于已有信息的最佳建议
    - 提供有条理、易于理解的回答，必要时使用代码示例、列表或表格增强可读性    
    ''')
    
    # 8. 演示使用SearchTool
    logger.info("开始演示SearchTool的使用...")
    
#     search_query = "请使用搜索工具查找与文件监控相关的代码文件："
#     search_request = AgentRequest(user_input=f"""
# {search_query}

# <search>
# <query>文件监控系统实现</query>
# <max_files>3</max_files>
# </search>
# """)
    
#     logger.info(f"用户输入: {search_query}")
#     logger.info("运行Agent...")
#     rag_demo_agent.run_in_terminal(search_request)
    
    # 9. 演示使用RecallTool
#     logger.info("开始演示RecallTool的使用...")
    
    recall_query = "找到系统里工具获取与文件监控相关的代码内容"
    recall_request = AgentRequest(user_input=f"""
{recall_query}
""")
    
    logger.info(f"用户输入: {recall_query}")
    logger.info("运行Agent...")
    rag_demo_agent.run_in_terminal(recall_request)
    
    # 10. 清理环境
    logger.info(f"演示完成，保留演示环境以供检查: {source_dir}")
    logger.info("如需清理环境，请手动删除该目录")

if __name__ == "__main__":
    main()
