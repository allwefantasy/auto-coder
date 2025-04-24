# Auto-Coder 运行上下文 (Run Context) 和 human_as_model 说明

## `src/autocoder/run_context.py`

- **目的**: 提供一个 `RunContext` 单例类，用于跟踪和管理 Auto-Coder 的运行模式。
- **模式**: 主要有两种模式：
    - `RunMode.TERMINAL`: 表示在命令行终端运行。
    - `RunMode.WEB`: 表示通过 Web 界面运行。
- **用法**:
    - `get_run_context()`: 获取 `RunContext` 的单例实例。
    - `context.mode`: 读取当前的运行模式。
    - `context.set_mode(RunMode)`: 设置运行模式。
    - `context.is_terminal()`: 检查是否为终端模式。
    - `context.is_web()`: 检查是否为 Web 模式。
- **重要性**: 允许 Auto-Coder 的不同部分根据运行环境调整其行为。

## `human_as_model` 参数

- **目的**: 允许用户在 **终端模式** 下代替 LLM 手动输入代码或响应，用于调试、测试或在没有 LLM 时工作。
- **失效条件**:
    - 当 Auto-Coder 通过 Web 界面启动，即运行模式为 `RunMode.WEB` 时，`human_as_model` 功能会被 **显式禁用**。
    - 这是因为 Web 环境通常不提供必要的交互式命令行来支持此功能。代码中通过检查 `get_run_context().mode` 或 `get_run_context().is_web()` 来实现此禁用逻辑。
- **总结**: 如果你希望使用 `human_as_model`，请确保在命令行终端中运行 Auto-Coder。