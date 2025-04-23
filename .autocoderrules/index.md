
# Rules索引

本文档记录项目中所有可用的代码规则(rules)及其用途。

## byzerllm_prompt_decorator.md
使用 @byzerllm.prompt() 简化 Prompt 构建

## byzerllm_dynamic_prompt.md
如何给 @byzerllm.prompt() 函数添加用户自定义规则文档。同时也演示了，如果添加额外的上下文信息，如何动态生成复杂的 LLM Prompt。

## to_ignore_files.md
使用 .autocoderignore 文件中的规则来判断是否应忽略某个文件或目录。

## file_monitor_rule.md
使用 watchfiles 实现高效的文件系统监控。

## rule_file_manager_rule.md
管理和加载 .autocoderrules 目录下的规则文件，并支持热加载。
