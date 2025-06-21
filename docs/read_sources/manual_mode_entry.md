# Manual 模式代码入口

## 调用流程概述

原始流程：auto-coder.py -> dispacher.py -> action.py/action_regex_project.py

## 详细调用流程图

```mermaid
graph TD
    %% Main entry point
    A["main() in auto_coder.py"] --> B["Dispacher(args, llm)"];
    B --> C["dispacher.dispach()"];
    
    %% Dispatcher flow
    C --> D["Loop through actions"];
    D --> E{"action.run()?"};
    E -->|"True"| F["Return"];
    E -->|"False"| D;
    
    %% Actions
    D --> G1["ActionTSProject"];
    D --> G2["ActionPyProject"];
    D --> G3["ActionCopilot"];
    D --> G4["ActionRegexProject"];
    D --> G5["ActionSuffixProject"];
    
    %% Action execution flow
    subgraph "Action Execution Flow"
        H["action.run()"] --> I["Initialize Project"];
        I --> J["project.run()"];
        J --> K["source_code_list = SourceCodeList(project.sources)"];
        K --> L["build_index_and_filter_files()"];
        L --> M["action.process_content(source_code_list)"];
    end
    
    %% Process content flow
    subgraph "Process Content Flow"
        M --> N["CodeAutoGenerate/CodeAutoGenerateEditBlock"];
        N --> O["generate.single_round_run()"];
        O --> P{"args.auto_merge?"};
        P -->|"Yes"| Q["CodeAutoMerge/CodeAutoMergeEditBlock"];
        Q --> R["code_merge.merge_code()"];
        P -->|"No"| S["Return content"];
        R --> S;
    end
    
    %% EditBlock Manager (for advanced mode)
    subgraph "EditBlock Manager Flow"
        T["CodeEditBlockManager"] --> U["generate_and_fix()"];
        U --> V["_fix_missing_context()"];
        V --> W["_fix_unmerged_blocks()"];
        W --> X["_fix_lint_errors()"];
        X --> Y["_fix_compile_errors()"];
        Y --> Z["code_merger.merge_code()"];
    end
```

## 关键组件说明

1. **main()** - 入口函数，位于 auto_coder.py，当执行 /coding 指令的时候会解析命令行参数并初始化 Dispatcher

2. **Dispatcher** - 负责根据项目类型选择合适的 Action 执行
   - 尝试多种 Action 类型，直到找到一个返回 True 的 Action

3. **Action 类型**
   - ActionTSProject: 处理 TypeScript 项目
   - ActionPyProject: 处理 Python 项目
   - ActionCopilot: 处理 Copilot 模式
   - ActionRegexProject: 处理正则表达式项目
   - ActionSuffixProject: 处理后缀项目

4. **代码生成与合并**
   - CodeAutoGenerate/CodeAutoGenerateEditBlock: 生成代码
   - CodeAutoMerge/CodeAutoMergeEditBlock: 合并生成的代码

5. **高级编辑模式**
   - CodeEditBlockManager: 管理代码编辑块，提供自动修复功能
   - 可以修复缺失上下文、未合并代码块、Lint 错误和编译错误