
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
    import traceback # 用于记录错误堆栈
    from autocoder.common.types import SomeConfigArgs, SomeToolInput, SomeToolOutput # 假设的配置和输入/输出类型
    from autocoder.events import ( # 导入事件创建函数
        get_event_manager, 
        create_stream_thinking, 
        create_result, 
        create_error, 
        create_completion
    )
    from autocoder.events.event_types import EventMetadata # 用于事件元数据

    class SimplifiedAgent:
        def __init__(self, llm: byzerllm.ByzerLLM, args: SomeConfigArgs):
            self.llm = llm
            self.args = args
            # 为每个Agent实例或运行设置唯一的事件文件路径
            self.event_file_path = f".auto-coder/events/{self.__class__.__name__}_{args.task_id}.jsonl" # 示例路径，假设args有task_id
            self.event_manager = get_event_manager(self.event_file_path)
            # 定义基础元数据，用于此Agent产生的所有事件
            self.metadata = EventMetadata(action_file=__file__, path=f"/agent/{self.__class__.__name__}") 

        def run(self, tool_input: SomeToolInput) -> SomeToolOutput:
            """
            简化Agent的主要执行逻辑。
            接收结构化输入，执行模拟的处理，记录事件，并返回结构化输出。
            """
            seq = 1 # 事件序列号
            error_occurred = False
            final_result = None

            try:
                # 1. 记录初始思考过程 (流式事件)
                thinking_start = create_stream_thinking(f"开始处理任务，输入: {tool_input}", sequence=seq)
                self.event_manager.write_stream(content=thinking_start.to_dict(), metadata=self.metadata.to_dict())
                seq += 1

                # 2. 准备Prompt (调用辅助方法)
                prompt = self._build_prompt(tool_input)
                thinking_prompt = create_stream_thinking(f"构建的Prompt: {prompt[:100]}...", sequence=seq) # 记录部分Prompt
                self.event_manager.write_stream(content=thinking_prompt.to_dict(), metadata=self.metadata.to_dict())
                seq += 1
                
                # --- 概念性工具使用点 ---
                # 在某些Agent模式中 (如agentic_edit)，LLM的响应可能包含调用工具的指令
                # 这里可以插入解析LLM响应、决定是否调用工具、执行工具、并将结果整合回上下文的逻辑
                # 例如:
                # tool_call_request = parse_llm_response_for_tool_call(llm_response)
                # if tool_call_request:
                #     tool_result = execute_tool(tool_call_request)
                #     # ... 更新 prompt 或上下文 ...
                # ------------------------

                # 3. 执行核心逻辑 (模拟LLM调用)
                # response = self.llm.chat_oai([{"role": "user", "content": prompt}]) 
                # 为简化，直接模拟一个LLM响应
                simulated_llm_response = {"choices": [{"message": {"content": f"模拟LLM响应：已成功处理参数 '{tool_input.some_param}'。"}}]} # 模拟OAI响应结构

                # 4. 处理和解析结果 (调用辅助方法)
                final_result = self._parse_response(simulated_llm_response)
                
                # 5. 记录最终结果 (结果事件)
                result_content = create_result(content=final_result.to_dict(), metadata={"source": "agent_logic"})
                # 合并基础元数据和特定于此事件的元数据
                combined_metadata = {**self.metadata.to_dict(), **result_content.metadata}
                self.event_manager.write_result(content=result_content.to_dict(), metadata=combined_metadata)

            except Exception as e:
                error_occurred = True
                # 6. 记录错误信息 (错误事件)
                error_content = create_error(
                    error_code="AGENT_EXECUTION_ERROR",
                    error_message=f"Agent执行过程中发生错误: {str(e)}",
                    details={"input": tool_input.to_dict(), "traceback": traceback.format_exc()} # 注意生产环境中谨慎记录完整traceback
                )
                self.event_manager.write_error(content=error_content.to_dict(), metadata=self.metadata.to_dict())
                # 准备一个表示错误的输出对象
                final_result = SomeToolOutput(success=False, message=f"执行错误: {str(e)}", content=None)

            finally:
                # 7. 记录完成状态 (完成事件，仅在未发生错误时)
                if not error_occurred and final_result and final_result.success:
                    completion_content = create_completion(
                        success_code="TASK_COMPLETE",
                        success_message="Agent任务成功完成模拟处理。",
                        result=final_result.to_dict() # 将最终结果包含在完成事件中
                    )
                    self.event_manager.write_completion(content=completion_content.to_dict(), metadata=self.metadata.to_dict())
                
                # 确保总是有返回值，即使在finally块之前出现意外退出
                if final_result is None:
                     final_result = SomeToolOutput(success=False, message="Agent因未知原因未能正常完成。", content=None)

            return final_result

        # --- 辅助方法 ---
        
        def _build_prompt(self, tool_input: SomeToolInput) -> str:
            """
            构建发送给LLM的Prompt (简化示例)。
            真实场景会更复杂，可能使用 @byzerllm.prompt() 装饰器。
            """
            # 这里可以访问 self.args 获取配置
            return f"请处理以下请求: {tool_input.some_param}. 配置: {self.args}" # 假设tool_input和args有这些属性

        def _parse_response(self, response: dict) -> SomeToolOutput:
            """
            解析LLM的响应 (简化示例)。
            真实场景需要处理各种响应格式和错误。
            """
            try:
                # 模拟从类OAI响应中提取内容
                content = response["choices"][0]["message"]["content"]
                # 根据内容或其他逻辑判断成功状态
                success = "成功" in content 
                message = "解析成功" if success else "解析完成但未明确成功标志"
                return SomeToolOutput(success=success, message=message, content=content)
            except (KeyError, IndexError, TypeError) as e:
                # 记录解析错误事件可能在这里进行
                error_content = create_error(
                    error_code="RESPONSE_PARSING_ERROR",
                    error_message=f"解析LLM响应时出错: {str(e)}",
                    details={"response_sample": str(response)[:200]} # 记录部分响应样本
                )
                self.event_manager.write_error(content=error_content.to_dict(), metadata=self.metadata.to_dict())
                return SomeToolOutput(success=False, message=f"解析响应失败: {e}", content=None)

    # --- 概念性使用示例 (通常不包含在规则文档的核心示例中) ---
    # if __name__ == "__main__":
    #     # 此处需要设置模拟的LLM实例和配置参数
    #     mock_llm = None # 替换为实际或模拟的LLM客户端
    #     mock_args = SomeConfigArgs(task_id="demo_run_123") # 假设的配置对象
          
    #     # 创建Agent实例
    #     agent = SimplifiedAgent(llm=mock_llm, args=mock_args)
          
    #     # 准备输入数据
    #     input_data = SomeToolInput(some_param="测试值") # 假设的输入对象
          
    #     # 执行Agent
    #     output = agent.run(input_data)
          
    #     # 打印结果
    #     print(f"Agent 输出: {output}")
    #     print(f"事件已记录到: {agent.event_file_path}")
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
