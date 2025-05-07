---
description: 规范化使用ShadowManager和ShadowLinter进行代码质量检查的模式
globs: ["src/**/*.py"] # 适用于src目录下所有Python模块
alwaysApply: false
---

# 影子系统组合使用模式

## 简要说明
本规则定义了如何在AutoCoder项目中组合使用ShadowManager和ShadowLinter来实现代码生成、代码质量检查和自动修复的标准方法。ShadowManager管理真实文件和"影子文件"之间的映射，ShadowLinter在不修改原始文件的情况下对这些影子文件进行代码质量检查。这种组合模式可以安全地检查和验证生成的代码更改，而不影响实际项目文件。

## 典型用法

### 1. 初始化影子系统

```python
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.linters.shadow_linter import ShadowLinter

# 初始化影子管理器
# event_file 参数可用于创建特定事件相关的隔离影子目录
shadow_manager = ShadowManager(
    source_dir="/path/to/project",  # 项目根目录
    event_file_id="event_id",  # 可选，特定事件ID
    ignore_clean_shadows=False  # 是否忽略清理影子目录
)

# 初始化影子代码质量检查器
shadow_linter = ShadowLinter(
    shadow_manager=shadow_manager,
    verbose=False  # 是否启用详细输出
)
```

### 2. 将生成的代码创建为影子文件

```python
def _create_shadow_files_from_edits(self, generation_result):
    """
    从编辑块内容中提取代码并创建临时影子文件用于检查。

    参数:
        generation_result: 包含SEARCH/REPLACE块的内容

    返回:
        Dict[str, str]: 映射 {影子文件路径: 内容}
    """
    # 使用合并工具从生成结果中提取最佳编辑
    result = self.code_merger.choose_best_choice(generation_result)
    merge = self.code_merger._merge_code_without_effect(result.contents[0])
    
    shadow_files = {}
    # 将成功的编辑块应用到影子文件中
    for file_path, new_content in merge.success_blocks:
        self.shadow_manager.update_file(file_path, new_content)
        shadow_files[self.shadow_manager.to_shadow_path(
            file_path)] = new_content

    return shadow_files
```

### 3. 执行代码质量检查并格式化结果

```python
def _format_lint_issues(self, lint_results, levels=[IssueSeverity.ERROR]):
    """
    将linter结果格式化为字符串供模型使用

    参数:
        lint_results: Linter结果对象
        level: 过滤问题的级别

    返回:
        str: 格式化的问题描述
    """
    formatted_issues = []

    for file_path, result in lint_results.file_results.items():
        file_has_issues = False
        file_issues = []

        for issue in result.issues:
            if issue.severity.value not in levels:
                continue

            if not file_has_issues:
                file_has_issues = True
                file_issues.append(f"文件: {file_path}")

            severity = "错误" if issue.severity == IssueSeverity.ERROR else "警告" if issue.severity == IssueSeverity.WARNING else "信息"
            line_info = f"第{issue.position.line}行"
            if issue.position.column:
                line_info += f", 第{issue.position.column}列"

            file_issues.append(
                f"  - [{severity}] {line_info}: {issue.message} (规则: {issue.code})"
            )

        if file_has_issues:
            formatted_issues.extend(file_issues)
            formatted_issues.append("")  # 空行分隔不同文件

    return "\n".join(formatted_issues)

def _count_errors(self, lint_results, levels=[IssueSeverity.ERROR]):
    """
    计算lint结果中的错误数量

    参数:
        lint_results: Linter结果对象

    返回:
        int: 错误数量
    """
    error_count = 0

    for _, result in lint_results.file_results.items():
        if IssueSeverity.ERROR in levels:
            error_count += result.error_count
        if IssueSeverity.WARNING in levels:
            error_count += result.warning_count
        if IssueSeverity.INFO in levels:
            error_count += result.info_count
        if IssueSeverity.HINT in levels:
            error_count += result.hint_count

    return error_count
```

### 4. 如何获取 Lint 结果

```python
def get_lint_results(self, generated_code):
    """
    获取生成代码的Lint结果
    
    参数:
        generated_code: 生成的代码内容
        
    返回:
        tuple: (lint_results, error_count, formatted_issues)
    """
    # 首先清理之前的影子文件
    self.shadow_manager.clean_shadows()
    
    # 创建影子文件
    shadow_files = self._create_shadow_files_from_edits(generated_code)
    
    if not shadow_files:
        return None, 0, "无需进行代码质量检查的文件"
    
    # 运行linter检查所有影子文件
    lint_results = self.shadow_linter.lint_all_shadow_files()
    
    # 计算错误数量
    error_count = self._count_errors(lint_results, 
                                     [IssueSeverity.ERROR, IssueSeverity.WARNING])
    
    # 将结果格式化为可读文本
    formatted_issues = self._format_lint_issues(
        lint_results, [IssueSeverity.ERROR, IssueSeverity.WARNING])
    
    # 记录或输出结果
    if error_count > 0:
        self.logger.warning(f"发现 {error_count} 个代码质量问题")
        self.logger.debug(formatted_issues)
    else:
        self.logger.info("代码质量检查通过，未发现问题")
    
    return lint_results, error_count, formatted_issues
```

