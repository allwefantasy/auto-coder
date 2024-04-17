# 019-AutoCoder对本地文档自动构建索引

> AutoCoder >= 0.1.36 特性

AutoCoder已经支持对代码构建索引了，参考：

1. [006-AutoCoder 开启索引，减少上下文](006-AutoCoder%20%E5%BC%80%E5%90%AF%E7%B4%A2%E5%BC%95%EF%BC%8C%E5%87%8F%E5%B0%91%E4%B8%8A%E4%B8%8B%E6%96%87.md)
2. [017-AutoCoder指定专有索引模型](017-AutoCoder%E6%8C%87%E5%AE%9A%E4%B8%93%E6%9C%89%E7%B4%A2%E5%BC%95%E6%A8%A1%E5%9E%8B.md)
3. [018-AutoCoder 索引过滤经验谈](018-AutoCoder 索引过滤经验谈.md)

而对文档的使用，我们目前还需要用户通过如下配置来使用：

1. urls: 这里你可以指定本地路径的文档或者网络文档，多个文档可以用逗号分隔。
2. search_engine/search_engine_token 来开启自动到网络寻找文档

今天我们允许用户对本地文档进行索引来使用了。

## 启动索引服务

还记得我们是怎么启动模型服务的么？类似下面这种：

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen-max \
--model qianwen_chat
```


通过运行上面的命令，我们就能得到一个 qianwen_chat 模型。

现在我们可以用相同的命令启动一个索引服务：

```bash
# export JAVA_HOME=/Users/allwefantasy/Library/Java/JavaVirtualMachines/openjdk-21/Contents/Home
byzerllm storage start
```

注意，你系统需要装有 JDK21。如果JDK21不是你默认 SDK,可以在启动命令前临时export JAVA_HOME。
系统会自动下载需要的文件。

## 对文档进行索引构建

在构建之前，你需要先部署两个模型，一个是 qianwen_chat, 一个是qianwen_emb。 

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

现在，可以构建你的文档了：

```bash
auto-coder doc build --model qianwen_chat \
--emb_model qianwen_emb \
--source_dir 你存放文档的目录
```

你也可以把上面的参数放到一个 YAML 文件里去：

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
   请只给出 qianwen_chat  的启动语句。   
```

然后这样运行：

```bash
auto-coder doc build --file actions/019_test_rag.yml 
```

## 使用

### 用来做问答助手

```bash
auto-coder doc query --model qianwen_chat --emb_model qianwen_emb --source_dir . \
--query "请给出 qianwen_chat  的启动语句"
```
或者把问题和参数写到文件里：

```bash
auto-coder doc query --file actions/019_test_rag.yml 
```

下面是输出：

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
会告诉你结果，以及是根据那些文件得到的结果。

### 用来自动化执行代码

如果是代码，你也可以直接让他执行这个代码：

```bash
auto-coder doc query --model qianwen_chat --emb_model qianwen_emb \
--source_dir . \
--query "请给出 qianwen_chat  的启动语句" \
--execute
```

下面是输出：

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

模型 qianwen_chat 已经部署过了
```

可以看到他正确的运行了这个代码。

### 用来提供辅助信息生成代码

generate.yml:

```yaml
source_dir: 你的项目路径
target_file: 你的项目路径/output.txt 

model: qianwen_chat

enable_rag_search: true
emb_model: qianwen_emb

index_filter_level: 0

execute: true
auto_merge: true
human_as_model: true

query: |   
   请根据 qianwen_chat 的启动代码，封装一个函数 start_qianwen_chat。
```

我们通过参数 `enable_rag_search` 控制是否启用 Rag 检索来获取一些额外信息给到大模型来生成代码。

然后执行:

```bash
auto-coder --file generate.yml
```







