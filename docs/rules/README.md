

# AutoCoder 模块文档规范

本目录包含了 AutoCoder 项目中模块文档的标准化规范和工具，确保所有模块都有高质量、结构一致的文档。

## 📚 文档列表

### 1. 核心规范文档

#### [module_documentation_template.md](./module_documentation_template.md)
**完整的模块文档生成指南**
- 详细的文档结构模板
- 内容填写指南和规范
- 特殊模块类型的处理方法
- 质量检查清单和维护指南

#### [module_doc_quick_reference.md](./module_doc_quick_reference.md)
**快速参考指南**
- 简化的文档结构清单
- 模板填写检查表
- 常见模块类型的特殊要求
- 编写提示和质量标准

### 2. 自动化工具

#### [generate_module_doc.py](./generate_module_doc.py)
**模块文档生成器**
- 自动扫描模块目录结构
- 提取Python文件的基本信息
- 生成标准化的文档模板
- 支持命令行参数配置

## 🎯 使用流程

### 快速开始

1. **查看参考示例**
   ```bash
   # 查看完整的参考实现
   cat src/autocoder/common/v2/agent/.meta.mod.md
   ```

2. **使用自动生成器**
   ```bash
   # 为新模块生成文档模板
   python docs/rules/generate_module_doc.py src/your/module/path
   ```

3. **完善文档内容**
   - 参考 `module_doc_quick_reference.md` 中的检查表
   - 根据模块类型补充特殊内容
   - 确保代码示例可运行

4. **质量检查**
   - 使用 `module_documentation_template.md` 中的质量检查清单
   - 验证文档的完整性和准确性

### 详细流程

#### 步骤1：信息收集
使用 `module_documentation_template.md` 中的指南收集：
- 模块基本信息
- 文件结构
- API 接口
- 依赖关系

#### 步骤2：生成基础模板
```bash
# 生成文档模板
python docs/rules/generate_module_doc.py [模块路径] -n "[模块名称]"

# 示例
python docs/rules/generate_module_doc.py src/autocoder/events -n "事件系统"
```

#### 步骤3：内容完善
根据模块类型补充特殊内容：

- **🔧 工具类模块**：详细列出所有工具及参数
- **📡 事件驱动模块**：说明事件类型和触发条件  
- **⚙️ 配置驱动模块**：详细说明配置选项
- **🏗️ 架构类模块**：提供完整的依赖图

#### 步骤4：质量验证
使用检查清单验证：
- [ ] 内容完整性
- [ ] 代码质量
- [ ] 文档结构
- [ ] 用户体验

## 📋 文档结构标准

### 必需章节
1. **标题和概述** - 模块名称和功能描述
2. **目录结构** - 完整的文件树和功能注释
3. **快速开始** - API使用指南和代码示例
4. **核心组件详解** - 主要类和子系统架构
5. **Mermaid 依赖图** - 可视化的依赖关系

### 可选章节
- 配置管理
- 错误处理
- 最佳实践
- 性能优化
- 扩展指南

## 🛠️ 工具使用

### 生成器参数
```bash
python generate_module_doc.py [模块路径] [选项]

选项：
  -n, --name     模块名称
  -o, --output   输出文件路径
  -h, --help     显示帮助信息
```

### 使用示例
```bash
# 基本使用
python generate_module_doc.py src/autocoder/common/v2/agent

# 指定模块名称
python generate_module_doc.py src/autocoder/events -n "事件管理系统"

# 指定输出路径
python generate_module_doc.py src/autocoder/rag -o docs/rag_module.md
```

## 📖 参考示例

### 完整实现参考
- **[src/autocoder/common/v2/agent/.meta.mod.md](../../../src/autocoder/common/v2/agent/.meta.mod.md)**
  - 工具系统的详细分类和定义
  - 事件系统的完整类型说明
  - 复杂依赖关系的可视化表达
  - 多种使用模式的代码示例

### 模块类型示例

#### 工具类模块示例
```markdown
#### 工具类型定义

**文件操作工具：**

- **`read_file`**: 文件读取工具
  - **类型**: `ReadFileTool`
  - **参数**: `path: str` - 文件路径
  - **功能**: 读取文件内容
  - **示例**: `<read_file><path>src/main.py</path></read_file>`
```

#### 事件驱动模块示例
```markdown
#### 事件类型定义

**LLM 交互事件：**

- **`LLMOutputEvent`**: LLM输出事件
  - **触发时机**: LLM生成文本时
  - **数据结构**: `{ text: str }`
  - **用途**: 承载LLM生成的文本内容
```

## ✅ 质量标准

### 内容质量
- **准确性**：代码示例可运行，说明与实现一致
- **完整性**：覆盖所有重要功能和使用场景
- **清晰性**：结构清晰，逻辑流畅
- **实用性**：新手能快速上手使用

### 格式规范
- **标题层级**：使用标准的Markdown标题层级
- **代码格式**：使用正确的语法高亮
- **图表规范**：Mermaid图表准确反映依赖关系
- **链接有效**：所有内部链接和引用正确

### 维护要求
- **同步更新**：代码变更时及时更新文档
- **版本标注**：重要变更记录版本信息
- **定期检查**：定期验证文档的准确性

## 🔄 维护流程

### 更新时机
- 模块功能发生重大变更
- 添加新的公开API
- 修复重要bug
- 架构调整

### 更新内容
- 同步更新代码示例
- 更新依赖关系图
- 修正过时的说明
- 添加新功能的文档

### 版本管理
- 在文档中标注适用版本
- 保留重要变更的历史记录
- 与代码版本保持同步

通过遵循这套规范和使用提供的工具，可以确保 AutoCoder 项目中所有模块都有高质量、结构一致的文档，便于开发者理解和使用。

