# Lint 集成设计：ReplaceInFileToolResolver

## 概述

本文档提供了在 `ReplaceInFileToolResolver` 中集成代码质量检查（Lint）功能的设计方案。通过使用 AgenticEdit 中已有的 shadow_manager 和 shadow_linter 实例，我们可以在文件修改后立即提供代码质量反馈，从而提高生成代码的质量。

## 背景

`ReplaceInFileToolResolver` 类负责处理文件内容的替换操作，但目前缺少代码质量检查功能。由于 `AgenticEdit` 类已经初始化了 `shadow_manager` 和 `shadow_linter` 实例，我们可以通过 `self.agent` 访问这些实例，进行代码质量检查。

## 设计目标

1. 在文件修改完成后，对修改后的文件进行代码质量检查
2. 提供清晰、格式化的质量检查结果
3. 将质量检查结果包含在工具的返回结果中
4. 确保不干扰原有的文件修改功能

## 实现方案

### 1. 添加 Lint 功能

在 `ReplaceInFileToolResolver` 类的 `resolve` 方法中，在文件修改完成后添加代码质量检查流程：

```python
def resolve(self) -> ToolResult:
    # ... 现有的文件处理代码 ...
    
    # 完成文件写入后，如果写入成功
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as f:
            f.write(current_content)
        logger.info(f"Successfully applied {applied_count}/{len(parsed_blocks)} changes to file: {file_path}")
        
        # 新增：执行代码质量检查
        lint_results = None
        lint_message = ""
        formatted_issues = ""
        has_lint_issues = False
        
        if self.agent and self.agent.shadow_linter:
            # 对修改后的文件进行 lint 检查
            shadow_path = self.shadow_manager.to_shadow_path(abs_file_path)
            lint_results = self.agent.shadow_linter.lint_shadow_file(shadow_path)
            
            if lint_results and lint_results.issues:
                has_lint_issues = True
                # 格式化 lint 问题
                formatted_issues = self._format_lint_issues(lint_results)
                lint_message = f"\n\n代码质量检查发现 {len(lint_results.issues)} 个问题:\n{formatted_issues}"
            else:
                lint_message = "\n\n代码质量检查通过，未发现问题。"
        
        # 构建包含 lint 结果的返回消息
        if errors:
            message = get_message_with_format("replace_in_file.apply_success_with_warnings", 
                                              applied=applied_count, 
                                              total=len(parsed_blocks), 
                                              file_path=file_path,
                                              errors="\n".join(errors))
        else:
            message = get_message_with_format("replace_in_file.apply_success", 
                                              applied=applied_count, 
                                              total=len(parsed_blocks), 
                                              file_path=file_path)
        
        # 将 lint 消息添加到结果中
        message += lint_message
        
        # 变更跟踪，回调AgenticEdit
        if self.agent:
            rel_path = os.path.relpath(abs_file_path, abs_project_dir)
            self.agent.record_file_change(rel_path, "modified", diff=diff_content, content=current_content)
        
        # 附加 lint 结果到返回内容
        result_content = {
            "content": current_content,
            "lint_results": {
                "has_issues": has_lint_issues,
                "issues": formatted_issues if has_lint_issues else None
            }
        }
        
        return ToolResult(success=True, message=message, content=result_content)
    except Exception as e:
        # ... 现有的错误处理代码 ...
```

### 2. 添加 Lint 结果格式化方法

在 `ReplaceInFileToolResolver` 类中添加格式化 lint 结果的辅助方法：

```python
def _format_lint_issues(self, lint_result):
    """
    将 lint 结果格式化为可读的文本格式
    
    参数:
        lint_result: 单个文件的 lint 结果对象
        
    返回:
        str: 格式化的问题描述
    """
    formatted_issues = []
    
    for issue in lint_result.issues:
        severity = "错误" if issue.severity.value == 3 else "警告" if issue.severity.value == 2 else "信息"
        line_info = f"第{issue.position.line}行"
        if issue.position.column:
            line_info += f", 第{issue.position.column}列"
        
        formatted_issues.append(
            f"  - [{severity}] {line_info}: {issue.message} (规则: {issue.code})"
        )
    
    return "\n".join(formatted_issues)
```

### 3. 对返回的 ToolResult 进行扩展

为了在 `ToolResult` 中包含 lint 结果，我们需要使用 `content` 字段来传递更丰富的结构化数据：

```python
# 返回结构示例
ToolResult(
    success=True,
    message="成功应用了 1/1 处修改到文件: src/main.js\n\n代码质量检查发现 2 个问题:\n  - [警告] 第10行: 未使用的变量 'data' (规则: no-unused-vars)\n  - [错误] 第15行: 缺少分号 (规则: semi)",
    content={
        "content": "文件的完整内容...",
        "lint_results": {
            "has_issues": True,
            "issues": "  - [警告] 第10行: 未使用的变量 'data' (规则: no-unused-vars)\n  - [错误] 第15行: 缺少分号 (规则: semi)"
        }
    }
)
```

## 其他考虑事项

### 性能

对每个修改的文件进行 lint 检查会增加一些延迟，但由于影子系统的使用，这些检查不会影响原始文件系统，且只对修改的文件进行检查，因此对性能的影响是可控的。

### 错误处理

保持原有的错误处理逻辑不变，但在 lint 检查过程中出现错误时，应记录日志并优雅地继续执行，而不应阻止文件修改操作的完成。

```python
try:
    # lint 检查代码
    lint_results = self.agent.shadow_linter.lint_shadow_file(shadow_path)
except Exception as e:
    logger.error(f"Lint 检查失败: {str(e)}")
    lint_message = "\n\n尝试进行代码质量检查时出错。"
```

### 扩展性

此设计允许未来添加更多功能，例如：

1. 添加自动修复选项
2. 添加严重性筛选选项
3. 将 lint 结果包含在事件系统中，用于前端展示

## 结论

通过整合 shadow_manager 和 shadow_linter，我们可以在 ReplaceInFileToolResolver 中添加代码质量检查功能，为开发者提供更好的编码体验。这种集成利用了 AgenticEdit 中已有的实例，避免了重复初始化，并保持了原有功能的完整性。

集成后，开发者在使用 replace_in_file 工具修改文件后，将立即获得代码质量反馈，从而可以更快地发现并修复潜在问题。
