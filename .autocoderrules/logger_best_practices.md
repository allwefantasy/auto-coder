---
description: 在项目中使用logger的最佳实践和规范
globs: ["**/*.py"]
alwaysApply: false
---

# Logger 最佳实践

## 简要说明
本文档规定了项目中使用日志记录器(logger)的最佳实践和规范，确保日志记录统一、有效且易于维护。

## 基本用法

```python
# 推荐导入方式
from loguru import logger

# 基本使用示例
def some_function():
    try:
        # 正常操作
        result = process_data()
        logger.info(f"数据处理成功: {result}")
    except Exception as e:
        # 错误处理
        logger.warning(f"处理数据时出错: {str(e)}")
        logger.exception(e)  # 自动包含堆栈跟踪
        return None
```

## 日志级别使用规范

- **debug**: 用于详细的调试信息，仅在开发环境中启用
  ```python
  logger.debug(f"变量值: {value}, 状态: {state}")
  ```

- **info**: 用于记录正常操作和状态变化
  ```python
  logger.info(f"用户 {user_id} 登录成功")
  ```

- **warning**: 用于潜在问题和异常情况，但不影响系统主要功能
  ```python
  logger.warning(f"跳过条目 {module_name}，数据格式异常: {type(data)}")
  ```

- **error**: 用于影响功能但不导致程序崩溃的错误
  ```python
  logger.error(f"处理文件 {file_path} 失败: {str(err)}")
  ```

- **critical**: 用于导致系统崩溃或需要立即处理的严重错误
  ```python
  logger.critical(f"数据库连接失败: {str(err)}")
  ```

- **exception**: 用于记录异常信息，自动包含堆栈跟踪
  ```python
  try:
      # 操作
  except Exception as e:
      logger.warning(f"简短错误描述: {str(e)}")
      logger.exception(e)  # 添加详细错误堆栈
  ```

## 最佳实践

1. **结构化日志信息**:
   - 使用 f-strings 格式化日志内容
   - 在日志中包含关键标识符(ID, 路径等)方便追踪
   - 保持日志消息简洁明了

2. **异常处理日志**:
   - 总是使用 `try-except` 包裹可能抛出异常的代码
   - 使用 `logger.warning` 或 `logger.error` 记录简要错误信息
   - 同时使用 `logger.exception(e)` 记录详细堆栈信息

3. **避免冗余日志**:
   - 避免在循环中记录重复信息
   - 针对大批量操作，考虑使用聚合日志或抽样记录

4. **上下文信息**:
   - 在日志中包含足够的上下文信息以便问题定位
   - 记录操作对象、关键参数和结果状态

## 实际示例

以下是从项目中提取的实际使用示例:

```python
# 处理索引数据时的错误处理
def read_index(self) -> List[IndexItem]:
    if not os.path.exists(self.index_file):
        return []

    with open(self.index_file, "r", encoding="utf-8") as file:
        index_data = json.load(file)

    index_items = []
    for module_name, data in index_data.items():
        try:
            index_item = IndexItem(
                module_name=module_name,
                symbols=data["symbols"],
                last_modified=data["last_modified"],
                md5=data["md5"],
            )
            index_items.append(index_item)
        except (KeyError, TypeError) as e:
            logger.warning(f"处理索引条目 {module_name} 时出错: {str(e)}")
            logger.exception(e)
            continue

    return index_items 