
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
