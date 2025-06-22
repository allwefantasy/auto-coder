
# Command File Manager 模块

该模块提供了一套完整的API，用于管理和分析 `.autocodercommands` 目录中的命令文件。它能够列出目录中的命令文件、读取指定文件内容，以及提取文件中的 Jinja2 变量及其元数据。特别适合需要处理模板文件和动态生成内容的场景。

## 快速开始

### CommandManager 基本使用

```python
from autocoder.common.command_file_manager import CommandManager

# 1. 创建命令管理器实例
manager = CommandManager("/path/to/.autocodercommands")

# 2. 列出所有命令文件
result = manager.list_command_files(recursive=True)
if result.success:
    print(f"找到 {len(result.command_files)} 个命令文件:")
    for file_path in result.command_files:
        print(f"  - {file_path}")
else:
    print(f"列出文件失败: {result.errors}")

# 3. 读取指定命令文件
command_file = manager.read_command_file("example.md")
if command_file:
    print(f"文件名: {command_file.file_name}")
    print(f"文件路径: {command_file.file_path}")
    print(f"文件内容:\n{command_file.content}")
else:
    print("文件读取失败")

# 4. 分析文件中的 Jinja2 变量
analysis = manager.analyze_command_file("example.md")
if analysis:
    print(f"文件 {analysis.file_name} 包含的变量:")
    for var in analysis.variables:
        print(f"  - {var.name}")
        if var.default_value:
            print(f"    默认值: {var.default_value}")
        if var.description:
            print(f"    描述: {var.description}")
else:
    print("文件分析失败")

# 5. 获取所有文件中的变量映射
variables_map = manager.get_all_variables(recursive=True)
for file_path, variables in variables_map.items():
    print(f"文件 {file_path} 中的变量: {', '.join(variables)}")
```

## CommandManager 类详解

### 初始化

```python
from autocoder.common.command_file_manager import CommandManager

# 使用绝对路径初始化
manager = CommandManager("/absolute/path/to/.autocodercommands")

# 使用相对路径初始化
manager = CommandManager(".autocodercommands")

# 使用项目根目录下的命令目录
import os
project_root = os.getcwd()
commands_dir = os.path.join(project_root, ".autocodercommands")
manager = CommandManager(commands_dir)
```

### 核心方法详解

#### 1. list_command_files() - 列出命令文件

**方法签名:**
```python
def list_command_files(self, recursive: bool = True) -> ListCommandsResult
```

**参数:**
- `recursive` (bool): 是否递归搜索子目录，默认为 True

**返回值:** `ListCommandsResult` 对象
- `success` (bool): 操作是否成功
- `command_files` (List[str]): 找到的命令文件路径列表
- `errors` (Dict[str, str]): 错误信息映射

**使用示例:**
```python
# 递归搜索所有命令文件
result = manager.list_command_files(recursive=True)
if result.success:
    print("找到的命令文件:")
    for file_path in result.command_files:
        print(f"  {file_path}")
else:
    print("搜索失败:")
    for path, error in result.errors.items():
        print(f"  {path}: {error}")

# 只搜索顶层目录
result = manager.list_command_files(recursive=False)
if result.success:
    print(f"顶层目录有 {len(result.command_files)} 个命令文件")
```

#### 2. read_command_file() - 读取命令文件

**方法签名:**
```python
def read_command_file(self, file_name: str) -> Optional[CommandFile]
```

**参数:**
- `file_name` (str): 要读取的文件名（可以是相对路径）

**返回值:** `CommandFile` 对象或 None
- `file_path` (str): 文件的完整路径
- `file_name` (str): 文件名
- `content` (str): 文件内容

