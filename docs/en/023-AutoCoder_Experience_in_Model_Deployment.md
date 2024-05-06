# Experience in Model Deployment in AutoCoder

We know that in order to connect various models, we provide the `byzerllm` deployment tool.

A typical SaaS deployment script is as follows:

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat
```

A typical private model deployment is as follows:

```bash
byzerllm deploy --pretrained_model_type custom/auto \
--infer_backend vllm \
--model_path /home/winubuntu/models/openbuddy-zephyr-7b-v14.1 \
--cpus_per_worker 0.001 \
--gpus_per_worker 1 \
--num_workers 1 \
--infer_params backend.max_model_len=28000 \
--model zephyr_7b_chat
```

Now let's take a closer look at the parameters above.

## 0. `--model`

Assign a unique name to the current deployed instance, which is used to distinguish different models. You can think of a model as a template, and a model launched is an instance.
For example, for the same SaaS model, I can start multiple instances.

## 1. `--pretrained_model_type`

The definition is as follows:

1. If it is a SaaS model, this parameter is `saas/xxxxx`. If your SaaS model (or the model deployed by the company through other tools) is compatible with the openai protocol, then you can use `saas/openai`. Otherwise, you need to write according to the list in the official documentation. Refer here: https://github.com/allwefantasy/byzer-llm?tab=readme-ov-file#SaaS-Models

    Here is an example compatible with the openai protocol, such as the moonshot model:

    ```bash
    byzerllm deploy --pretrained_model_type saas/official_openai \
    --cpus_per_worker 0.001 \
    --gpus_per_worker 0 \
    --num_workers 2 \
    --infer_params saas.api_key=${MODEL_KIMI_TOKEN} saas.base_url="https://api.moonshot.cn/v1" saas.model=moonshot-v1-32k \
    --model kimi_chat
    ```

    Also, for example, if you deploy a model using ollama, you can do it like this:

    ```bash
    byzerllm deploy  --pretrained_model_type saas/openai \
    --cpus_per_worker 0.01 \
    --gpus_per_worker 0 \
    --num_workers 2 \
    --infer_params saas.api_key=token saas.model=llama3:70b-instruct-q4_0  saas.base_url="http://192.168.3.106:11434/v1/" \
    --model ollama_llama3_chat
    ```

2. If it is a private model, this parameter is determined by the `--infer_backend` parameter. If your model can be deployed using vllm/llama_cpp, then `--pretrained_model_type` is a fixed value `custom/auto`. If you deploy using transformers, then this parameter is the model name of transformers, the specific name can currently be referred to at https://github.com/allwefantasy/byzer-llm. Usually only multimodal, vector models need to be deployed using transformers, we have examples for most of them, if not, then you can also set it to custom/auto for testing.## 2. `--infer_backend`

Currently supports four values: vllm/transformers/deepspeed/llama_cpp. Among them, deepspeed is basically not used because the effect is not good. It is recommended to use vllm/llama_cpp.

## 3. `--infer_params`

For SaaS models, all parameters start with `saas.` and are basically compatible with OpenAI parameters. For example, `saas.api_key`, `saas.model`, `saas.base_url`, and so on.
For all private models, if deployed using vllm, they start with `backend.`. Specific parameters need to be referred to the vllm documentation. For llama_cpp deployment, configure llama_cpp-related parameters directly, and specific parameters need to be referred to the llama_cpp documentation.

Common vllm parameters:

1. backend.gpu_memory_utilization GPU memory utilization ratio, default 0.9
2. backend.max_model_len Maximum model length, will be automatically adjusted according to the model. However, if your memory is not enough for the model's default value, you need to adjust it yourself.
3. backend.enforce_eager Whether to enable eager mode (cuda graph, will occupy some additional memory for acceleration), default True
4. backend.trust_remote_code Sometimes you need to enable this parameter to load certain models. Default False

Common llama_cpp parameters:

1. n_gpu_layers Used to control the number of model GPU layers loaded. Default is 0, indicating not using GPU. To use GPU as much as possible, set it to -1, otherwise set a reasonable value (you can start with a value like 100).
2. verbose Whether to enable detailed logs. Default is True.

## 4. `--model_path`

`--model_path` is a parameter unique to private models, usually a directory containing model weight files, configuration files, etc.

## 5. `--num_workers`

`--num_workers` specifies the number of deployed instances. For backend vllm, by default, one worker is one vllm instance, supporting concurrent inference, so usually it can be set to 1. If it is an SaaS model, one worker only supports one concurrency, and you can set a reasonable number of workers according to your needs.

Byzerllm uses the LRU strategy to allocate worker requests.

You can use `byzerllm stat` to view the current status of the deployed model.

For example:

```bash
byzerllm stat --model gpt3_5_chat
```

Output:
```
Command Line Arguments:
--------------------------------------------------
command             : stat
ray_address         : auto
model               : gpt3_5_chat
file                : None
--------------------------------------------------
2024-05-06 14:48:17,206	INFO worker.py:1564 -- Connecting to existing Ray cluster at address: 127.0.0.1:6379...
2024-05-06 14:48:17,222	INFO worker.py:1740 -- Connected to Ray cluster. View the dashboard at 127.0.0.1:8265
{
    "total_workers": 3,
    "busy_workers": 0,
    "idle_workers": 3,
    "load_balance_strategy": "lru",
    "total_requests": [
        33,
        33,
        32
    ],
    "state": [
        1,
        1,
        1
    ],
    "worker_max_concurrency": 1,
    "workers_last_work_time": [
        "631.7133535240428s",
        "631.7022202090011s",
        "637.2349605050404s"     ]
}
```
Explanation of the output above:

1. total_workers: the actual number of deployed instances for the model gpt3_5_chat
2. busy_workers: the number of deployment instances currently busy
3. idle_workers: the number of deployment instances currently idle
4. load_balance_strategy: the load balancing strategy among instances at present
5. total_requests: the cumulative number of requests for each deployment instance
6. worker_max_concurrency: the maximum concurrency for each deployment instance
7. state: the current idle concurrency for each deployment instance (running concurrency = worker_max_concurrency - current value of state)
8. workers_last_work_time: the time since the last invocation of each deployment instance up to now


## 6. `--cpus_per_worker`

`--cpus_per_worker` specifies the number of CPU cores for each deployment instance. For SaaS models, this is usually a very small value, such as 0.001.


## 7. `--gpus_per_worker`

`--gpus_per_worker` specifies the number of GPU cores for each deployment instance. For SaaS models, this is usually 0.