# 大模型性能基准测试指南

Auto-coder 提供了一个强大的 benchmark 工具，可以帮助开发者评估和比较不同大语言模型（LLM）的性能。本文将详细介绍如何使用这个工具进行性能测试。

## 1. 基本用法

### 1.1 命令行使用

```bash
auto-coder.rag benchmark --model MODEL_NAME [--parallel PARALLEL] [--rounds ROUNDS] [--type CLIENT_TYPE] [--api_key API_KEY] [--base_url BASE_URL]
```

参数说明：
- `--model`: (必需) 要测试的模型名称，如 deepseek_chat
- `--parallel`: (可选) 并发请求数，默认 10
- `--rounds`: (可选) benchmark测试轮数，默认 1
- `--type`: (可选) 客户端类型，可选 byzerllm（默认）或 openai
- `--api_key`: (可选) 当使用 OpenAI 客户端时需要提供 API key
- `--base_url`: (可选) 自定义 OpenAI 客户端的基础 URL

### 1.2 使用示例

1. 测试 ByzerLLM 的 deepseek_chat 模型 (5轮，每轮20并发)：
```bash
auto-coder.rag benchmark --model deepseek_chat --parallel 20 --rounds 5
```

2. 测试 OpenAI 的 gpt-4 模型 (3轮，每轮10并发)：
```bash
auto-coder.rag benchmark --model gpt-4 --type openai --api_key YOUR_API_KEY --parallel 10 --rounds 3
```

## 2. 测试指标说明

benchmark 工具会输出以下性能指标：

- **Total Time**: 总测试时间
- **Average Response Time**: 平均响应时间
- **Median (P50)**: 中位数响应时间
- **P90**: 90% 请求的响应时间
- **P95**: 95% 请求的响应时间
- **P99**: 99% 请求的响应时间
- **Requests/Second**: 每秒处理的请求数

## 3. 测试原理

benchmark 工具的工作原理如下：

1. 初始化测试环境
2. 创建指定数量的并发请求
3. 每个请求发送相同的提示："Hello, how are you?"
4. 记录每个请求的响应时间
5. 计算并输出统计结果

## 4. 使用建议

1. **选择合适的并发数**：
   - 对于本地部署的模型，建议从 10 开始逐步增加
   - 对于 SaaS 模型，请参考服务商的并发限制

2. **测试环境准备**：
   - 确保网络连接稳定
   - 关闭其他可能影响测试结果的程序
   - 对于本地模型，确保有足够的计算资源

3. **结果分析**：
   - 关注 P95 和 P99 指标，它们反映了最差情况下的性能
   - 如果 Requests/Second 过低，可能是模型或硬件存在瓶颈
   - 对比不同模型的测试结果，选择最适合的模型

## 5. 高级用法

### 5.1 自定义测试提示

可以通过修改源码中的 `single_request` 函数来使用自定义提示：

```python
def single_request(llm):
    try:
        t1 = time.time()
        llm.chat_oai(conversations=[{
            "role": "user",
            "content": "你的自定义提示"
        }])
        t2 = time.time()
        return t2 - t1
```

### 5.2 测试不同模型配置

可以通过修改 `llm.setup_default_model_name` 来测试不同模型配置：

```python
llm.setup_default_model_name("deepseek_chat")
llm.setup_model_config("deepseek_chat", {"temperature": 0.7, "max_tokens": 100})
```

## 6. 注意事项

1. 测试 OpenAI 模型时，请确保 API key 有足够的配额
2. 对于本地模型，测试前请确保模型已正确部署
3. 测试结果可能受到网络、硬件等因素影响，建议多次测试取平均值
4. 高并发测试可能会对生产环境造成影响，建议在测试环境进行

## 7. 实际应用案例

### 7.1 模型选型

```python
# 测试不同模型的性能
models = ["deepseek_chat", "qwen_chat", "gpt-4"]
results = {}

for model in models:
    result = subprocess.run([
        "auto-coder.rag", "benchmark",
        "--model", model,
        "--parallel", "20"
    ], capture_output=True, text=True)
    results[model] = result.stdout

# 比较结果
for model, result in results.items():
    print(f"Model: {model}")
    print(result)
```

### 7.2 性能优化

```python
# 测试不同并发下的性能
parallel_levels = [10, 20, 50, 100]
results = {}

for parallel in parallel_levels:
    result = subprocess.run([
        "auto-coder.rag", "benchmark",
        "--model", "deepseek_chat",
        "--parallel", str(parallel)
    ], capture_output=True, text=True)
    results[parallel] = result.stdout

# 分析最佳并发数
for parallel, result in results.items():
    print(f"Parallel: {parallel}")
    print(result)
```

## 8. 总结

Auto-coder 的 benchmark 工具为开发者提供了一个简单而强大的性能测试方案。通过合理使用这个工具，开发者可以：

1. 评估不同模型的性能
2. 优化模型配置
3. 确定最佳并发数
4. 监控模型性能变化

建议定期运行 benchmark 测试，以确保模型始终处于最佳性能状态。对于更高级的测试需求，可以参考源码进行定制化开发。