**使用示例:**
```python
# 读取根目录下的文件
command_file = manager.read_command_file("template.md")
if command_file:
    print(f"文件: {command_file.file_name}")
    print(f"路径: {command_file.file_path}")
    print(f"内容长度: {len(command_file.content)} 字符")
    print(f"内容预览: {command_file.content[:100]}...")
else:
    print("文件不存在或读取失败")

# 读取子目录中的文件
command_file = manager.read_command_file("templates/project.md")
if command_file:
    print(f"成功读取子目录文件: {command_file.file_name}")

# 批量读取文件
files_result = manager.list_command_files()
if files_result.success:
    for file_path in files_result.command_files:
        file_name = os.path.basename(file_path)
        command_file = manager.read_command_file(file_name)
        if command_file:
            print(f"已读取: {command_file.file_name} ({len(command_file.content)} 字符)")
```

#### 3. analyze_command_file() - 分析命令文件变量

**方法签名:**
```python
def analyze_command_file(self, file_name: str) -> Optional[CommandFileAnalysisResult]
```

**参数:**
- `file_name` (str): 要分析的文件名

**返回值:** `CommandFileAnalysisResult` 对象或 None
- `file_path` (str): 文件路径
- `file_name` (str): 文件名
- `variables` (List[JinjaVariable]): 提取的变量列表
- `raw_variables` (Set[str]): 原始变量名集合

**使用示例:**
```python
# 基本分析
analysis = manager.analyze_command_file("template.md")
if analysis:
    print(f"分析文件: {analysis.file_name}")
    print(f"找到 {len(analysis.variables)} 个变量:")
    
    for var in analysis.variables:
        print(f"  变量名: {var.name}")
        if var.default_value:
            print(f"  默认值: {var.default_value}")
        if var.description:
            print(f"  描述: {var.description}")
        print("  ---")
else:
    print("文件分析失败")

# 分析变量类型
analysis = manager.analyze_command_file("template.md")
if analysis:
    required_vars = [var for var in analysis.variables if var.default_value is None]
    optional_vars = [var for var in analysis.variables if var.default_value is not None]
    
    print(f"必需变量 ({len(required_vars)}):")
    for var in required_vars:
        print(f"  - {var.name}: {var.description or '无描述'}")
    
    print(f"可选变量 ({len(optional_vars)}):")
    for var in optional_vars:
        print(f"  - {var.name} (默认: {var.default_value}): {var.description or '无描述'}")

# 获取原始变量集合
analysis = manager.analyze_command_file("template.md")
if analysis:
    print(f"原始变量集合: {analysis.raw_variables}")
    print(f"变量总数: {len(analysis.raw_variables)}")
```

#### 4. get_all_variables() - 获取所有变量映射

**方法签名:**
```python
def get_all_variables(self, recursive: bool = False) -> Dict[str, Set[str]]
```

**参数:**
- `recursive` (bool): 是否递归搜索，默认为 False

**返回值:** `Dict[str, Set[str]]` - 文件路径到变量名集合的映射

**使用示例:**
```python
# 获取所有文件的变量映射
variables_map = manager.get_all_variables(recursive=True)

print("变量使用统计:")
all_variables = set()
file_count = {}

for file_path, variables in variables_map.items():
    print(f"{file_path}: {len(variables)} 个变量")
    print(f"  变量: {', '.join(sorted(variables))}")
    
    # 统计每个变量在多少个文件中使用
    for var in variables:
        all_variables.add(var)
        file_count[var] = file_count.get(var, 0) + 1

print(f"\n总计唯一变量: {len(all_variables)}")
print("变量使用频率:")
for var, count in sorted(file_count.items(), key=lambda x: x[1], reverse=True):
    print(f"  {var}: {count} 个文件")

# 查找未使用的变量
common_vars = {'project_name', 'author', 'version', 'description'}
unused_vars = common_vars - all_variables
if unused_vars:
    print(f"未使用的常见变量: {unused_vars}")
```

#### 5. get_command_file_path() - 获取文件完整路径

**方法签名:**
```python
def get_command_file_path(self, file_name: str) -> str
```

**参数:**
- `file_name` (str): 文件名

**返回值:** `str` - 文件的完整路径

