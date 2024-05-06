# 023-Experience in Model Deployment in AutoCoder

We know that in order to integrate various models, we provide the `byzerllm` deployment tool.

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

## 1. `--pretrained_model_type`

The definition rules are as follows:

1. For SaaS models, this parameter is `saas/xxxxx`. If your SaaS model (or the model deployed by the company through other tools) is compatible with the openai protocol, you can use `saas/openai`, otherwise, you need to write according to the list in the official documentation. Refer here: https://github.com/allwefantasy/byzer-llm?tab=readme-ov-file#SaaS-Models

2. For private models, this parameter is determined by the `--infer_backend` parameter. If your model can be deployed using vllm/llama_cpp, then `--pretrained_model_type` is a fixed value `custom/auto`. If you deploy using transformers, then this parameter is the model name of transformers, the specific name can currently be referred to at https://github.com/allwefantasy/byzer-llm. Usually only multimodal and vector models need to use transformers for deployment.

## 2. `--infer_backend`

Currently supports four values: vllm/transformers/deepspeed/llama_cpp. Among them, deepspeed is not used much due to poor performance. It is recommended to use vllm/llama_cpp.

## 3. `--infer_params`

For SaaS models, all parameters start with `saas.`, which are basically compatible with OpenAI parameters. For example, `saas.api_key`, `saas.model`, `saas.base_url`, and so on.
For all private models, if using vllm for deployment, they all start with `backend.`. The specific parameters need to refer to the vllm documentation. For llama_cpp deployment, simply configure llama_cpp related parameters, and the specific parameters need to refer to the llama_cpp documentation.

Common vllm parameters:

1. backend.gpu_memory_utilization GPU memory utilization ratio, default 0.9
2. backend.max_model_len Maximum model length, will be automatically adjusted according to the model. However, if your GPU memory is not enough for the default model value, you need to adjust it yourself.
3. backend.enforce_eager Whether to enable eager mode (cuda graph, will consume additional memory to improve performance), default True
4. backend.trust_remote_code Sometimes you need to enable this parameter to load certain models. Default False

Common llama_cpp parameters:

1. n_gpu_layers Used to control the number of model layers loaded on the GPU. Default is 0, indicating not using the GPU. Set to -1 for maximum GPU usage, otherwise set to a reasonable value (you can start from a value like 100 and try)
2. verbose Whether to enable detailed logging. Default is True.

## 4. `--model_path`

`--model_path` is a parameter unique to private models, usually a directory containing model weight files, configuration files, etc.## 5. `--num_workers`

`--num_workers` specifies the number of deployment instances. Taking the backend vllm as an example, by default, one worker is one vllm instance that supports concurrent inference, so it is usually set to 1. If it is a SaaS model, one worker only supports one concurrency. You can set a reasonable number of workers according to your needs.

## 6. `--cpus_per_worker`

`--cpus_per_worker` specifies the number of CPU cores per deployment instance. For a SaaS model, this is usually a very small value, such as 0.001.

## 7. `--gpus_per_worker`

`--gpus_per_worker` specifies the number of GPU cores per deployment instance. For a SaaS model, this is usually 0.