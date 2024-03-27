# 014 - AutoCoder using Ollama

Ollama is an excellent model deployment tool. 
Byzer-LLM, however, supports not only model deployment capabilities similar to Ollama but can also be used for

1. Open-source or private model training, model tuning, etc.
2. Distributed
3. Also supports SaaS models
4. Supports more advanced designs that integrate large models with programming languages, such as Prompt functions/classes

However, if the user has already used Ollama for model deployment, we can still use byzer-llm to interface with Ollama, so that AutoCoder can use Ollama seamlessly.
Since ollama supports OpenAI protocol interfaces, we can deploy it as follows:

```shell
byzerllm deploy  --pretrained_model_type saas/official_openai \
--cpus_per_worker 0.01 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=xxxxx saas.model=llama2  saas.base_url="http://localhost:11434/v1/" \
--model ollama_llama2_chat
```

Here `ollama_llama2_chat` is a model name that you can define yourself, which will later be used in AutoCoder. The rest are some resource configurations. Since we are using an already deployed Ollama, setting gpus to 0 and cpus to a smaller number is sufficient. Also, set the concurrency number num_workers, which is set to 1 here because I am testing.

Finally, configure the Ollama address in `saas.base_url`.

After deployment, you can test it:

```shell
byzerllm query --model ollama_llama2_chat --query 你好
```

Output as follows:

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