
---
description: 定义在 AutoCoder 项目中开发新 Agent 的标准模式和最佳实践。
globs: ["src/autocoder/agent/**/*.py", "src/autocoder/common/v2/agent/**/*.py"] # 适用于 Agent 实现相关文件
alwaysApply: false
---

# Agent 开发模式指南

## 简要说明
本规则旨在为 AutoCoder 项目中开发新的 Agent 提供一套标准化的模式和最佳实践。Agent 通常是指执行特定自动化任务（如代码生成、分析、编辑、学习等）的核心逻辑单元，通常会与 LLM (大型语言模型) 进行交互。遵循这些模式有助于保持代码的一致性、可维护性和可扩展性。

## 核心模式与最佳实践

1.  **基于类的结构 (Class-based Structure):**
    *   将 Agent 的核心逻辑封装在一个专门的 Python 类中。
    *   类的构造函数 (`__init__`) 应用于接收必要的配置、依赖（如 LLM 客户端实例、配置参数 `args` 等）。
    *   将 Agent 的主要功能或执行入口实现为一个或多个明确的方法（例如 `run`, `process`, `resolve`, `analyze` 等）。

    ```python
    import byzerllm
    from autocoder.common.types import SomeConfigArgs # 假设的配置类型
    from autocoder.events import get_event_manager # 用于事件记录

    class MyNewAgent:
        def __init__(self, llm: byzerllm.ByzerLLM, args: SomeConfigArgs):
            self.llm = llm
            self.args = args
            # 初始化事件管理器 (如果需要详细日志)
            self.event_manager = get_event_manager(f".auto-coder/events/{self.__class__.__name__}.jsonl")
            # 其他初始化...

        def run(self, user_input: str) -> str:
            """Agent 的主要执行逻辑"""
            # 1. 记录开始事件 (可选但推荐)
            self.event_manager.write_stream(...) 

            # 2. 处理输入，准备 LLM 调用
            prompt = self._build_prompt(user_input)

            # 3. 调用 LLM
            response = self.llm.chat_oai(...) 

            # 4. 处理 LLM 响应
            result = self._parse_response(response)

            # 5. 记录结果事件 (可选)
            self.event_manager.write_result(...)

            # 6. 返回最终结果
            return result

        def _build_prompt(self, input_data: str) -> str:
            # 使用 @byzerllm.prompt() 或手动构建 Prompt
            # 参考: byzerllm_prompt_decorator.md, byzerllm_dynamic_prompt.md
            pass

        def _parse_response(self, response) -> str:
            # 解析 LLM 返回的内容
            pass

        # 其他辅助方法...
    ```

2.  **LLM 交互 (LLM Interaction):**
    *   明确 Agent 与 LLM 的交互方式。
    *   可以直接使用 `ByzerLLM` 实例的方法（如 `chat_oai`）。
    *   推荐使用 `@byzerllm.prompt()` 装饰器来管理和构建 Prompt 模板，将 Prompt 逻辑与执行逻辑分离。参考 `byzerllm_prompt_decorator.md` 和 `byzerllm_dynamic_prompt.md`。
    *   动态构建 Prompt 时，可以结合上下文信息、代码片段、项目结构以及通过 `autocoder.common.rulefiles.autocoderrules_utils.get_rules()` 加载的用户自定义规则。

3.  **事件系统集成 (Event System Integration):**
    *   对于需要详细追踪执行过程、步骤、思考链或中间结果的复杂 Agent（特别是多轮交互或需要调试的 Agent），强烈建议集成事件系统 (`autocoder.events`)。
    *   使用 `get_event_manager()` 获取实例，并为每个 Agent 或任务实例指定独立的事件文件路径（例如，放在 `.auto-coder/events/` 目录下）。
    *   在关键步骤（开始、思考、中间输出、错误、最终结果、完成）使用 `event_manager` 的 `write_stream`, `write_result`, `write_error`, `write_completion` 等方法记录结构化事件。
    *   参考 `event_system_usage.md` 获取详细用法。

4.  **输入/输出处理 (Input/Output Handling):**
    *   明确定义 Agent 的输入参数类型（例如，使用 Pydantic 模型或类型提示）。
    *   明确定义 Agent 的输出结果类型（例如，返回 Pydantic 模型、字典或简单类型）。
    *   如果 Agent 需要与文件系统交互（读写文件），应通过配置参数（如 `source_dir`, `output_dir`）或明确的方法参数传入路径，避免硬编码。对于复杂的文件操作，可以考虑封装成独立的工具或使用 `agentic_edit.py` 中展示的工具解析器模式。

5.  **配置与上下文 (Configuration & Context):**
    *   Agent 运行所需的配置（如 LLM 模型名称、源文件目录、特定行为开关等）应通过构造函数或方法参数传入，通常使用一个配置对象（如 Pydantic 模型或 `argparse` 结果）。
    *   避免在 Agent 内部硬编码配置值。

6.  **错误处理 (Error Handling):**
    *   实现健壮的错误处理逻辑，例如使用 `try...except` 块捕获 LLM 调用失败、文件操作错误、数据解析错误等。
    *   如果使用了事件系统，务必在 `except` 块中记录 `ERROR` 事件，包含错误信息和上下文。

7.  **工具使用 (Tool Usage - for Advanced Agents):**
    *   对于需要执行特定、可复用操作（如文件搜索、代码执行、API 调用）的复杂 Agent，可以考虑实现或复用 "Tools"。
    *   `agentic_edit.py` 中的 `AgenticEditToolsManager` 和 `*ToolResolver` 类展示了一种实现工具调用和管理的模式。Agent 可以根据 LLM 的指令或内部逻辑来决定调用哪个工具。

## 示例参考

*   **`src/autocoder/common/v2/agent/agentic_edit.py`**: 展示了一个高度集成了事件系统和工具使用的复杂 Agent 模式，适用于需要精确控制和观察执行流程的场景。
*   **`src/autocoder/agent/auto_learn.py`**: 展示了一个相对简单、侧重于使用 `@byzerllm.prompt()` 进行 LLM 交互和分析任务的 Agent。

## 依赖说明
*   `byzerllm`: LLM 交互核心库。
*   `autocoder.events`: 事件记录系统 (可选但推荐)。
*   `autocoder.common.types` (或类似模块): 用于定义配置和输入/输出的数据结构 (推荐使用 Pydantic)。
*   `autocoder.common.rulefiles.autocoderrules_utils`: 用于加载 `.autocoderrules` (如果需要动态 Prompt)。
*   Python 标准库 (os, typing, etc.)。

## 学习来源
本文档总结自对 `src/autocoder/common/v2/agent/agentic_edit.py` 和 `src/autocoder/agent/auto_learn.py` 等 Agent 实现的分析。