### 5. 使用参数控制代码质量检查

通过在`AutoCoderArgs`中定义的`enable_auto_fix_lint`参数，可以控制是否执行代码质量检查。这样可以在不需要代码质量检查时提高性能，或者在特定场景下选择性地启用或禁用此功能。

```python
def resolve(self) -> ToolResult:
    # ... 现有的文件处理代码 ...
    
    # 完成文件写入后
    try:
        # 写入文件内容
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(current_content)
        
        # 检查是否启用了Lint功能
        enable_lint = self.args.enable_auto_fix_lint
        
        # 根据配置决定是否执行代码质量检查
        if enable_lint:
            try:
                if self.shadow_linter and self.shadow_manager:
                    # 对修改后的文件进行 lint 检查
                    shadow_path = target_path  # 已经是影子路径
                    lint_results = self.shadow_linter.lint_shadow_file(shadow_path)
                    
                    # 处理 lint 结果
                    if lint_results and lint_results.issues:
                        has_lint_issues = True
                        formatted_issues = self._format_lint_issues(lint_results)
                        lint_message = f"\n\n代码质量检查发现 {len(lint_results.issues)} 个问题:\n{formatted_issues}"
                    else:
                        lint_message = "\n\n代码质量检查通过，未发现问题。"
            except Exception as e:
                logger.error(f"Lint 检查失败: {str(e)}")
                lint_message = "\n\n尝试进行代码质量检查时出错。"
        else:
            logger.info("代码质量检查已禁用")
            
        # 将 lint 消息添加到结果中，仅当启用了 lint 功能时
        if enable_lint:
            message += lint_message
            
        # 构建返回内容，根据是否启用 lint 添加不同的信息
        result_content = {
            "content": current_content
        }
        
        # 只有在启用 Lint 时才添加 Lint 结果
        if enable_lint:
            result_content["lint_results"] = {
                "has_issues": has_lint_issues,
                "issues": formatted_issues if has_lint_issues else None
            }
        
        return ToolResult(success=True, message=message, content=result_content)
    except Exception as e:
        # ... 错误处理 ...
```

这种方式可以在不同的场景下灵活控制代码质量检查功能：

1. 在资源受限的环境中可以禁用检查以提高性能
2. 在开发阶段可以启用检查以提高代码质量
3. 在测试或生产环境中可以根据需要选择启用或禁用

在配置文件中设置该参数的方式通常如下：

```yaml
# 配置文件示例
enable_auto_fix_lint: true  # 启用代码质量检查
# 或
enable_auto_fix_lint: false  # 禁用代码质量检查
```

### 6. 完整的代码生成和质量检查流程

```python
def generate_and_check(self, query, source_code_list):
    """
    生成代码并进行代码质量检查
    
    参数:
        query: 用户查询
        source_code_list: 源代码列表
        
    返回:
        tuple: (生成结果, lint结果, 是否通过质量检查)
    """
    # 初始代码生成
    self.printer.print_in_terminal("generating_initial_code")
    start_time = time.time()
    generation_result = self.code_generator.single_round_run(
        query, source_code_list)
        
    # 计算token使用情况
    token_cost_calculator = TokenCostCalculator(args=self.args)        
    token_cost_calculator.track_token_usage_by_generate(
        llm=self.code_generator.llms[0],
        generate=generation_result,
        operation_name="code_generation_complete",
        start_time=start_time,
        end_time=time.time()
    )
    
    # 确保结果非空
    if not generation_result.contents:
        self.printer.print_in_terminal("generation_failed", style="red")
        return generation_result, None, False
        
    # 选择最佳结果
    generation_result = self.code_merger.choose_best_choice(generation_result)
    generation_result = CodeGenerateResult(
        contents=[generation_result.contents[0]], 
        conversations=[generation_result.conversations[0]], 
        metadata=generation_result.metadata
    )
    
    # 获取Lint结果
    lint_results, error_count, formatted_issues = self.get_lint_results(generation_result)
    
    # 判断是否通过质量检查
    quality_passed = error_count == 0
    
    # 清理影子文件
    self.shadow_manager.clean_shadows()
    
    return generation_result, lint_results, quality_passed
```

