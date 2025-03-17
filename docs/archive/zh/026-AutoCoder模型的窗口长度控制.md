# 026-AutoCoder模型的窗口长度控制

不同的模型的窗口是不一样的，目前比较主流的是8k和32k,128k。 建议使用32k 起步。

不同的SaaS模型，对输入的控制也是不一样的，比如 QwenMax 的输入是控制在6000个字符，而不是token。这个是特别需要注意的。
此外，大部分模型都控制了请求频率，我们在使用 AutoCoder 的时候，这样就比较容易失败。

为了避免上述这些情况导致的失败，我们推荐用一些更加宽松的模型，比如 deepseek v2 以及 GPT 3.5 或者 Haiku 来做AutoCoder 的驱动和索引模型。

如果你无法使用上述模型，比如就只能使用 QwenMax,那么可以通过如下配置来避免失败：

```yml
# 当前模型的最大生成长度
model_max_length: 2000
# 当前模型的最大输入长度
model_max_input_length: 6000
# 当前模型每次请求后休息的时间，避免触发频率限制
model_anti_quota_limit: 1

# 功能如上，专门正对构建索引的配置
index_model_max_length: 2000
index_model_max_input_length: 6000
index_model_anti_quota_limit: 1
```

如果超出长度，AutoCoder 会自动进行切分，从而保证每次请求都不会超出长度限制，从而避免失败，但这也极大的影响了效率。

## 如果你使用 DeepSeekV2 来做索引和驱动

```yml
model: deepseek_chat
index_model: deepseek_chat

skip_build_index: false
index_filter_level: 1
index_model_max_input_length: 30000
index_filter_workers: 4
index_build_workers: 4
```

一个不错的配置。记得你在部署 deepseek 的时候，也要保证 并发度>4,否则容易出问题。

下面是一个示例部署：

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 30 \
--num_workers 1 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```

这里我们把并发设置为 30。

