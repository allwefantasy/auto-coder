# 000-AutoCoder_Prepare_Journey

This article will introduce how to quickly convert your project to auto-coder using SaaS API.

## Install auto-coder

```shell
conda create --name auto-coder python=3.10.11
conda activate auto-coder
pip install -U auto-coder
ray start --head
```

## Start the recommended model proxy

For the large language model (you need to apply for a token on the deepseek website), then execute the following command.

```shell
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 30 \
--num_workers 1 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```

For the vector model (you need to apply for a token on the qwen website), then execute the following command.

```shell
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=text-embedding-v2 \
--model qianwen_emb
```

## Initialize an existing project

Go to your project's root directory and execute the following command.

```shell
auto-coder init --source_dir .
```
The system will automatically generate `.auto-coder` and `actions` directories in the current directory.
In the actions directory, a `101_current_work.yaml` file will be generated, which you can use as a template.

## Start your journey

[002- Adding and Modifying Code with AutoCoder](./002-%20Adding%20and%20Modifying%20Code%20with%20AutoCoder.md)