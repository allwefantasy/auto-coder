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
    React TypeScript 计算器项目文件创建器
    """
    
    def create_files(self, project_dir: str) -> None:
        """创建 React TypeScript 项目文件"""
        # 创建 package.json
        self._create_package_json(project_dir)
        # 创建 index.html
        self._create_index_html(project_dir)
        # 创建 src 目录
        src_dir = os.path.join(project_dir, "src")
        os.makedirs(src_dir, exist_ok=True)
        # 创建 App.tsx 和 Calculator.tsx 组件
        self._create_app_tsx(src_dir)
        self._create_calculator_component(src_dir)
        self._create_index_tsx(src_dir)
        # 创建 tsconfig.json
        self._create_tsconfig_json(project_dir)
    
    def get_file_paths(self, project_dir: str) -> List[str]:
        """获取 React TypeScript 项目的主要文件路径"""
        abs_project_dir = os.path.abspath(project_dir)
        return [
            os.path.join(abs_project_dir, "package.json"),
            os.path.join(abs_project_dir, "tsconfig.json"),
            os.path.join(abs_project_dir, "src", "App.tsx"),
            os.path.join(abs_project_dir, "src", "Calculator.tsx"),
            os.path.join(abs_project_dir, "src", "index.tsx")
        ]
    
    @property
    def project_type(self) -> str:
        """返回项目类型"""
        return "tsx"
    
    def _create_index_html(self, project_dir: str) -> None:
        """创建 index.html 文件"""
        index_html_path = os.path.join(project_dir, "public", "index.html")
        os.makedirs(os.path.dirname(index_html_path), exist_ok=True)
        index_html_content = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="theme-color" content="#000000" />
    <meta name="description" content="React Calculator App" />
    <title>React Calculator</title>
  </head>
  <body>
    <noscript>You need to enable JavaScript to run this app.</noscript>
    <div id="root"></div>
  </body>
</html>"""
        with open(index_html_path, "w", encoding="utf-8") as f:
            f.write(index_html_content)
    
    def _create_package_json(self, project_dir: str) -> None:
        """创建 package.json 文件"""
        package_path = os.path.join(project_dir, "package.json")
        package_content = """{
  "name": "calculator-app",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1",
    "@types/node": "^16.18.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^4.9.5"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test",
    "eject": "react-scripts eject"
  },
  "eslintConfig": {
    "extends": [
      "react-app",
      "react-app/jest"
    ]
  },
  "browserslist": {
    "production": [
      ">0.2%",
      "not dead",
      "not op_mini all"
    ],
    "development": [
      "last 1 chrome version",
      "last 1 firefox version",
      "last 1 safari version"
    ]
  }
}"""
        with open(package_path, "w", encoding="utf-8") as f:
            f.write(package_content)
    
    def _create_tsconfig_json(self, project_dir: str) -> None:
        """创建 tsconfig.json 文件"""
        tsconfig_path = os.path.join(project_dir, "tsconfig.json")
        tsconfig_content = """{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "esnext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}"""
        with open(tsconfig_path, "w", encoding="utf-8") as f:
            f.write(tsconfig_content)
    
    def _create_app_tsx(self, src_dir: str) -> None:
        """创建 App.tsx 文件"""
        app_path = os.path.join(src_dir, "App.tsx")
        app_content = """import React from 'react';
import Calculator from './Calculator';

const App: React.FC = () => {
  return (
    <div className="App">
      <header className="App-header">
        <h1>React Calculator</h1>
      </header>
      <main>
        <Calculator />
      </main>
    </div>
  );
};

export default App;"""
        with open(app_path, "w", encoding="utf-8") as f:
            f.write(app_content)
    
    def _create_calculator_component(self, src_dir: str) -> None:
        """创建 Calculator.tsx 组件"""
        calculator_path = os.path.join(src_dir, "Calculator.tsx")
        calculator_content = """import React, { useState } from 'react';

interface CalculatorProps {}

const Calculator: React.FC<CalculatorProps> = () => {
  const [display, setDisplay] = useState<string>('0');
  const [equation, setEquation] = useState<string>('');

  const handleNumber = (num: string) => {
    if (display === '0') {
      setDisplay(num);
    } else {
      setDisplay(display + num);
    }
  };

  const handleOperator = (operator: string) => {
    setEquation(display + ' ' + operator + ' ');
    setDisplay('0');
  };

  const handleEqual = () => {
    try {
      const result = eval(equation + display);
      setDisplay(result.toString());
      setEquation('');
    } catch (error) {
      setDisplay('Error');
      setEquation('');
    }
  };

  const handleClear = () => {
    setDisplay('0');
    setEquation('');
  };

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
  );
};

export default Calculator;"""
        with open(calculator_path, "w", encoding="utf-8") as f:
            f.write(calculator_content)
    
    def _create_index_tsx(self, src_dir: str) -> None:
        """创建 index.tsx 文件"""
        index_path = os.path.join(src_dir, "index.tsx")
        index_content = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);"""
        with open(index_path, "w", encoding="utf-8") as f:
            f.write(index_content) 


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
enable_multi_round_generate: false
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
