# 014 - AutoCoder 使用 Ollama

Ollama 是一个很优秀的模型部署工具。 Byzer-LLM 则不仅仅支持类似 Ollama 的模型部署能力，还包括如下功能特性：

1. 开源或者私有模型训练、模型调参等
2. 训练和部署都支持分布式
3. 同时支持Saas模型
4. 支持诸如Prompt函数/类等将大模型和编程语言融合的一些高阶特性

不过如果用户已经使用 Ollama 进行了模型的部署,我们依然可以使用 byzer-llm 对接Ollama, 这样 AutoCoder就可以无缝使用 Ollama了。 因为 ollama 支持 OpenAI 协议的接口，所以我们可以使用如下方式进行部署：

```shell
byzerllm deploy  --pretrained_model_type saas/official_openai \
--cpus_per_worker 0.01 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=xxxxx saas.model=llama2  saas.base_url="http://localhost:11434/v1/" \
--model ollama_llama_chat
```

这里的 `ollama_llama2_chat` 是一个模型的名字，可以自己定义，后续在 AutoCoder 中使用这个名字即可, 其他的则是一些资源方面的配置，因为
我们用的是已经部署好的Ollama,所以 gpus设置为0, cpus 则设置一个较小的数值即可，并且设置下并发数num_workers，这里因为我是测试，所以设置为1。

最后在 `saas.base_url` 配置下 Ollama 的地址。

部署完成后可以测试下：

```shell
byzerllm query --model ollama_llama2_chat --query 你好
```

输出如下：

```
Command Line Arguments:
--------------------------------------------------
command             : query
ray_address         : auto
model               : ollama_llama2_chat
query               : 你好
template            : auto
file                : None
--------------------------------------------------
2024-03-27 16:34:22,040	INFO worker.py:1540 -- Connecting to existing Ray cluster at address: 192.168.3.123:6379...
2024-03-27 16:34:22,043	INFO worker.py:1715 -- Connected to Ray cluster. View the dashboard at 192.168.3.123:8265

Hello! 😊 How are you today? Is there anything you'd like to chat about or ask? I'm here to help with any questions you may have.
```


