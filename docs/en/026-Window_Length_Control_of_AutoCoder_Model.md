# 026-Control of Window Length of AutoCoder Model

The window size of different models varies, with the most popular being 8k, 32k, and 128k. It is recommended to start with 32k.

Different SaaS models also have different input controls. For example, the input for QwenMax is limited to 6000 characters, not tokens. This is something to pay special attention to.
Additionally, most models have restrictions on request frequency, which can easily lead to failures when using AutoCoder.

To avoid failures caused by the above situations, we recommend using more lenient models such as deepseek v2, GPT 3.5, or Haiku for driving and indexing AutoCoder.

If you are unable to use the above models and can only use QwenMax, you can avoid failures by configuring as follows:

```yml
# Maximum generation length of the current model
model_max_length: 2000
# Maximum input length of the current model
model_max_input_length: 6000
# Time to rest after each request of the current model to avoid triggering frequency limits
model_anti_quota_limit: 1

# Similar settings specifically for building indexes
index_model_max_length: 2000
index_model_max_input_length: 6000
index_model_anti_quota_limit: 1
```

If the length exceeds the limit, AutoCoder will automatically split the content to ensure that each request does not exceed the length limit, thus avoiding failures, but this greatly affects efficiency.

## If you use DeepSeekV2 for indexing and driving

```yml
model: deepseek_chat
index_model: deepseek_chat

skip_build_index: false
index_filter_level: 1
index_model_max_input_length: 30000
index_filter_workers: 4
index_build_workers: 4
```

A good configuration. Remember to ensure concurrency > 4 when deploying deepseek, otherwise problems may occur.

Here is an example deployment:

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 30 \
--num_workers 1 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```

Here we set the concurrency to 30.