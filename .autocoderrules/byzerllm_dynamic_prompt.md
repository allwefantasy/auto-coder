---
description: Dynamically construct LLM prompts using @byzerllm.prompt() with context.
globs: ["*/*.py"]
alwaysApply: false
---

# Dynamic LLM Prompt Construction with Context using @byzerllm.prompt()

## 简要说明
如何给 @byzerllm.prompt() 函数使用autocoderrules_utils工具添加用户自定义规则文档，同时也演示了，如果添加额外的上下文信息，如何动态生成复杂的 LLM Prompt。

## 典型用法

```python
# 导入必要的库
import byzerllm
from typing import Dict, Optional, List

# 步骤 1: 导入 get_rules 函数，用于自动加载用户自定义规则文件
from autocoder.common.rulefiles.autocoderrules_utils import get_rules

# 示例：获取显式传递的外部规则
def get_explicit_external_rules() -> Dict[str, str]:
    """获取显式传递的外部规则，这些规则可以由用户直接提供"""
    # 实际应用中可能从配置文件或API获取
    return {
        "code_style.txt": "Always use snake_case for variable names.",
        "formatting.json": '{"max_line_length": 88, "use_spaces": true}'
    }

# 示例：获取项目结构信息
def get_project_structure() -> str:
    """获取项目的目录结构"""
    # 实际应用中可能使用 os.walk 或其他方法动态生成
    return """
project_root/
├── src/
│   ├── main.py
│   └── utils/
│       └── helpers.py
├── docs/
│   └── usage.md
└── README.md
"""

class DynamicPromptBuilder:
    def __init__(self, args: Optional[Dict] = None):
        """初始化 DynamicPromptBuilder
        
        Args:
            args: 可选的配置参数，用于控制 prompt 生成的行为
        """
        self.args = args or {}

    @byzerllm.prompt()
    def generate_code_prompt(self,
                             instruction: str,
                             code_snippets: Dict[str, str],
                             project_structure: Optional[str] = None,
                             extra_context: Optional[str] = None,
                             external_rules: Optional[Dict[str, str]] = None
                             ) -> Dict: # 返回类型是 Dict，用于传递模板变量
        """
        根据用户指令生成代码的提示模板。
        
        使用 Jinja2 语法构建模板，根据传入的参数动态生成最终的提示文本。
        模板中的条件语句确保只有提供了相应参数时才会包含对应部分。

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
        # 步骤 2: 在方法内部调用 get_rules() 获取用户自定义规则
        extra_docs = get_rules()

        # 返回包含模板变量的字典
        # 注意：@byzerllm.prompt() 装饰器会使用这些变量渲染模板，并返回最终的字符串
        return {
            # 将参数直接传递给模板
            "project_structure": project_structure,
            # 步骤 3: 将加载的规则添加到模板上下文中
            "extra_docs": extra_docs
        }

# === 调用示例 ===
if __name__ == "__main__":
    # 创建 DynamicPromptBuilder 实例
    builder = DynamicPromptBuilder()

    # 准备动态数据
    instruction = "Implement a function to calculate the factorial of a number."
    
    # 代码片段示例 - 可以是项目中已有的代码
    code_snippets = {
        "src/utils.py": "def helper_function():\n    # 辅助函数\n    pass"
    }
    
    # 获取项目结构
    project_structure_str = get_project_structure()
    
    # 额外上下文信息
    extra_context_info = "The function should handle non-negative integers only and raise ValueError for negative inputs."
    
    # 获取显式传递的规则
    explicit_rules = get_explicit_external_rules()

    # 示例 1: 基本用法 - 调用 prompt 方法生成最终的 prompt 字符串
    # 注意: 所有在模板中使用的变量都需要作为关键字参数传递
    # extra_docs 会在方法内部通过 get_rules() 自动加载，无需手动传递
    final_prompt = builder.generate_code_prompt.prompt(
        instruction=instruction,
        code_snippets=code_snippets,
        project_structure=project_structure_str,  # 显式传递项目结构
        extra_context=extra_context_info,
        external_rules=explicit_rules  # 传递显式规则
    )

    print("===== 生成的提示内容 =====")
    print(final_prompt)

    # 示例 2: 高级用法 - 在调用时使用不同的参数
    modified_prompt = builder.generate_code_prompt.prompt(
        instruction="Refactor the existing factorial function for better performance and readability.",
        code_snippets={
            "src/math_lib.py": "def factorial(n):\n    if n <= 1:\n        return 1\n    return n * factorial(n-1)"
        },
        project_structure=project_structure_str,
        extra_context="Optimize for both time and space complexity. Consider using iteration instead of recursion.",
        external_rules=explicit_rules,
        # 可以添加模板中未定义的新变量
        # additional_context="This value will be available in the template if referenced"
    )
    
    print("\n===== 修改后的提示内容 =====")
    print(modified_prompt)

```

## 依赖说明
- `byzerllm`: 核心库，提供 `@byzerllm.prompt()` 装饰器。 (`pip install byzerllm`)
- `Jinja2`: `@byzerllm.prompt()` 内部使用 Jinja2 进行模板渲染。通常作为 `byzerllm` 的依赖自动安装。
- 无特定环境要求，可在任何标准 Python 环境中使用。
- 无特殊初始化流程，直接使用装饰器即可。

## 学习来源
该模式提取自 `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/code_auto_generate_diff.py` 文件中的 `CodeAutoGenerateDiff.single_round_instruction` 方法。该方法演示了如何结合项目结构、源码、上下文、包信息和通过 `get_rules()` 自动加载的用户自定义规则动态生成用于代码生成的复杂 prompt。