**使用示例:**
```python
# 获取文件完整路径
file_path = manager.get_command_file_path("example.md")
print(f"文件完整路径: {file_path}")

# 检查文件是否存在
import os
file_path = manager.get_command_file_path("template.md")
if os.path.exists(file_path):
    print(f"文件存在: {file_path}")
else:
    print(f"文件不存在: {file_path}")

# 获取文件信息
file_path = manager.get_command_file_path("example.md")
if os.path.exists(file_path):
    stat = os.stat(file_path)
    print(f"文件大小: {stat.st_size} 字节")
    print(f"修改时间: {stat.st_mtime}")
```

## 实际使用场景

### 场景 1: 项目模板管理器

```python
from autocoder.common.command_file_manager import CommandManager
import os
from pathlib import Path

class ProjectTemplateManager:
    def __init__(self, templates_dir: str):
        """初始化项目模板管理器"""
        self.manager = CommandManager(templates_dir)
    
    def list_templates(self):
        """列出所有可用模板"""
        result = self.manager.list_command_files(recursive=True)
        if not result.success:
            return {"success": False, "errors": result.errors}
        
        templates = []
        for file_path in result.command_files:
            # 分析模板获取元信息
            file_name = os.path.basename(file_path)
            analysis = self.manager.analyze_command_file(file_name)
            
            template_info = {
                "name": file_name,
                "path": file_path,
                "variables_count": len(analysis.variables) if analysis else 0
            }
            
            if analysis:
                template_info["required_vars"] = [
                    var.name for var in analysis.variables 
                    if var.default_value is None
                ]
                template_info["optional_vars"] = [
                    var.name for var in analysis.variables 
                    if var.default_value is not None
                ]
            
            templates.append(template_info)
        
        return {"success": True, "templates": templates}
    
    def get_template_requirements(self, template_name: str):
        """获取模板的变量要求"""
        analysis = self.manager.analyze_command_file(template_name)
        if not analysis:
            return {"success": False, "error": f"无法分析模板 '{template_name}'"}
        
        requirements = {
            "required_variables": [],
            "optional_variables": []
        }
        
        for var in analysis.variables:
            var_info = {
                "name": var.name,
                "description": var.description or "无描述"
            }
            
            if var.default_value is None:
                requirements["required_variables"].append(var_info)
            else:
                var_info["default_value"] = var.default_value
                requirements["optional_variables"].append(var_info)
        
        return {"success": True, "requirements": requirements}
    
    def validate_template_variables(self, template_name: str, provided_vars: dict):
        """验证提供的变量是否满足模板要求"""
        analysis = self.manager.analyze_command_file(template_name)
        if not analysis:
            return {"success": False, "error": f"无法分析模板 '{template_name}'"}
        
        required_vars = {var.name for var in analysis.variables if var.default_value is None}
        missing_vars = required_vars - set(provided_vars.keys())
        
        if missing_vars:
            return {
                "success": False, 
                "valid": False,
                "missing_variables": list(missing_vars)
            }
        
        return {"success": True, "valid": True}

# 使用示例
template_manager = ProjectTemplateManager(".autocodercommands")

# 列出所有模板
templates_result = template_manager.list_templates()
if templates_result["success"]:
    print("可用模板:")
    for template in templates_result["templates"]:
        print(f"  - {template['name']} ({template['variables_count']} 个变量)")

# 获取特定模板的要求
requirements = template_manager.get_template_requirements("project_template.md")
if requirements["success"]:
    req = requirements["requirements"]
    print(f"必需变量: {[var['name'] for var in req['required_variables']]}")
    print(f"可选变量: {[var['name'] for var in req['optional_variables']]}")

# 验证变量
provided_vars = {"project_name": "MyProject", "author": "John Doe"}
validation = template_manager.validate_template_variables("project_template.md", provided_vars)
if validation["success"]:
    if validation["valid"]:
        print("✓ 变量验证通过")
    else:
        print(f"✗ 缺少变量: {validation['missing_variables']}")
```

### 场景 2: 文档生成器

