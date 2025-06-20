# Auto-Coder SDK 集成测试项目

本项目用于验证 Auto-Coder SDK 的功能是否正常工作。

## 项目结构

```
sdk_integration_test/
├── README.md              # 本文档
├── test_project.py        # 测试项目代码
├── test_python_api.py     # Python API 测试脚本
├── test_cli.py            # CLI 测试脚本
└── run_tests.py           # 主测试运行脚本
```

## 测试内容

### Python API 测试 (`test_python_api.py`)

测试以下功能：
- 同步查询 (`query_sync`)
- 异步查询 (`query`)
- 代码修改 (`modify_code`)
- 流式代码修改 (`modify_code_stream`)

### CLI 测试 (`test_cli.py`)

测试以下命令行功能：
- 帮助命令 (`--help`)
- 版本命令 (`--version`)
- 基本查询 (`-p "query"`)
- JSON 输出 (`--output-format json`)
- 流式 JSON 输出 (`--output-format stream-json`)

## 运行测试

### 运行所有测试

```bash
cd examples/sdk_integration_test
python run_tests.py
```

### 运行单个测试

```bash
# 运行 Python API 测试
python test_python_api.py

# 运行 CLI 测试
python test_cli.py
```

## 测试结果说明

### 成功的测试
- 显示 ✅ 符号
- 返回码为 0
- 输出相关的响应内容

### 失败的测试
- 显示 ❌ 符号
- 返回码为非 0
- 输出错误信息

## 注意事项

1. **环境设置**: 测试脚本会自动设置 `PYTHONPATH` 环境变量
2. **模拟模式**: 如果无法导入 `auto_coder_runner`，系统会使用模拟模式
3. **超时设置**: CLI 测试设置了 30 秒的超时时间
4. **依赖检查**: 确保所有必要的依赖都已安装

## 预期行为

### Python API 测试预期结果
- 同步查询应返回包含查询内容的响应
- 异步查询应产生消息流
- 代码修改应返回 `CodeModificationResult` 对象
- 流式代码修改应产生 `StreamEvent` 流

### CLI 测试预期结果
- 帮助命令应显示使用说明
- 版本命令应显示版本信息
- 查询命令应返回响应内容
- JSON 输出应返回格式化的 JSON

## 调试指南

如果测试失败，请检查：

1. **导入错误**: 确保 `PYTHONPATH` 正确设置
2. **模块缺失**: 确保所有必要的模块都存在
3. **权限问题**: 确保有足够的文件系统权限
4. **超时问题**: 如果命令执行时间过长，可能需要调整超时设置

## 扩展测试

要添加新的测试：

1. 在相应的测试文件中添加新的测试函数
2. 在 `run_tests.py` 中添加新的测试脚本
3. 更新本 README 文档

## 故障排除

### 常见问题

1. **模块导入失败**
   ```
   ModuleNotFoundError: No module named 'autocoder.sdk'
   ```
   解决方案: 确保从项目根目录运行测试，或正确设置 `PYTHONPATH`

2. **CLI 命令不存在**
   ```
   python: can't open file 'autocoder.sdk.cli': [Errno 2] No such file or directory
   ```
   解决方案: 确保 CLI 模块正确实现并可通过 `-m` 参数调用

3. **超时错误**
   ```
   ❌ 命令执行超时
   ```
   解决方案: 检查命令是否陷入无限循环，或调整超时设置

### 获取帮助

如果遇到其他问题，请：
1. 检查项目根目录的文档
2. 查看相关的错误日志
3. 确认所有依赖都已正确安装 