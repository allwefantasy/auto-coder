---
description: Dynamically construct LLM prompts using @byzerllm.prompt() with context.
globs: ["*/*.py"]
alwaysApply: false
---

# Dynamic LLM Prompt Construction with Context using @byzerllm.prompt()

## 简要说明
利用 `byzerllm` 库的 `@byzerllm.prompt()` 装饰器和 Jinja2 模板引擎，动态构建结构复杂、包含丰富上下文信息的 LLM prompt。适用于需要向 LLM 提供如代码片段、项目结构、外部规则、历史变更等动态数据的场景，例如代码生成、代码分析、问答系统等。

## 典型用法

```python
import byzerllm
from typing import Dict, Optional, List
from autocoder.common.rulefiles.autocoderrules_utils import get_rules # Step 1: Import get_rules

# 假设存在一个函数用于获取 *显式传递* 的外部规则
def get_explicit_external_rules() -> Dict[str, str]:
    # 在实际应用中，这会从文件或其他来源加载规则
    return {
        "rule1.txt": "Always use snake_case for variable names.",
        "rule2.json": '{"max_line_length": 88}'
    }

# 假设存在一个函数获取项目结构
def get_project_structure() -> str:
    # 在实际应用中，这会扫描目录生成结构树
    return """
project_root/
├── src/
│   └── main.py
├── docs/
│   └── usage.md
└── README.md
"""

class DynamicPromptBuilder:
    def __init__(self, args: Optional[Dict] = None):
        # args 可以包含控制 prompt 生成的配置项
        self.args = args or {}

    @byzerllm.prompt()
    def generate_code_prompt(self,
                             instruction: str,
                             code_snippets: Dict[str, str],
                             project_structure: Optional[str] = None,
                             extra_context: Optional[str] = None,
                             external_rules: Optional[Dict[str, str]] = None
                             ) -> Dict: # Return type is Dict for template variables
        """
        根据用户指令生成代码。

        {%- if project_structure %}
        项目结构:
        {{ project_structure }}
        {%- endif %}

        {%- if code_snippets %}
        相关代码片段:
        <code_snippets>
        {% for file, code in code_snippets.items() %}
        ##File: {{ file }}
        ```python
        {{ code }}
        ```
        {% endfor %}
        </code_snippets>
        {%- endif %}

        {%- if extra_context %}
        额外上下文信息:
        <extra_context>
        {{ extra_context }}
        </extra_context>
        {%- endif %}

        {%- if external_rules %}
        必须遵守的外部规则:
        <external_rules>
        {% for file, rule in external_rules.items() %}
        ##Rule File: {{ file }}
        {{ rule }}
        {% endfor %}
        </external_rules>
        {%- endif %}

        {%- if extra_docs %}
        ====

        RULES PROVIDED BY USER (Loaded from .autocoderrules)

        The following rules are provided by the user, and you must follow them strictly.

        {% for key, value in extra_docs.items() %}
        <user_rule>
        ##File: {{ key }}
        {{ value }}
        </user_rule>
        {% endfor %}
        {%- endif %}

        用户指令:
        {{ instruction }}

        请根据上述信息和指令生成代码。
        """
        # Step 2: Call get_rules() inside the method
        extra_docs = get_rules()

        # 这个 return 语句用于传递需要在模板渲染时计算或获取的变量
        # 实际的 prompt 方法返回值是渲染后的字符串
        return {
            "project_structure": project_structure,  # 将参数直接传递给模板
            "extra_docs": extra_docs # Step 3: Add loaded rules to the template context
        }

# === 调用示例 ===
if __name__ == "__main__":
    builder = DynamicPromptBuilder()

    # 准备动态数据
    instruction = "Implement a function to calculate the factorial of a number."
    code_snippets = {
        "src/utils.py": "def helper_function():\n    pass"
    }
    project_structure_str = get_project_structure()
    extra_context_info = "The function should handle non-negative integers only."
    # 获取 *显式传递* 的规则
    explicit_rules = get_explicit_external_rules()

    # 调用 prompt 方法生成最终的 prompt 字符串
    # 注意：所有在模板中使用的变量 (instruction, code_snippets, project_structure, etc.)
    # 都需要作为关键字参数传递给 .prompt() 方法。
    # 模板中使用的 extra_docs 会在方法内部通过 get_rules() 自动加载并填充。
    final_prompt = builder.generate_code_prompt.prompt(
        instruction=instruction,
        code_snippets=code_snippets,
        project_structure=project_structure_str, # 显式传递 project_structure
        extra_context=extra_context_info,
        external_rules=explicit_rules # 传递显式规则
    )

    print("===== Generated Prompt =====")
    print(final_prompt)

    # 也可以在调用时覆盖或添加模板变量
    modified_prompt = builder.generate_code_prompt.prompt(
        instruction="Refactor the existing factorial function for clarity.",
        code_snippets={"src/math_lib.py": "def factorial(n):\n # ... implementation ..."},
        project_structure=project_structure_str, # 显式传递 project_structure
        extra_context="Focus on readability.",
        external_rules=explicit_rules, # 传递显式规则
        # new_variable="This value was not in the original signature" # 仍然可以添加新变量
    )
    # print("\n===== Modified Prompt =====")
    # print(modified_prompt)

```

## 依赖说明
- `byzerllm`: 核心库，提供 `@byzerllm.prompt()` 装饰器。 (`pip install byzerllm`)
- `Jinja2`: `@byzerllm.prompt()` 内部使用 Jinja2 进行模板渲染。通常作为 `byzerllm` 的依赖自动安装。
- 无特定环境要求，可在任何标准 Python 环境中使用。
- 无特殊初始化流程，直接使用装饰器即可。

## 学习来源
该模式提取自 `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/code_auto_generate_diff.py` 文件中的 `CodeAutoGenerateDiff.single_round_instruction` 方法。该方法演示了如何结合项目结构、源码、上下文、包信息和通过 `get_rules()` 自动加载的用户自定义规则动态生成用于代码生成的复杂 prompt。