```python
from autocoder.common.command_file_manager import CommandManager
from jinja2 import Environment, Template
import json

class DocumentationGenerator:
    def __init__(self, docs_dir: str):
        """初始化文档生成器"""
        self.manager = CommandManager(docs_dir)
        self.jinja_env = Environment()
    
    def generate_document(self, template_name: str, variables: dict, output_path: str = None):
        """生成文档"""
        try:
            # 读取模板
            command_file = self.manager.read_command_file(template_name)
            if not command_file:
                return {"success": False, "error": f"模板 '{template_name}' 不存在"}
            
            # 分析变量并应用默认值
            analysis = self.manager.analyze_command_file(template_name)
            final_vars = variables.copy()
            
            if analysis:
                # 检查必需变量
                required_vars = {var.name for var in analysis.variables if var.default_value is None}
                missing_vars = required_vars - set(variables.keys())
                if missing_vars:
                    return {"success": False, "error": f"缺少必需变量: {missing_vars}"}
                
                # 应用默认值
                for var in analysis.variables:
                    if var.name not in final_vars and var.default_value:
                        final_vars[var.name] = var.default_value
            
            # 渲染模板
            template = self.jinja_env.from_string(command_file.content)
            rendered_content = template.render(**final_vars)
            
            # 保存到文件（如果指定了输出路径）
            if output_path:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(rendered_content)
                return {"success": True, "output_path": output_path, "content": rendered_content}
            
            return {"success": True, "content": rendered_content}
            
        except Exception as e:
            return {"success": False, "error": f"生成文档时出错: {str(e)}"}
    
    def batch_generate(self, template_vars_mapping: dict, output_dir: str = None):
        """批量生成文档"""
        results = {}
        
        for template_name, variables in template_vars_mapping.items():
            output_path = None
            if output_dir:
                import os
                output_path = os.path.join(output_dir, f"generated_{template_name}")
            
            result = self.generate_document(template_name, variables, output_path)
            results[template_name] = result
        
        return results
    
    def preview_template(self, template_name: str, variables: dict):
        """预览模板渲染结果（不保存文件）"""
        return self.generate_document(template_name, variables, output_path=None)

# 使用示例
doc_generator = DocumentationGenerator(".autocodercommands")

# 生成单个文档
variables = {
    "project_name": "AutoCoder",
    "version": "1.0.0",
    "author": "Development Team",
    "description": "一个自动化代码生成工具"
}

result = doc_generator.generate_document("README_template.md", variables, "generated_README.md")
if result["success"]:
    print(f"文档已生成: {result['output_path']}")
else:
    print(f"生成失败: {result['error']}")

# 批量生成
batch_mapping = {
    "README_template.md": {
        "project_name": "Project A",
        "version": "1.0.0",
        "author": "Team A"
    },
    "CONTRIBUTING_template.md": {
        "project_name": "Project A",
        "contact_email": "team-a@example.com"
    }
}

batch_results = doc_generator.batch_generate(batch_mapping, "output_docs")
for template, result in batch_results.items():
    if result["success"]:
        print(f"✓ {template} 生成成功")
    else:
        print(f"✗ {template} 生成失败: {result['error']}")
```

### 场景 3: 配置文件管理器

