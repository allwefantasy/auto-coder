# 023-AutoCoder中模型部署经验谈

我们知道，为了对接各种模型，我们提供了 `byzerllm` 部署工具。

一个典型的SaaS部署脚本如下：

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat
```

一个典型的私有模型部署如下：

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

现在我们来仔细看看上面的参数。

## 1. `--pretrained_model_type`

定义规则如下：

1. 如果是SaaS模型，这个参数是 `saas/xxxxx`。 如果你的 SaaS 模型（或者公司已经通过别的工具部署的模型），并且兼容 openai 协议，那么你可以使用 `saas/openai`，否则其他的就要根据官方文档的罗列来写。 参考这里： https://github.com/allwefantasy/byzer-llm?tab=readme-ov-file#SaaS-Models
 
2. 如果是私有模型，这个参数是是由 `--infer_backend` 参数来决定的。 如果你的模型可以使用 vllm/llama_cpp 部署，那么 `--pretrained_model_type` 是一个固定值 `custom/auto`。 如果你是用 transformers 部署，那么这个参数是 transformers 的模型名称, 具体名称目前也可以参考 https://github.com/allwefantasy/byzer-llm。 通常只有多模态，向量模型才需要使用 transformers 部署，我们大部分都有例子，如果没有的，那么也可以设置为 custom/auto 进行尝试。


## 2. `--infer_backend`

目前支持 vllm/transformers/deepspeed/llama_cpp 四个值。 其中 deepspeed 因为效果不好，基本不用。推荐vllm/llama_cpp 两个。

## 3. `--infer_params`

对于 SaaS 模型，所有的参数都以 `saas.` 开头，基本兼容 OpenAI 参数。 例如 `saas.api_key`, `saas.model`,`saas.base_url` 等等。
对于所有私有模型，如果使用 vllm 部署，则都以 `backend.` 开头。 具体的参数则需要参考 vllm 的文档。 对于llama_cpp 部署，则直接配置 llama_cpp相关的参数即可，具体的参数则需要参考 llama_cpp 的文档。

vllm 常见参数：

1. backend.gpu_memory_utilization GPU显存占用比例 默认0.9
2. backend.max_model_len 模型最大长度 会根据模型自动调整。 但是如果你的显存不够模型默认值，需要自己调整。
3. backend.enforce_eager 是否开启eager模式(cuda graph, 会额外占用一些显存来提数) 默认True
4. backend.trust_remote_code 有的时候加载某些模型需要开启这个参数。 默认False

llama_cpp 常见参数：

1. n_gpu_layers 用于控制模型GPU加载模型的层数。默认为 0,表示不使用GPU。尽可能使用GPU，则设置为 -1, 否则设置一个合理的值。（你可以比如从100这个值开始试）
2. verbose 是否开启详细日志。默认为True。

## 4. `--model_path`

`--model_path` 是私有模型独有的参数， 通常是一个目录，里面包含了模型的权重文件，配置文件等等。

## 5. `--num_workers`

`--num_workers` 是指定部署实例的数量。 以backend  vllm 为例，默认一个worker就是一个vllm实例，支持并发推理，所以通常是1。 如果是SaaS模型，则一个 worker 只支持一个并发，你可以根据你的需求设置合理数目的 worker 数量。

## 6. `--cpus_per_worker`

`--cpus_per_worker` 是指定每个部署实例的CPU核数。 如果是SaaS模型通常是一个很小的值，比如0.001。


## 7. `--gpus_per_worker`

`--gpus_per_worker` 是指定每个部署实例的GPU核数。 如果是SaaS模型通常是0。

