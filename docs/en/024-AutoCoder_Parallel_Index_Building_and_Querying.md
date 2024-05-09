# 024-AutoCoder Parallel Index Building and Querying
> Version Requirement:
> - auto-coder >= 0.1.52
## Which models are suitable for index building and querying?
Both deepseek and haiku are cost-effective models that can be used for index building.
For index querying, gpt-3.5-turbo can be used as it is fast and effective, making it suitable for index querying.

## Parallelism Setting

Normally, building an index using haiku in a Python file takes between 2-7 seconds, while using deepseek takes between 10-30 seconds.
If users are building the index for the first time, it may lead to a long wait time, so we can use parallelism to build the index.

```yaml
# Enable indexing
skip_build_index: false
# Level for index querying
index_filter_level: 1
# Parallelism setting for querying the index
index_filter_workers: 4

# Maximum input length for a single build, recommended to set a large value
index_model_max_input_length: 30000
# Parallelism setting for building the index
index_build_workers: 4
```

As shown above, we can set the `index_build_workers` to determine the parallelism for building the index, for example, setting it to 4 here.
However, setting this to 4 alone may not be enough, we also need to match the parallelism when deploying the model:

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 4 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```

Here, I deployed the deepseek model and set `--num_workers 4`, ensuring that the parallelism settings for building and querying the index are not blocked by byzerllm. Generally, we can set the value of num_workers slightly higher than index_build_workers to ensure that the index building process is not blocked.