```python
from autocoder.common.command_file_manager import CommandManager
import yaml
import json

class ConfigurationManager:
    def __init__(self, config_templates_dir: str):
        """初始化配置管理器"""
        self.manager = CommandManager(config_templates_dir)
    
    def get_available_configs(self):
        """获取所有可用的配置模板"""
        result = self.manager.list_command_files(recursive=True)
        if not result.success:
            return {"success": False, "errors": result.errors}
        
        configs = []
        for file_path in result.command_files:
            file_name = os.path.basename(file_path)
            analysis = self.manager.analyze_command_file(file_name)
            
            config_info = {
                "name": file_name,
                "path": file_path,
                "type": self._detect_config_type(file_name)
            }
            
            if analysis:
                config_info["variables"] = [
                    {
                        "name": var.name,
                        "required": var.default_value is None,
                        "default": var.default_value,
                        "description": var.description
                    }
                    for var in analysis.variables
                ]
            
            configs.append(config_info)
        
        return {"success": True, "configurations": configs}
    
    def _detect_config_type(self, file_name: str):
        """检测配置文件类型"""
        if 'docker' in file_name.lower():
            return 'docker'
        elif 'nginx' in file_name.lower():
            return 'nginx'
        elif 'database' in file_name.lower() or 'db' in file_name.lower():
            return 'database'
        elif 'api' in file_name.lower():
            return 'api'
        else:
            return 'general'
    
    def generate_config(self, template_name: str, environment_vars: dict):
        """生成配置文件"""
        try:
            # 读取模板
            command_file = self.manager.read_command_file(template_name)
            if not command_file:
                return {"success": False, "error": f"配置模板 '{template_name}' 不存在"}
            
            # 分析并验证变量
            analysis = self.manager.analyze_command_file(template_name)
            if analysis:
                required_vars = {var.name for var in analysis.variables if var.default_value is None}
                missing_vars = required_vars - set(environment_vars.keys())
                if missing_vars:
                    return {"success": False, "error": f"缺少必需的环境变量: {missing_vars}"}
                
                # 应用默认值
                final_vars = environment_vars.copy()
                for var in analysis.variables:
                    if var.name not in final_vars and var.default_value:
                        final_vars[var.name] = var.default_value
            else:
                final_vars = environment_vars
            
            # 渲染配置
            from jinja2 import Environment
            env = Environment()
            template = env.from_string(command_file.content)
            rendered_config = template.render(**final_vars)
            
            return {"success": True, "config_content": rendered_config, "variables_used": final_vars}
            
        except Exception as e:
            return {"success": False, "error": f"生成配置时出错: {str(e)}"}
    
    def validate_environment(self, template_name: str, environment_vars: dict):
        """验证环境变量是否满足配置要求"""
        analysis = self.manager.analyze_command_file(template_name)
        if not analysis:
            return {"success": False, "error": f"无法分析模板 '{template_name}'"}
        
        validation_result = {
            "valid": True,
            "missing_required": [],
            "available_optional": [],
            "unused_provided": []
        }
        
        template_vars = {var.name for var in analysis.variables}
        required_vars = {var.name for var in analysis.variables if var.default_value is None}
        optional_vars = {var.name for var in analysis.variables if var.default_value is not None}
        
        # 检查缺失的必需变量
        missing_required = required_vars - set(environment_vars.keys())
        if missing_required:
            validation_result["valid"] = False
            validation_result["missing_required"] = list(missing_required)
        
        # 检查可用的可选变量
        provided_optional = set(environment_vars.keys()) & optional_vars
        validation_result["available_optional"] = list(provided_optional)
        
        # 检查未使用的提供变量
        unused_provided = set(environment_vars.keys()) - template_vars
        validation_result["unused_provided"] = list(unused_provided)
        
        return {"success": True, "validation": validation_result}

# 使用示例
config_manager = ConfigurationManager(".autocodercommands/configs")

# 获取可用配置
configs_result = config_manager.get_available_configs()
if configs_result["success"]:
    print("可用配置模板:")
    for config in configs_result["configurations"]:
        print(f"  - {config['name']} ({config['type']})")
        if 'variables' in config:
            required_vars = [v['name'] for v in config['variables'] if v['required']]
            if required_vars:
                print(f"    必需变量: {required_vars}")

# 验证环境变量
env_vars = {
    "database_host": "localhost",
    "database_port": "5432",
    "database_name": "myapp",
    "database_user": "admin"
}

validation = config_manager.validate_environment("database_config.yml", env_vars)
if validation["success"]:
    val_result = validation["validation"]
    if val_result["valid"]:
        print("✓ 环境变量验证通过")
    else:
        print(f"✗ 缺少必需变量: {val_result['missing_required']}")

# 生成配置
config_result = config_manager.generate_config("database_config.yml", env_vars)
if config_result["success"]:
    print("生成的配置:")
    print(config_result["config_content"])
    
    # 保存到文件
    with open("database.yml", "w") as f:
        f.write(config_result["config_content"])
    print("配置已保存到 database.yml")
```

## 错误处理最佳实践

### 完整的错误处理示例

