# Java Linter 设计文档

## 概述
本模块提供对Java代码的质量检查和最佳实践验证功能，基于Python linter模块的设计实现。

## 核心功能
1. 支持.java文件扩展名
2. 检查Java开发环境(JDK)是否安装
3. 集成主流Java代码检查工具
4. 实现单文件和项目级别的代码检查
5. 支持自动修复功能
6. 格式化检查结果输出

## 类设计

```python
class JavaLinter(BaseLinter):
    def __init__(self, verbose=False):
        super().__init__(verbose)
    
    def get_supported_extensions(self):
        return [".java"]
    
    def _check_dependencies(self):
        """检查JDK、checkstyle、pmd等是否安装"""
        # 检查javac是否可用
        # 检查其他Java工具是否安装
    
    def _install_dependencies_if_needed(self):
        """自动安装缺失的Java工具"""
    
    def _run_javac(self, file_path):
        """使用javac编译Java文件"""
        # 返回编译错误信息
    
    def _run_checkstyle(self, target):
        """使用checkstyle检查代码"""
    
    def _run_pmd(self, target):
        """使用pmd检查代码"""
    
    def _run_spotbugs(self, target):
        """使用spotbugs检查代码"""
    
    def _run_java_formatter(self, target, fix=False):
        """使用google-java-format格式化代码"""
    
    def lint_file(self, file_path, fix=False):
        """检查单个Java文件"""
        # 1. 使用javac编译检查
        # 2. 应用其他检查工具
        # 3. 返回合并结果
    
    def lint_project(self, project_path, fix=False):
        """检查整个Java项目"""
    
    def format_lint_result(self, lint_result):
        """格式化检查结果输出"""
```

## 工具集成

### Javac
- 用于编译检查Java文件
- 检查语法错误和类型错误
- 命令: `javac -d /tmp/out Example.java`

### Checkstyle
- 用于检查编码规范和格式问题
- 配置文件: google_checks.xml或自定义规则
- 支持自动修复部分问题

### PMD
- 用于静态代码分析
- 检测潜在错误、不良实践等
- 支持自定义规则集

### SpotBugs
- 用于查找潜在bug
- 检测空指针、资源泄漏等问题
- 需要编译后的class文件

### Google Java Format
- 用于代码自动格式化
- 支持检查模式和自动修复模式

## 实现步骤

1. **环境检查**
   - 验证JDK安装及版本
   - 检查各工具是否可用
   - 自动安装缺失工具

2. **单文件检查**
   - 应用所有检查工具
   - 合并检查结果
   - 支持自动修复

3. **项目检查**
   - 递归查找所有.java文件
   - 批量应用检查工具
   - 汇总检查结果

4. **结果格式化**
   - 按严重程度分类
   - 按文件分组显示
   - 包含详细位置和描述

## 示例用法

```python
# 检查单个文件
linter = JavaLinter(verbose=True)
result = linter.lint_file("src/main/java/Example.java", fix=False)
print(linter.format_lint_result(result))

# 检查整个项目
result = linter.lint_project("src/main/java", fix=True)
print(linter.format_lint_result(result))
```

## 依赖管理

| 工具 | 安装命令 | 检查命令 |
|------|---------|---------|
| Javac | 安装JDK | `javac -d /tmp/out Example.java` |
|------|---------|---------|
| Checkstyle | `mvn checkstyle:checkstyle` | `checkstyle -c /path/to/checks.xml` |
| PMD | `mvn pmd:pmd` | `pmd check -d src -R rulesets/java/quickstart.xml` |
| SpotBugs | `mvn spotbugs:spotbugs` | `spotbugs -textui` |
| Google Java Format | 通过Maven/Gradle插件 | `google-java-format -a` |

## 测试计划
1. 单元测试: 验证各工具调用和结果解析
2. 集成测试: 验证完整检查流程
3. 性能测试: 验证大规模项目检查效率
