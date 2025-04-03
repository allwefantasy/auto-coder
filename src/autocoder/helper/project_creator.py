#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ProjectCreator 类：用于创建示例项目的工具类
可以灵活配置项目结构、文件内容和 Git 初始化选项
"""

import os
import shutil
import git
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod


class FileCreator(ABC):
    """
    文件创建抽象基类，定义了创建项目文件的接口
    """
    
    @abstractmethod
    def create_files(self, project_dir: str) -> None:
        """
        在项目目录中创建必要的文件
        
        参数:
            project_dir: 项目目录路径
        """
        pass
    
    @abstractmethod
    def get_file_paths(self, project_dir: str) -> List[str]:
        """
        获取创建的文件路径列表，用于配置文件中引用
        
        参数:
            project_dir: 项目目录路径
            
        返回:
            List[str]: 文件路径的列表
        """
        pass
    
    @property
    @abstractmethod
    def project_type(self) -> str:
        """返回项目类型标识"""
        pass


class PythonFileCreator(FileCreator):
    """
    Python 计算器项目文件创建器
    """
    
    def create_files(self, project_dir: str) -> None:
        """创建 Python 项目文件"""
        # 创建计算器文件
        self._create_calculator_file(project_dir)
        # 创建主程序文件
        self._create_main_file(project_dir)
    
    def get_file_paths(self, project_dir: str) -> List[str]:
        """获取 Python 项目的主要文件路径"""
        abs_project_dir = os.path.abspath(project_dir)
        return [
            os.path.join(abs_project_dir, "calculator.py"),
            os.path.join(abs_project_dir, "main.py")
        ]
    
    @property
    def project_type(self) -> str:
        """返回项目类型"""
        return "py"
    
    def _create_calculator_file(self, project_dir: str) -> None:
        """创建计算器示例文件"""
        calculator_path = os.path.join(project_dir, "calculator.py")
        calculator_content = """