```python
from autocoder.common.command_file_manager import CommandManager
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def robust_command_manager_usage(commands_dir: str):
    """健壮的 CommandManager 使用示例"""
    try:
        # 初始化管理器
        manager = CommandManager(commands_dir)
        logger.info(f"初始化命令管理器，目录: {commands_dir}")
        
        # 1. 检查目录是否存在
        import os
        if not os.path.exists(commands_dir):
            logger.error(f"命令目录不存在: {commands_dir}")
            return {"success": False, "error": "命令目录不存在"}
        
        # 2. 列出文件并处理错误
        files_result = manager.list_command_files(recursive=True)
        if not files_result.success:
            logger.error("列出命令文件失败")
            for path, error in files_result.errors.items():
                logger.error(f"  {path}: {error}")
            return {"success": False, "errors": files_result.errors}
        
        if not files_result.command_files:
            logger.warning("未找到任何命令文件")
            return {"success": True, "message": "目录中没有命令文件"}
        
        logger.info(f"找到 {len(files_result.command_files)} 个命令文件")
        
        # 3. 逐个处理文件
        processed_files = []
        failed_files = []
        
        for file_path in files_result.command_files:
            file_name = os.path.basename(file_path)
            
            try:
                # 读取文件
                command_file = manager.read_command_file(file_name)
                if not command_file:
                    logger.warning(f"无法读取文件: {file_name}")
                    failed_files.append({"file": file_name, "error": "读取失败"})
                    continue
                
                # 分析文件
                analysis = manager.analyze_command_file(file_name)
                if not analysis:
                    logger.warning(f"无法分析文件: {file_name}")
                    failed_files.append({"file": file_name, "error": "分析失败"})
                    continue
                
                # 处理成功
                file_info = {
                    "name": command_file.file_name,
                    "path": command_file.file_path,
                    "content_length": len(command_file.content),
                    "variables_count": len(analysis.variables),
                    "variables": [var.name for var in analysis.variables]
                }
                
                processed_files.append(file_info)
                logger.info(f"成功处理文件: {file_name}")
                
            except Exception as e:
                logger.error(f"处理文件 {file_name} 时出错: {str(e)}")
                failed_files.append({"file": file_name, "error": str(e)})
        
        # 4. 生成统计信息
        total_variables = set()
        for file_info in processed_files:
            total_variables.update(file_info["variables"])
        
        result = {
            "success": True,
            "statistics": {
                "total_files": len(files_result.command_files),
                "processed_files": len(processed_files),
                "failed_files": len(failed_files),
                "unique_variables": len(total_variables)
            },
            "processed_files": processed_files,
            "failed_files": failed_files,
            "all_variables": list(total_variables)
        }
        
        logger.info(f"处理完成: {len(processed_files)} 成功, {len(failed_files)} 失败")
        return result
        
    except Exception as e:
        logger.error(f"CommandManager 使用过程中发生严重错误: {str(e)}")
        return {"success": False, "error": f"严重错误: {str(e)}"}

# 使用示例
result = robust_command_manager_usage(".autocodercommands")
if result["success"]:
    stats = result["statistics"]
    print(f"处理统计:")
    print(f"  总文件数: {stats['total_files']}")
    print(f"  成功处理: {stats['processed_files']}")
    print(f"  失败文件: {stats['failed_files']}")
    print(f"  唯一变量: {stats['unique_variables']}")
    
    if result["failed_files"]:
        print("失败文件:")
        for failed in result["failed_files"]:
            print(f"  - {failed['file']}: {failed['error']}")
else:
    print(f"操作失败: {result['error']}")
```

## 性能优化建议

### 1. 大量文件处理优化