### 7. 在工具解析器中使用影子系统进行文件操作

下面是一个从`ReplaceInFileToolResolver`中提取的示例，展示了如何在工具解析器中将正常文件路径转换为影子系统的路径，并进行读写操作：

```python
def resolve(self) -> ToolResult:
    # 获取文件路径
    file_path = self.tool.path
    diff_content = self.tool.diff
    source_dir = self.args.source_dir or "."
    abs_project_dir = os.path.abspath(source_dir)
    abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

    # 安全检查
    if not abs_file_path.startswith(abs_project_dir):
        return ToolResult(success=False, message="访问被拒绝：文件路径不在项目目录内")

    # 文件路径转换：判断是否使用影子文件系统
    target_path = abs_file_path
    if self.shadow_manager:
        # 将项目文件路径转换为影子文件路径
        target_path = self.shadow_manager.to_shadow_path(abs_file_path)

    # 读取文件内容逻辑
    try:
        # 1. 如果影子文件已存在，直接读取影子文件
        if os.path.exists(target_path) and os.path.isfile(target_path):
            with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
        # 2. 如果影子文件不存在但原文件存在，从原文件复制内容创建影子文件
        elif self.shadow_manager and os.path.exists(abs_file_path) and os.path.isfile(abs_file_path):
            # 从原始文件读取内容
            with open(abs_file_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()
            # 确保影子文件父目录存在
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # 将原始内容写入影子文件作为基准
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            logger.info(f"[Shadow] 从原始文件初始化影子文件: {target_path}")
        else:
            return ToolResult(success=False, message=f"文件未找到: {file_path}")
    except Exception as e:
        logger.error(f"读取文件出错 '{file_path}': {str(e)}")
        return ToolResult(success=False, message=f"读取文件错误: {str(e)}")

    # ... 处理文件内容 ...

    # 写入更新后的内容到影子文件
    try:
        # 确保影子文件父目录存在
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        # 写入修改后的内容
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(current_content)
        logger.info(f"成功应用变更到文件: {file_path}")

        # 如果有代理，记录文件变更
        if self.agent:
            rel_path = os.path.relpath(abs_file_path, abs_project_dir)
            self.agent.record_file_change(rel_path, "modified", diff=diff_content, content=current_content)

        return ToolResult(success=True, message="操作成功", content=current_content)
    except Exception as e:
        logger.error(f"写入文件出错 '{file_path}': {str(e)}")
        return ToolResult(success=False, message=f"写入文件错误: {str(e)}")
```

上述代码展示了在工具解析器中使用影子系统的标准流程：

1. **路径转换**：使用`shadow_manager.to_shadow_path()`将项目文件路径转换为影子文件路径
2. **智能读取**：先尝试读取影子文件，如果不存在则读取原始文件并创建对应的影子文件
3. **安全写入**：所有写入操作都针对影子文件，不会直接修改原始项目文件
4. **变更记录**：在完成操作后记录文件变更信息，用于后续处理

这种模式确保了所有文件修改都在影子系统中进行，保持原始文件的不变性，同时提供了完整的文件操作功能。

## 依赖说明
- **核心组件**:
    - `ShadowManager`: 管理项目文件与影子文件的映射
    - `ShadowLinter`: 对影子文件进行代码质量检查
- **辅助组件**:
    - `TokenCostCalculator`: 跟踪LLM Token使用情况
    - `EventManager`: 记录处理过程中的事件
    - `CodeAutoGenerateEditBlock`: 生成代码编辑块
    - `CodeAutoMergeEditBlock`: 合并代码编辑块
- **其他依赖**:
    - `global_cancel`: 用于检查是否取消操作
    - `Printer`: 用于终端输出
    - `loguru.logger`: 用于日志记录

## 关键概念
- **影子文件系统**: 在`.auto-coder/shadows/`目录下创建与源代码结构相同的文件系统，用于安全地进行代码修改和检查。
- **增量修改**: A只在影子系统中修改需要变更的文件，保持其他文件不变。
- **代码质量检查**: 在不影响原始代码的情况下，对生成的代码进行静态分析和规范检查。
- **事件追踪**: 记录整个处理过程中的关键事件，便于调试和分析。
- **可控性**: 通过`enable_auto_fix_lint`参数控制是否执行代码质量检查，提高系统灵活性和性能。

## 学习来源
从以下源文件的实践中提取：
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/code_editblock_manager.py`
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/shadows/shadow_manager.py`
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/linters/shadow_linter.py`
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/agent/agentic_edit_tools/replace_in_file_tool_resolver.py`