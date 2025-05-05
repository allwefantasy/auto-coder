# Rules索引

本文档记录项目中所有可用的代码规则(rules)及其用途。

## byzerllm_prompt_decorator.md
使用 @byzerllm.prompt() 简化 Prompt 构建

## byzerllm_dynamic_prompt.md
如何给 @byzerllm.prompt() 函数添加用户自定义规则文档。同时也演示了，如果添加额外的上下文信息，如何动态生成复杂的 LLM Prompt。

## to_ignore_files.md
使用 .autocoderignore 文件中的规则来判断是否应忽略某个文件或目录。

## token_counter_service.md
提供标准化的Token计数服务实现，包括本地、远程和多进程计数方式，适用于LLM API调用成本控制等场景。

## event_system_usage.md
标准化事件系统用法，用于模块间解耦通信和记录交互。

## agent_development_pattern.md
定义在 AutoCoder 项目中开发新 Agent 的标准模式和最佳实践。

## logger_best_practices.md
规定项目中使用日志记录器(logger)的最佳实践和规范，确保日志记录统一、有效且易于维护。

## demo_or_test_initialization_order.md
在实现demo或者单元测试时，尤其是对于LongContextRAG等基于检索增强生成的组件，必须严格遵循特定的初始化顺序，避免FileMonitor、token计数器等组件出现冲突或错误初始化。

## get_llm.md
在测试代码中获取和初始化LLM模型的标准方法，包括加载token统计、获取模型和配置参数的步骤。

## always_repsond_in_chinese.md
指定交互语言为中文，规定LLM应始终用中文回复并先说明将要执行的操作。

## module_testing_and_demo_structure.md
为新模块添加Pytest测试和示例Demo的标准结构，确保模块功能正确性并提供清晰的使用示例。

## file_monitor_usage.md
解释如何使用FileMonitor单例进行文件系统监控，包括获取实例、注册回调、开始/停止监控等关键步骤。

## save_json_as_md_usage.md
标准化日志保存方法，用于保存各种类型的JSON格式日志为Markdown格式到项目指定目录，特别适用于保存RAG对话、模型响应与调试信息。