class Calculator:
    def __init__(self):
        self.history = []
        
    def add(self, a, b):
        '''加法函数'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a, b):
        '''减法函数'''
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
        
    def clear_history(self):
        '''清除历史记录'''
        self.history = []
"""
        
        with open(calculator_path, "w", encoding="utf-8") as f:
            f.write(calculator_content)
    
    def _create_main_file(self, project_dir: str) -> None:
        """创建主程序文件"""
        main_path = os.path.join(project_dir, "main.py")
        main_content = """
from calculator import Calculator
  from abc import ABC, abstractmethod
def main():
    calc = Calculator()
    
    # 进行一些计算
    print(calc.add(5, 3))
    print(calc.subtract(10, 4))
    
    # 打印历史记录
    print("计算历史:")
    for item in calc.history:
        print(item)

if __name__ == "__main__":
    main()
"""
        
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_content)


class ReactJSFileCreator(FileCreator):
    """
    Vite + React TypeScript 计算器项目文件创建器
    """
    
    def create_files(self, project_dir: str) -> None:
        """创建 Vite + React TypeScript 项目文件"""
        # 创建 package.json
        self._create_package_json(project_dir)
        # 创建 index.html
        self._create_index_html(project_dir)
        # 创建 vite.config.ts
        self._create_vite_config(project_dir)
        # 创建 src 目录
        src_dir = os.path.join(project_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        # 创建 App.tsx 和 Calculator.tsx 组件
        self._create_app_tsx(src_dir)
        self._create_calculator_component(src_dir)
        self._create_main_tsx(src_dir)
        # 创建 tsconfig.json 和 tsconfig.node.json
        self._create_tsconfig_json(project_dir)
        self._create_tsconfig_node_json(project_dir)
        # 创建 .gitignore
        self._create_gitignore(project_dir)
    
    def get_file_paths(self, project_dir: str) -> List[str]:
        """获取 Vite + React TypeScript 项目的主要文件路径"""
        abs_project_dir = os.path.abspath(project_dir)
        return [
            os.path.join(abs_project_dir, "package.json"),
            os.path.join(abs_project_dir, "vite.config.ts"),
            os.path.join(abs_project_dir, "tsconfig.json"),
            os.path.join(abs_project_dir, "src", "App.tsx"),
            os.path.join(abs_project_dir, "src", "Calculator.tsx"),
            os.path.join(abs_project_dir, "src", "main.tsx")
        ]
    
    @property
    def project_type(self) -> str:
        """返回项目类型"""
        return "tsx"
    
    def _create_index_html(self, project_dir: str) -> None:
        """创建 index.html 文件"""
        index_html_path = os.path.join(project_dir, "index.html")
        index_html_content = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Vite + React Calculator</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>"""
        with open(index_html_path, "w", encoding="utf-8") as f:
            f.write(index_html_content)
    
    def _create_package_json(self, project_dir: str) -> None:
        """创建 package.json 文件"""
        package_path = os.path.join(project_dir, "package.json")
        package_content = """{
  "name": "calculator-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.15",
    "@types/react-dom": "^18.2.7",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@vitejs/plugin-react": "^4.0.3",
    "eslint": "^8.45.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.3",
    "typescript": "^5.0.2",
    "vite": "^4.4.5"
  }
}"""
        with open(package_path, "w", encoding="utf-8") as f:
            f.write(package_content)
    
    def _create_vite_config(self, project_dir: str) -> None:
        """创建 vite.config.ts 文件"""
        vite_config_path = os.path.join(project_dir, "vite.config.ts")
        vite_config_content = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
})
"""
        with open(vite_config_path, "w", encoding="utf-8") as f:
            f.write(vite_config_content)
    
    def _create_tsconfig_json(self, project_dir: str) -> None:
        """创建 tsconfig.json 文件"""
        tsconfig_path = os.path.join(project_dir, "tsconfig.json")
        tsconfig_content = """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}"""
        with open(tsconfig_path, "w", encoding="utf-8") as f:
            f.write(tsconfig_content)
    
    def _create_tsconfig_node_json(self, project_dir: str) -> None:
        """创建 tsconfig.node.json 文件"""
        tsconfig_node_path = os.path.join(project_dir, "tsconfig.node.json")
        tsconfig_node_content = """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true
  },
  "include": ["vite.config.ts"]
}"""
        with open(tsconfig_node_path, "w", encoding="utf-8") as f:
            f.write(tsconfig_node_content)
    
    def _create_gitignore(self, project_dir: str) -> None:
        """创建 .gitignore 文件"""
        gitignore_path = os.path.join(project_dir, ".gitignore")
        gitignore_content = """# Logs
logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*

node_modules
dist
dist-ssr
*.local

# Editor directories and files
.vscode/*
!.vscode/extensions.json
.idea
.DS_Store
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?
"""
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write(gitignore_content)
    
    def _create_app_tsx(self, src_dir: str) -> None:
        """创建 App.tsx 文件"""
        app_path = os.path.join(src_dir, "App.tsx")
        app_content = """import { useState } from 'react'
import Calculator from './Calculator'
import './App.css'

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Vite + React Calculator</h1>
      </header>
      <main>
        <Calculator />
      </main>
    </div>
  )
}

export default App
"""
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(app_content)
        
        # 创建 App.css 文件
        app_css_path = os.path.join(src_dir, "App.css")
        app_css_content = """.App {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}

.App-header {
  margin-bottom: 2rem;
}

.App-header h1 {
  font-size: 2.5em;
  line-height: 1.1;
}
"""
        with open(app_css_path, "w", encoding="utf-8") as f:
            f.write(app_css_content)
    
    def _create_calculator_component(self, src_dir: str) -> None:
        """创建 Calculator.tsx 组件"""
        calculator_path = os.path.join(src_dir, "Calculator.tsx")
        calculator_content = """import { useState } from 'react'
import './Calculator.css'

interface CalculatorProps {}

const Calculator: React.FC<CalculatorProps> = () => {
  const [display, setDisplay] = useState<string>('0')
  const [equation, setEquation] = useState<string>('')

  const handleNumber = (num: string) => {
    if (display === '0') {
      setDisplay(num)
    } else {
      setDisplay(display + num)
    }
  }

  const handleOperator = (operator: string) => {
    setEquation(display + ' ' + operator + ' ')
    setDisplay('0')
  }

  const handleEqual = () => {
    try {
      const result = eval(equation + display)
      setDisplay(result.toString())
      setEquation('')
    } catch (error) {
      setDisplay('Error')
      setEquation('')
    }
  }

  const handleClear = () => {
    setDisplay('0')
    setEquation('')
  }

  return (
    <div className="calculator">
      <div className="display">
        <div className="equation">{equation}</div>
        <div className="current">{display}</div>
      </div>
      <div className="buttons">
        <button onClick={handleClear}>C</button>
        <button onClick={() => handleOperator('/')}>/</button>
        <button onClick={() => handleOperator('*')}>×</button>
        <button onClick={() => handleNumber('7')}>7</button>
        <button onClick={() => handleNumber('8')}>8</button>
        <button onClick={() => handleNumber('9')}>9</button>
        <button onClick={() => handleOperator('-')}>-</button>
        <button onClick={() => handleNumber('4')}>4</button>
        <button onClick={() => handleNumber('5')}>5</button>
        <button onClick={() => handleNumber('6')}>6</button>
        <button onClick={() => handleOperator('+')}>+</button>
        <button onClick={() => handleNumber('1')}>1</button>
        <button onClick={() => handleNumber('2')}>2</button>
        <button onClick={() => handleNumber('3')}>3</button>
        <button onClick={handleEqual}>=</button>
        <button onClick={() => handleNumber('0')}>0</button>
        <button onClick={() => handleNumber('.')}>.</button>
      </div>
    </div>
  )
}

export default Calculator
"""
        with open(calculator_path, "w", encoding="utf-8") as f:
            f.write(calculator_content)
        
        # 创建 Calculator.css 文件
        calculator_css_path = os.path.join(src_dir, "Calculator.css")
        calculator_css_content = """.calculator {
  width: 300px;
  margin: 0 auto;
  border: 1px solid #ccc;
  border-radius: 5px;
  padding: 10px;
  background-color: #f7f7f7;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
}

.display {
  background-color: #fff;
  border: 1px solid #ddd;
  border-radius: 3px;
  margin-bottom: 10px;
  padding: 10px;
  text-align: right;
  min-height: 60px;
}

.equation {
  color: #777;
  font-size: 14px;
  min-height: 20px;
}

.current {
  font-size: 24px;
  font-weight: bold;
  margin-top: 5px;
}

.buttons {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 5px;
}

button {
  background-color: #e0e0e0;
  border: 1px solid #ccc;
  border-radius: 3px;
  font-size: 18px;
  padding: 10px;
  cursor: pointer;
  transition: background-color 0.2s;
}

button:hover {
  background-color: #d0d0d0;
}

button:active {
  background-color: #c0c0c0;
}
"""
        with open(calculator_css_path, "w", encoding="utf-8") as f:
            f.write(calculator_css_content)
    
    def _create_main_tsx(self, src_dir: str) -> None:
        """创建 main.tsx 文件"""
        main_path = os.path.join(src_dir, "main.tsx")
        main_content = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""
        with open(main_path, "w", encoding="utf-8") as f:
            f.write(main_content)
        
        # 创建 index.css 文件
        index_css_path = os.path.join(src_dir, "index.css")
        index_css_content = """:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;

  color-scheme: light dark;
  color: rgba(255, 255, 255, 0.87);
  background-color: #242424;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

@media (prefers-color-scheme: light) {
  :root {
    color: #213547;
    background-color: #ffffff;
  }
}

body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}

* {
  box-sizing: border-box;
}
"""
        with open(index_css_path, "w", encoding="utf-8") as f:
            f.write(index_css_content)


class FileCreatorFactory:
    """
    文件创建器工厂类，根据项目类型返回对应的文件创建器
    """
    
    @staticmethod
    def get_creator(project_type: str) -> FileCreator:
        """
        获取指定类型的文件创建器
        
        参数:
            project_type: 项目类型，支持 'python'/'py' 或 'react'/'js'
        
        返回:
            FileCreator: 对应的文件创建器实例
        
        异常:
            ValueError: 不支持的项目类型
        """
        project_type = project_type.lower()
        
        if project_type in ('python', 'py'):
            return PythonFileCreator()
        elif project_type in ('react', 'reactjs', 'js'):
            return ReactJSFileCreator()
        else:
            raise ValueError(f"不支持的项目类型: {project_type}")


class ProjectCreator:
    """
    创建示例项目的工具类，支持自定义项目结构和内容
    """
    
    def __init__(
        self, 
        project_name: str = "test_project",
        project_type: str = "python",
        git_init: bool = True,
        git_user_email: str = "example@example.com",
        git_user_name: str = "Example User",
        create_actions: bool = True,
        query: str = "给计算器添加乘法和除法功能",
        model: str = "v3_chat",
        product_mode: str = "lite"
    ):
        """
        初始化项目创建器
        
        参数:
            project_name: 项目名称和目录名
            project_type: 项目类型，支持 'python'/'py' 或 'react'/'js'
            git_init: 是否初始化 Git 仓库
            git_user_email: Git 用户邮箱
            git_user_name: Git 用户名
            create_actions: 是否创建 actions 目录和配置文件
            query: 默认查询内容
            model: 使用的模型名称
            product_mode: 模型的产品模式
        """
        self.project_name = project_name
        self.git_init = git_init
        self.git_user_email = git_user_email
        self.git_user_name = git_user_name
        self.create_actions = create_actions
        self.query = query
        self.model = model
        self.product_mode = product_mode
        
        # 使用工厂获取文件创建器
        self.file_creator = FileCreatorFactory.get_creator(project_type)
        
    def create_project(self) -> str:
        """
        创建一个示例项目目录和文件
        
        返回:
            str: 项目目录的绝对路径
        """
        # 创建项目目录
        project_dir = self.project_name
        if os.path.exists(project_dir):
            shutil.rmtree(project_dir)
        os.makedirs(project_dir)
        
        # 使用文件创建器创建项目文件
        self.file_creator.create_files(project_dir)
        
        # 创建配置文件
        if self.create_actions:
            self._create_actions_files(project_dir)
        
        # 初始化 Git 仓库
        if self.git_init:
            self._init_git_repo(project_dir)
        
        return os.path.abspath(project_dir)
    
    def _create_actions_files(self, project_dir: str) -> None:
        """创建 actions 目录和配置文件"""
        # 创建 actions 目录
        actions_dir = os.path.join(project_dir, "actions")
        os.makedirs(actions_dir, exist_ok=True)
        
        # 创建 base 目录
        base_dir = os.path.join(actions_dir, "base")
        os.makedirs(base_dir, exist_ok=True)
        
        # 创建 base.yml 文件
        self._create_base_yml(project_dir, base_dir)
        
        # 创建 chat_action.yml 文件
        self._create_chat_action_yml(project_dir, actions_dir)
    
    def _create_base_yml(self, project_dir: str, base_dir: str) -> None:
        """创建 base.yml 配置文件"""
        base_yml_path = os.path.join(base_dir, "base.yml")
        abs_project_dir = os.path.abspath(project_dir)
        base_yml_content = f"""source_dir: {abs_project_dir}
target_file: {os.path.join(abs_project_dir, "output.txt")}
project_type: {self.file_creator.project_type}

model: {self.model}
index_model: {self.model}

index_filter_level: 1
index_model_max_input_length: 100000
model_max_input_length: 120000
index_filter_workers: 100
index_build_workers: 100

skip_build_index: false
execute: true
auto_merge: editblock
human_as_model: false
"""
        
        with open(base_yml_path, "w", encoding="utf-8") as f:
            f.write(base_yml_content)
    
    def _create_chat_action_yml(self, project_dir: str, actions_dir: str) -> None:
        """创建 chat_action.yml 配置文件"""
        chat_action_path = os.path.join(actions_dir, "000000000001_chat_action.yml")
        
        # 获取文件路径列表
        file_paths = self.file_creator.get_file_paths(project_dir)
        file_urls = "\n".join([f"- {path}" for path in file_paths])
        
        chat_action_content = f"""add_updated_urls: []
auto_merge: editblock
chat_model: {self.model}
code_model: {self.model}
enable_active_context: true
enable_global_memory: false
enable_task_history: true
generate_times_same_model: 1
human_as_model: false
include_file:
- ./base/base.yml
include_project_structure: true
model: {self.model}
product_mode: {self.product_mode}
query: '{self.query}'
silence: false
skip_build_index: true
skip_confirm: true
skip_filter_index: false
urls:
{file_urls}
"""
        
        with open(chat_action_path, "w", encoding="utf-8") as f:
            f.write(chat_action_content)
    
    def _init_git_repo(self, project_dir: str) -> None:
        """初始化 Git 仓库"""
        try:
            # 初始化 Git 仓库
            repo = git.Repo.init(project_dir)
            
            # 设置用户信息
            config_writer = repo.config_writer()
            config_writer.set_value("user", "email", self.git_user_email)
            config_writer.set_value("user", "name", self.git_user_name)
            config_writer.release()
            
            # 添加所有文件
            repo.git.add(A=True)
            
            # 提交
            repo.index.commit("Initial commit")
            
            print("Git 仓库初始化成功")
        except Exception as e:
            print(f"Git 初始化失败: {e}")