```python
from concurrent.futures import ThreadPoolExecutor
import time

def optimized_bulk_processing(manager: CommandManager, max_workers: int = 4):
    """优化的批量处理"""
    start_time = time.time()
    
    # 获取文件列表
    files_result = manager.list_command_files(recursive=True)
    if not files_result.success:
        return {"success": False, "errors": files_result.errors}
    
    def process_single_file(file_path):
        """处理单个文件"""
        file_name = os.path.basename(file_path)
        try:
            command_file = manager.read_command_file(file_name)
            if not command_file:
                return {"file": file_name, "success": False, "error": "读取失败"}
            
            analysis = manager.analyze_command_file(file_name)
            if not analysis:
                return {"file": file_name, "success": False, "error": "分析失败"}
            
            return {
                "file": file_name,
                "success": True,
                "variables": [var.name for var in analysis.variables],
                "content_length": len(command_file.content)
            }
        except Exception as e:
            return {"file": file_name, "success": False, "error": str(e)}
    
    # 并行处理
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(process_single_file, file_path): file_path
            for file_path in files_result.command_files
        }
        
        for future in future_to_file:
            results.append(future.result())
    
    # 统计结果
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    
    processing_time = time.time() - start_time
    
    return {
        "success": True,
        "processing_time": processing_time,
        "total_files": len(results),
        "successful_files": len(successful),
        "failed_files": len(failed),
        "results": results
    }

# 使用示例
manager = CommandManager(".autocodercommands")
result = optimized_bulk_processing(manager, max_workers=8)

if result["success"]:
    print(f"批量处理完成:")
    print(f"  处理时间: {result['processing_time']:.2f} 秒")
    print(f"  总文件数: {result['total_files']}")
    print(f"  成功: {result['successful_files']}")
    print(f"  失败: {result['failed_files']}")
```

### 2. 缓存机制

```python
import hashlib
import pickle
import os
from typing import Dict, Any

class CachedCommandManager:
    """带缓存功能的 CommandManager 包装器"""
    
    def __init__(self, commands_dir: str, cache_dir: str = ".cache"):
        self.manager = CommandManager(commands_dir)
        self.cache_dir = cache_dir
        self._ensure_cache_dir()
        self._memory_cache: Dict[str, Any] = {}
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        os.makedirs(self.cache_dir, exist_ok=True)
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件内容哈希"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def _get_cache_path(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        return os.path.join(self.cache_dir, f"{cache_key}.cache")
    
    def _load_from_cache(self, cache_key: str):
        """从缓存加载数据"""
        cache_path = self._get_cache_path(cache_key)
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except:
                pass
        return None
    
    def _save_to_cache(self, cache_key: str, data):
        """保存数据到缓存"""
        cache_path = self._get_cache_path(cache_key)
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
        except:
            pass
    
    def analyze_command_file(self, file_name: str):
        """带缓存的文件分析"""
        file_path = self.manager.get_command_file_path(file_name)
        file_hash = self._get_file_hash(file_path)
        cache_key = f"analysis_{file_name}_{file_hash}"
        
        # 检查内存缓存
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]
        
        # 检查磁盘缓存
        cached_result = self._load_from_cache(cache_key)
        if cached_result is not None:
            self._memory_cache[cache_key] = cached_result
            return cached_result
        
        # 执行分析
        result = self.manager.analyze_command_file(file_name)
        
        # 保存到缓存
        if result:
            self._memory_cache[cache_key] = result
            self._save_to_cache(cache_key, result)
        
        return result
    
    def clear_cache(self):
        """清理缓存"""
        self._memory_cache.clear()
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
        self._ensure_cache_dir()

# 使用示例
cached_manager = CachedCommandManager(".autocodercommands", ".command_cache")

# 第一次分析（会缓存结果）
start_time = time.time()
analysis1 = cached_manager.analyze_command_file("large_template.md")
first_time = time.time() - start_time

# 第二次分析（从缓存读取）
start_time = time.time()
analysis2 = cached_manager.analyze_command_file("large_template.md")
cached_time = time.time() - start_time

print(f"首次分析时间: {first_time:.4f} 秒")
print(f"缓存读取时间: {cached_time:.4f} 秒")
print(f"性能提升: {first_time/cached_time:.1f}x")
```

## 总结

CommandManager 类是 Command File Manager 模块的核心，提供了完整的命令文件管理功能：

1. **文件管理**: 列出、读取命令文件
2. **变量分析**: 提取和分析 Jinja2 变量
3. **批量操作**: 处理多个文件的变量映射
4. **路径管理**: 处理文件路径和目录结构

