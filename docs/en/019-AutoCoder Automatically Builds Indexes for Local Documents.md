# 019-AutoCoder Automatically Builds Indexes for Local Documents

> AutoCoder >= 0.1.36 Feature

First, please execute:

```bash
pip install -U byzerllm
pip install -U auto-coder
```

AutoCoder now supports building indexes for code. See:

1. [006-AutoCoder Starts Indexing, Reducing Context](006-AutoCoder%20Starts%20Indexing%2C%20Reducing%20Context.md)
2. [017-AutoCoder Specifies a Proprietary Index Model](017-AutoCoder%20Specifies%20a%20Proprietary%20Index%20Model.md)
3. [018-AutoCoder Experience Talk on Index Filtering](018-AutoCoder%20Experience%20Talk%20on%20Index%20Filtering.md)

For document usage, we currently require users to configure as follows:

1. urls: Here you can specify documents from local paths or online documents; multiple documents can be separated by commas.
2. search_engine/search_engine_token to enable automatic online document search

Today, we allow users to index local documents for use.

## Starting the Index Service

Remember how we started the model service? Similar to the following:

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat
```

By running the above command, we can obtain a qianwen_chat model.

Now, we can start an indexing service with the same command:

```bash
# export JAVA_HOME=/Users/allwefantasy/Library/Java/JavaVirtualMachines/openjdk-21/Contents/Home
byzerllm storage start
```

Note, your system needs to have JDK21 installed. If JDK21 is not your default SDK, you can temporarily export JAVA_HOME before starting the command. The system will automatically download the required files.

## Building an Index for Documents

Before building, you need to deploy two models: one is qianwen_chat, the other is qianwen_emb.

qianwen_chat:

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat
```

qianwen_emb:

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=text-embedding-v2 \
--model qianwen_emb
```

Now, you can build your documents:

```bash
auto-coder doc build --model qianwen_chat \
--emb_model qianwen_emb \
--source_dir your directory for storing documents
```

You can also put the above parameters in a YAML file:

```yaml
source_dir: /Users/allwefantasy/projects/deploy_models
target_file: /Users/allwefantasy/projects/auto-coder/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

emb_model: qianwen_emb

index_filter_level: 0

query: |   
   Please only provide the startup statement for qianwen_chat.   
```

Then run it like this:

```bash
auto-coder doc build --file actions/019_test_rag.yml 
```

## Usage

### For Use as a Q&A Assistant

```bash
auto-coder doc query --model qianwen_chat --emb_model qianwen_emb --source_dir . \
--query "Please provide the startup statement for qianwen_chat"
```
Or, write the query and parameters to a file:

```bash
auto-coder doc query --file actions/019_test_rag.yml 
```

Below is the output:

```
=============RESPONSE==================


2024-04-17 14:01:50.287 | INFO     | autocoder.utils.llm_client_interceptors:token_counter_interceptor:16 - Input tokens count: 0, Generated tokens count: 0
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat

=============CONTEXTS==================
/Users/allwefantasy/projects/deploy_models/run.txt
/Users/allwefantasy/projects/deploy_models/run.sh
```

This will inform you of the results and the files from which the results were derived.

### For Automating Code Execution

If it's code, you can also have it directly execute this code:

```bash
auto-coder doc query --model qianwen_chat --emb_model qianwen_emb \
--source_dir . \
--query "Please provide the startup statement for qianwen_chat" \
--execute
```

Below is the output:

```
=============RESPONSE==================


2024-04-17 13:22:33.788 | INFO     | autocoder.utils.llm_client_interceptors:token_counter_interceptor:16 - Input tokens count: 0, Generated tokens count: 0
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat

=============CONTEXTS==================
/Users/allwefantasy/projects/deploy_models/run.txt
/Users/allwefantasy/projects/deploy_models/run.sh


=============EXECUTE==================
2024-04-17 13:22:45.916 | INFO     | autocoder.utils.llm_client_interceptors:token_counter_interceptor:16 - Input tokens count: 1184, Generated tokens count: 136
steps=[ExecuteStep(code='byzerllm deploy --pretrained_model_type saas/qianwen --cpus_per_worker 0.001 --gpus_per_worker 0 --num_workers 2 --infer_params saas.api_key=${MODEL_QIANWEN_TOKEN} saas.model=qwen-max --model qianwen_chat', lang='shell', total_steps=1, current_step=1, cwd=None, env=None, timeout=None, ignore_error=False)]
Shell Command:
byzerllm deploy --pretrained_model_type saas/qianwen --cpus_per_worker 0.001 --gpus_per_worker 0 --num_workers 2 --infer_params saas.api_key=${MODEL_QIANWEN_TOKEN} saas.model=qwen-max --model qianwen_chat
Output:
Command Line Arguments:

--------------------------------------------------

command             : deploy

ray_address         : auto

num_workers         : 2

gpus_per_worker     : 0.0

cpus_per_worker     : 0.001

model_path          : 

pretrained_model_type: saas/qianwen

model               : qianwen_chat

infer_backend       : vllm

infer_params        : {'saas.api_key': '', 'saas.model': 'qwen-max'}

file                : None

--------------------------------------------------

The qianwen_chat model has already been deployed.
```

You can see it has correctly executed this code.

### For Providing Auxiliary Code Generation Information

generate.yml:

```yaml
source_dir: your project path
target_file: your project path/output.txt 

model: qianwen_chat

enable_rag_search: true
emb_model: qianwen_emb

index_filter_level: 0

execute: true
auto_merge: true
human_as_model: true

query: |   
   Please encapsulate the qianwen_chat startup code into a function start_qianwen_chat.
```

We control whether to enable Rag retrieval with the parameter `enable_rag_search` to provide some additional information to the large model for code generation.

Then execute:

```bash
auto-coder --file generate.yml
```