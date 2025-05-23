# LLMFriendlyPackageManager 模块

## 概述

`LLMFriendlyPackageManager` 是一个用于管理 LLM 友好包的类，它封装了之前分散在 `auto_coder_runner.py` 中的所有 llm_friendly_package_docs 相关操作。

## 特性

- ✅ **库管理**: 添加、删除、列出已添加的库
- ✅ **文档获取**: 获取指定包或所有包的文档内容
- ✅ **库浏览**: 浏览所有可用的库
- ✅ **代理设置**: 设置和管理 Git 代理
- ✅ **仓库刷新**: 更新本地仓库到最新版本
- ✅ **美观显示**: 使用 Rich 表格美观地显示信息

## 基本用法

### 初始化管理器

```python
from autocoder.common.llm_friendly_package import LLMFriendlyPackageManager

# 使用默认配置
manager = LLMFriendlyPackageManager()

# 使用自定义配置
manager = LLMFriendlyPackageManager(
    project_root="/path/to/your/project",
    base_persist_dir="/path/to/your/persistence/directory"
)
```

### 库管理操作

```python
# 添加库（如果需要，会自动克隆仓库）
manager.add_library("moonbit")

# 删除库
manager.remove_library("moonbit")

# 列出已添加的库
added_libs = manager.list_added_libraries()

# 显示已添加的库（美观的表格）
manager.display_added_libraries()
```

### 文档获取

```python
# 获取所有包的文档内容
docs_content = manager.get_docs()

# 获取所有包的文档文件路径
docs_paths = manager.get_docs(return_paths=True)

# 获取特定包的文档
specific_docs = manager.get_docs(package_name="moonbit", return_paths=True)

# 显示特定包的文档路径
manager.display_library_docs("moonbit")
```

### 库浏览

```python
# 获取所有可用库的结构化数据
available_libs = manager.list_all_available_libraries()

# 显示所有可用库（美观的表格）
manager.display_all_libraries()
```

### 仓库管理

```python
# 获取当前代理设置
current_proxy = manager.set_proxy()

# 设置新的代理
manager.set_proxy("https://gitee.com/your-mirror/llm_friendly_packages")

# 刷新仓库
success = manager.refresh_repository()
```

## API 参考

### 类定义

#### `LLMFriendlyPackageManager`

主要的包管理器类。

##### 初始化参数

- `project_root` (str, optional): 项目根目录，默认为当前工作目录
- `base_persist_dir` (str, optional): 持久化基目录，默认为 `.auto-coder/plugins/chat-auto-coder`

### 主要方法

#### 库管理

- `add_library(lib_name: str) -> bool`: 添加库
- `remove_library(lib_name: str) -> bool`: 删除库
- `list_added_libraries() -> List[str]`: 列出已添加的库
- `display_added_libraries() -> None`: 显示已添加的库

#### 文档获取

- `get_docs(package_name: Optional[str] = None, return_paths: bool = False) -> List[str]`: 获取文档
- `get_library_docs_paths(package_name: str) -> List[str]`: 获取特定包的文档路径
- `display_library_docs(package_name: str) -> None`: 显示包的文档路径

#### 库浏览

- `list_all_available_libraries() -> List[LibraryInfo]`: 列出所有可用库
- `display_all_libraries() -> None`: 显示所有可用库

#### 仓库管理

- `set_proxy(proxy_url: Optional[str] = None) -> str`: 设置或获取代理
- `refresh_repository() -> bool`: 刷新仓库

### 数据类

#### `LibraryInfo`

库信息数据类。

```python
@dataclass
class LibraryInfo:
    domain: str          # 域名，如 "github.com"
    username: str        # 用户名，如 "allwefantasy"
    lib_name: str        # 库名，如 "moonbit"
    full_path: str       # 完整路径，如 "allwefantasy/moonbit"
    is_added: bool       # 是否已添加
    has_md_files: bool   # 是否包含 Markdown 文件
```

#### `PackageDoc`

包文档数据类。

```python
@dataclass
class PackageDoc:
    file_path: str                    # 文件路径
    content: Optional[str] = None     # 文件内容
```

## 兼容性

为了保持向后兼容性，原有的 `get_llm_friendly_package_docs` 函数仍然可用，但已被标记为遗留函数。新代码建议使用 `LLMFriendlyPackageManager` 类。

### 迁移指南

#### 从 auto_coder_runner.py 迁移

原有代码：
```python
docs = get_llm_friendly_package_docs(package_name, return_paths=True)
```

新代码：
```python
manager = LLMFriendlyPackageManager()
docs = manager.get_docs(package_name, return_paths=True)
```

#### 从命令行接口迁移

原有的 `/lib` 命令的所有子命令现在都使用新的管理器类：

- `/lib /add <lib_name>` → `manager.add_library(lib_name)`
- `/lib /remove <lib_name>` → `manager.remove_library(lib_name)`
- `/lib /list` → `manager.display_added_libraries()`
- `/lib /list_all` → `manager.display_all_libraries()`
- `/lib /get <package_name>` → `manager.display_library_docs(package_name)`
- `/lib /set-proxy <url>` → `manager.set_proxy(url)`
- `/lib /refresh` → `manager.refresh_repository()`

## 示例

详细的使用示例请参考：
- `llm_friendly_package_example.py` - 完整的使用示例
- `llm_friendly_package_test.py` - 基本功能测试

## 错误处理

管理器类内部会处理常见的错误情况：

- 文件或目录不存在
- Git 操作失败
- 权限问题
- 网络连接问题

大多数方法会返回布尔值或空列表来指示操作是否成功，而不是抛出异常。

## 依赖

- `rich`: 用于美观的表格显示
- `git`: 用于 Git 操作
- `filelock`: 用于文件锁定
- `dataclasses`: 用于数据类
- `typing`: 用于类型提示 