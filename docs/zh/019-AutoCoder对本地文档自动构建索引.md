# 019-AutoCoder对本地文档自动构建索引

> AutoCoder >= 0.1.36 特性

请先

```bash
pip install -U byzerllm
pip install -U auto-coder
```

AutoCoder已经支持对代码构建索引了，参考：

1. [006-AutoCoder 开启索引，减少上下文](006-AutoCoder%20%E5%BC%80%E5%90%AF%E7%B4%A2%E5%BC%95%EF%BC%8C%E5%87%8F%E5%B0%91%E4%B8%8A%E4%B8%8B%E6%96%87.md)
2. [017-AutoCoder指定专有索引模型](017-AutoCoder%E6%8C%87%E5%AE%9A%E4%B8%93%E6%9C%89%E7%B4%A2%E5%BC%95%E6%A8%A1%E5%9E%8B.md)
3. [018-AutoCoder 索引过滤经验谈](018-AutoCoder%20索引过滤经验谈.md)

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
系统会在启动期间下载一些库和文件，请确保网络畅通。

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

## 小实战

新建一个目录,然后把 auto-coder 的中文文档和 byzerllm 的命令行示例脚本拷贝进去：


```
ll /Users/allwefantasy/projects/doc_repo
total 0
drwxr-xr-x    5 allwefantasy  staff    160  4 17 15:19 ./
drwxr-xr-x  346 allwefantasy  staff  11072  4 17 15:04 ../
drwxr-xr-x    3 allwefantasy  staff     96  4 17 15:07 .auto-coder/
drwxr-xr-x   24 allwefantasy  staff    768  4 17 15:18 auto_coder_doc/
drwxr-xr-x    5 allwefantasy  staff    160  4 17 15:19 deploy_models/
```

新建一个  build.yml:

```yml
source_dir: /Users/allwefantasy/projects/doc_repo
model: qianwen_chat
emb_model: qianwen_emb
```

运行构建:

```bash
auto-coder doc build --file ./actions/build.yml
```

现在就可以就有个auto-coder助手了：

```bash
auto-coder doc query --file ./actions/build.yml --query "如何设置过滤级别"
```

输出：

```
=============RESPONSE==================


2024-04-17 15:40:12.547 | INFO     | autocoder.utils.llm_client_interceptors:token_counter_interceptor:16 - Input tokens count: 0, Generated tokens count: 0
如何设置过滤级别

在使用AutoCoder进行索引过滤时，可以通过调整`index_filter_level`参数来设定过滤级别的高低。具体设置方法如下：

1. **设置为0**：
   若要实现较为宽松的过滤条件，允许在查询中直接提及文件名以提升过滤准确性，将`index_filter_level`设置为0。这样，您可以在查询语句中明确指出希望包含的特定文件名，系统将依据这些指示进行文件筛选。

2. **设置为1**：
   若期望获得更为自然的使用体验，允许在查询中通过提及函数或类名来进行文件过滤，将`index_filter_level`设置为1。在这种级别下，AutoCoder能够自动识别您在查询中提到的函数或类，并据此有效地筛选相关文件。

综上所述，根据您的需求和工作场景，可通过将`index_filter_level`参数分别设置为0或1，来灵活调整AutoCoder的索引过滤级别，以达到期望的文件筛选效果。

=============CONTEXTS==================
/Users/allwefantasy/projects/doc_repo/auto_coder_doc/018-AutoCoder 索引过滤经验谈.md
```

其实最重要的是通过 CONTEXTS 快速定位相关文件。

再试一个：

```bash
auto-coder doc query --file ./actions/build.yml --query "如何对接ollama"
```

输出：

```
对接Ollama的步骤如下：

1. **模型部署**：
   使用Byzer-LLM进行模型部署，指定Ollama相关的参数。具体命令如下：

   ```shell
   byzerllm deploy  --pretrained_model_type saas/official_openai \
   --cpus_per_worker 0.01 \
   --gpus_per_worker 0 \
   --num_workers 1 \
   --infer_params saas.api_key=xxxxx saas.model=llama2  saas.base_url="http://localhost:11434/v1/" \
   --model ollama_llama2_chat
   ```

   参数说明：
   - `--pretrained_model_type saas/official_openai`: 指定使用Ollama模型，遵循OpenAI协议。
   - `--cpus_per_worker 0.01`: 分配给每个工作进程的CPU资源，由于使用已部署的Ollama，设为较小值即可。
   - `--gpus_per_worker 0`: 不分配GPU资源，因使用已部署的Ollama。
   - `--num_workers 1`: 设置并发数为1，此处为测试环境，可根据实际需求调整。
   - `--infer_params saas.api_key=xxxxx saas.model=llama2 saas.base_url="http://localhost:11434/v1/"`: 配置Ollama的相关参数：
     - `saas.api_key`: 提供您的Ollama API密钥。
     - `saas.model`: 指定使用的Ollama模型名称（例如：`llama2`）。
     - `saas.base_url`: 设置Ollama服务的URL地址。
   - `--model ollama_llama2_chat`: 自定义给部署模型命名，后续在AutoCoder中使用此名称。

2. **模型测试**：
   部署完成后，通过Byzer-LLM执行查询命令以测试对接的Ollama模型是否正常工作：

   ```shell
   byzerllm query --model ollama_llama2_chat --query 你好
   ```

   参数说明：
   - `--model ollama_llama2_chat`: 使用上一步部署时定义的模型名称。
   - `--query 你好`: 输入测试用的查询语句。

   如果对接成功，命令行将输出模型的响应，表明Ollama已成功与Byzer-LLM及AutoCoder对接。

综上所述，通过执行上述Byzer-LLM部署命令并进行模型测试，即可完成对Ollama的对接。后续在AutoCoder中直接使用模型名称`ollama_llama2_chat`即可无缝使用Ollama。

=============CONTEXTS==================
/Users/allwefantasy/projects/doc_repo/auto_coder_doc/命令行版Devin 来了: Auto-Coder.md
/Users/allwefantasy/projects/doc_repo/auto_coder_doc/014-AutoCoder使用Ollama.md
```






