# Token Helper 插件使用指南

Token Helper 插件是 AutoCoder 的一个实用工具，用于为您的代码文件和项目提供令牌（token）计数功能。这个插件帮助您分析代码库中的令牌使用情况，对于理解模型上下文限制、优化大型语言模型成本以及识别可能需要重构的复杂文件非常有价值。

以下是使用 Token Helper 插件的详细指南。

## 插件加载和卸载

```bash
# 查看已加载的插件
coding@auto-coder.chat:~$ /plugins
加载的插件:

# 列出可用插件
coding@auto-coder.chat:~$ /plugins /list
可用插件:
- TokenHelperPlugin (token_helper): 提供文件和项目令牌计数的令牌助手插件
...

# 加载 Token Helper 插件
coding@auto-coder.chat:~$ /plugins /load token_helper
插件 'token_helper' (v0.1.0) 加载成功

# 验证加载状态
coding@auto-coder.chat:~$ /plugins
加载的插件:
- token_helper (v0.1.0): 提供文件和项目令牌计数的令牌助手插件

# 卸载插件 - 如果需要卸载插件
coding@auto-coder.chat:~$ /plugins /unload token_helper
插件 'token_helper' 卸载成功
```

## 核心命令列表

```bash
coding@auto-coder.chat:~$ /token/count      # 计算当前项目中的令牌数
coding@auto-coder.chat:~$ /token/top 20     # 显示按令牌数排序的前 20 个文件
coding@auto-coder.chat:~$ /token/file path/to/file.py  # 计算特定文件中的令牌数
coding@auto-coder.chat:~$ /token/summary    # 按文件类型显示令牌使用摘要
```

## 智能补全演示

```bash
# 输入命令时按空格键触发补全
coding@auto-coder.chat:~$ /token/top[space]
5    10    20    50    100
```

## 使用示例

### 分析项目令牌使用情况

```bash
coding@auto-coder.chat:~$ /token/count
正在计算项目中的令牌数: /home/user/projects/myapp
文件类型: .py

正在扫描文件并计算令牌数...
已处理 10 个文件...
已处理 20 个文件...
已处理 30 个文件...

令牌计数完成！
总文件数: 32
总令牌数: 45,273
使用 /token/top N 查看按令牌数排序的前 N 个文件
使用 /token/summary 查看按文件类型的摘要
```

### 查找令牌数量多的文件

```bash
coding@auto-coder.chat:~$ /token/top 5
按令牌数排序的前 5 个文件:
令牌数     大小 (字节)     文件
---------- --------------- --------------------------------------------------
5,432      19,845          src/server/api/controllers/main_controller.py
3,876      14,234          src/server/models/database.py
3,240      12,105          src/client/components/dashboard.js
2,987      10,876          tests/integration/test_api.py
2,754      9,340           src/server/utils/helpers.py
```

### 按文件类型的令牌摘要

```bash
coding@auto-coder.chat:~$ /token/summary
按文件类型的令牌计数摘要:
扩展名      文件数    令牌数        总数百分比    大小 (KB)    
------------ -------- ------------ ------------ ------------
.py          21       31,245       69.01        114.56      
.js          8        10,432       23.04        45.67       
.md          3        3,596        7.94         12.45       
.html        1        1,245        2.75         3.45        

总文件数: 32
总令牌数: 45,273
总大小: 0.17 MB
项目目录: /home/user/projects/myapp
```

### 分析特定文件

```bash
coding@auto-coder.chat:~$ /token/file src/server/api/controllers/main_controller.py
文件: src/server/api/controllers/main_controller.py
令牌数: 5,432
文件大小: 19,845 字节
每个令牌平均字节数: 3.65
```

## 高级用法

### 自定义项目目录

```bash
# 分析不同的项目目录
coding@auto-coder.chat:~$ /token/count --dir /path/to/other/project

# 或使用替代语法
coding@auto-coder.chat:~$ /token/count dir=/path/to/other/project
```

### 按文件类型筛选

```bash
# 只计算 Python 和 JavaScript 文件
coding@auto-coder.chat:~$ /token/count --type .py,.js

# 使用短选项格式
coding@auto-coder.chat:~$ /token/count -t .py,.js
```

### 排除模式

```bash
# 排除测试文件和迁移文件
coding@auto-coder.chat:~$ /token/count --exclude "test_|migrations"
```

### 组合选项

```bash
# 带有多个选项的复杂示例
coding@auto-coder.chat:~$ /token/count --dir ./backend --type .py,.sql --exclude "test_|migrations|__pycache__"
```

## 重要注意事项

1. 令牌计数基于 AutoCoder 使用的分词器模型
2. 插件自动使用 AutoCoder 中的项目配置
3. 对于大型项目，令牌计数过程可能需要一些时间
4. 令牌计数提供 LLM 上下文使用和成本的估计
5. 必须先运行 `/token/count` 命令才能使用 `/token/top` 或 `/token/summary`
