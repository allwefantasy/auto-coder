---
description: 使用 @byzerllm.prompt() 简化 Prompt 构建
globs: ["*.py"]
alwaysApply: false
---

# 使用 @byzerllm.prompt() 装饰器构建动态 Prompt

## 简要说明
`@byzerllm.prompt()` 装饰器允许将方法的文档字符串 (docstring) 作为 Jinja2 模板，方法的返回值作为渲染模板的上下文，从而优雅地分离 Prompt 模板和填充逻辑。适用于需要根据不同输入动态生成复杂 Prompt 的场景。

## 典型用法
```python
import byzerllm
from typing import Dict, Any, List

# 假设有一个 LLM 实例
# llm = byzerllm.ByzerLLM() 

class PromptGenerator:
    def __init__(self, project_name: str):
        self.project_name = project_name

    @byzerllm.prompt()
    def generate_analysis_prompt(self, file_paths: List[str], user_query: str) -> Dict[str, Any]:
        """
        分析以下文件，并根据用户查询生成报告。

        项目名称: {{ project_name }}

        待分析文件:
        {% for file_path in files %}
        - {{ file_path }}
        {% endfor %}

        用户查询: {{ query }}

        请提供详细的分析结果。
        """
        # 此方法准备并返回用于渲染上面 docstring 模板的上下文
        context = {
            "project_name": self.project_name,
            "files": file_paths,
            "query": user_query
        }
        return context

# 使用示例
generator = PromptGenerator(project_name="AutoCoder")
file_list = ["src/main.py", "src/utils.py"]
query = "查找所有使用了 'os' 模块的地方"

# 调用 .prompt() 方法获取渲染后的 Prompt 字符串
rendered_prompt = generator.generate_analysis_prompt.prompt(file_paths=file_list, user_query=query)

print(rendered_prompt)
# 输出:
# 分析以下文件，并根据用户查询生成报告。
#
# 项目名称: AutoCoder
#
# 待分析文件:
#
# - src/main.py
# - src/utils.py
#
# 用户查询: 查找所有使用了 'os' 模块的地方
#
# 请提供详细的分析结果。

# 注意：实际调用 LLM 时，通常会将 rendered_prompt 作为输入内容
# result = llm.chat_oai([{"role": "user", "content": rendered_prompt}])
```

## 依赖说明
- 需要安装 `byzerllm` 库。(`pip install pybyzerllm`)
- Python 环境 (通常 >= 3.8)。

## 学习来源
从 `/Users/allwefantasy/projects/auto-coder/src/autocoder/agent/auto_learn.py` 模块中的 `AutoLearn.analyze_modules` 方法提取。该方法利用 `@byzerllm.prompt()` 装饰器，将复杂的 Prompt 生成逻辑封装在其 docstring 和返回的字典中。