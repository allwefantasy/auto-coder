# byzerllm 大模型编程快速指南


## 基于 Ray 的启动和管理模型

byzerllm 支持私有化模型或者SaaS模型的部署。

这里以 deepseek 官方API 为例：

```bash
easy-byzerllm deploy deepseek-chat --token xxxxx --alias deepseek_chat
```

或者跬基流动API:

```bash
easy-byzerllm deploy alibaba/Qwen1.5-110B-Chat --token xxxxx --alias qwen110b_chat
```

将上面的 API KEY 替换成你们自己的。

之后，你就可以在代码里使用  deepseek_chat 或者 qwen110b_chat  访问模型了。

可以使用

```
easy-byzerllm chat <模型别名> <query>
```

来和任何已经部署好的模型进行聊天。


### 硅基流动

```
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 1000 \
--infer_params saas.base_url="https://api.siliconflow.cn/v1" saas.api_key=${MODEL_silcon_flow_TOKEN}  saas.model=deepseek-ai/deepseek-v2-chat \
--model deepseek_chat
```

将 saas.model 替换成硅基流动提供的模型名字，然后将 saas.api_key 替换成你自己的key.

### gpt4o

byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 1000 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=gpt-4o \
--model gpt4o_chat

只需要填写 token, 其他的不需要调整。

### Azure gpt4o

byzerllm deploy --pretrained_model_type saas/azure_openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_type="azure" saas.azure_endpoint="https:/xxx.openai.azure.com/" saas.api_key="xxx" saas.api_version="2024-02-15-preview" saas.azure_deployment="gpt-4o-2024-05-13" saas.model=gpt-4o \
--model gpt4o_chat

主要修改的是 infer_params 里的参数。其他的不用调整。

值得注意的是：

1. saas.azure_endpoint 需要按需修改。
2. saas.azure_deployment="gpt-4o-2024-05-13"  是必须的，根据azure 提供的信息填写。

### Sonnet 3.5

byzerllm deploy --pretrained_model_type saas/claude \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 10 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_CLAUDE_TOEKN} saas.model=claude-3-5-sonnet-20240620 \
--model sonnet_3_5_chat

### AWS Sonnet 3.5

byzerllm deploy --pretrained_model_type saas/aws_bedrock \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 10 \
--num_workers 1 \
--infer_params saas.aws_access_key=xxxx saas.aws_secret_key=xxxx saas.region_name=xxxx saas.model_api_version=xxxx saas.model=xxxxx \
--model sonnet_3_5_chat

你可能还需要安装一个驱动：

pip install boto3 

主要修改的是 infer_params 里的参数。其他的不用调整。 

如果 saas.model_api_version 如果没有填写，并且 saas.model 是anthropic 开头的，那么该值默认为：bedrock-2023-05-31。 一般使用默认的即可。

下面是一个更完整的例子：

byzerllm deploy --pretrained_model_type saas/aws_bedrock --cpus_per_worker 0.001 --gpus_per_worker 0 --worker_concurrency 10 --num_workers 1 --infer_params saas.aws_access_key=xxx saas.aws_secret_key=xx saas.region_name=us-east-1 saas.model=anthropic.claude-3-5-sonnet-20240620-v1:0 --model sonnet_3_5_chat

### ollama或者oneapi 

byzerllm deploy  --pretrained_model_type saas/openai \
--cpus_per_worker 0.01 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=token saas.model=llama3:70b-instruct-q4_0  saas.base_url="http://192.168.3.106:11434/v1/" \
--model ollama_llama3_chat

### 兼容 OpenAI 接口
或者支持标准 OpenAI 的模型，比如 kimi 部署方式如下：

byzerllm deploy --pretrained_model_type saas/official_openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=${MODEL_KIMI_TOKEN} saas.base_url="https://api.moonshot.cn/v1" saas.model=moonshot-v1-32k \
--model kimi_chat

### 阿里云 Qwen系列

阿里云上的模型 qwen:

byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=qwen1.5-32b-chat \
--model qwen32b_chat

### 私有开源模型
或者部署一个私有/开源模型：

byzerllm deploy --pretrained_model_type custom/auto \
--infer_backend vllm \
--model_path /home/winubuntu/models/Qwen-1_8B-Chat \
--cpus_per_worker 0.001 \
--gpus_per_worker 1 \
--num_workers 1 \
--infer_params backend.max_model_len=28000 \
--model qwen_1_8b_chat

### emb模型：
比如Qwen系列：
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=text-embedding-v2 \
--model qianwen_emb

### GPT系列：

byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=text-embedding-3-small \
--model gpt_emb

### 私有 BGE 等：

!byzerllm deploy --pretrained_model_type custom/bge \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 10 \
--model_path /home/winubuntu/.auto-coder/storage/models/AI-ModelScope/bge-large-zh \
--infer_backend transformers \
--num_workers 1 \
--model emb

### 多模态部署

OpenAI 语音转文字模型：

byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.model=whisper-1 saas.api_key=${MODEL_OPENAI_TOKEN} \
--model voice2text

Open Whisper 语音转文字模型部署

byzerllm deploy --pretrained_model_type custom/whisper \
--infer_backend transformers \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--model_path <Whiper模型的地址>  \
--model voice2text
如果有GPU，记得 `--gpus_per_worker 0` 也设置为 1。CPU 还是比较慢的。

SenseVoice 语音转文字模型

byzerllm deploy --pretrained_model_type custom/sensevoice \
--infer_backend transformers \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--model_path <模型的地址>  \
--infer_params vad_model=fsmn-vad vad_kwargs.max_single_segment_time=30000
--model voice2text

注意： infer_params 是可选的。如果你通过  --gpus_per_workers 1  设置了 GPU ,那么 infer_params 参数可以追加一个  device=cuda:0 来使用 GPU。

### 火山引擎语言合成模型：

byzerllm deploy --pretrained_model_type saas/volcengine \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_VOLCANO_TTS_TOKEN} saas.app_id=6503259792 saas.model=volcano_tts \
--model volcano_tts

### 微软语言合成模型：

byzerllm deploy --pretrained_model_type saas/azure \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_AZURE_TTS_TOKEN} saas.service_region=eastus \
--model azure_tts

### OpenAI 语言合成模型：
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=tts-1 \
--model openai_tts

### OpenAi 图片生成模型：

byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=dall-e-3 \
--model openai_image_gen

### 千问VL模型

byzerllm deploy --pretrained_model_type saas/qianwen_vl \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=${MODEL_2_QIANWEN_TOKEN}  saas.model=qwen-vl-max \
--model qianwen_vl_max_chat

### 01万物VL模型：

byzerllm deploy  --pretrained_model_type saas/openai  \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=${MODEL_YI_TOKEN} saas.model=yi-vision saas.base_url=https://api.lingyiwanwu.com/v1 \
--model yi_vl_chat

### CPU部署私有开源模型

byzerllm deploy --pretrained_model_type custom/auto \
--infer_backend llama_cpp \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params verbose=true num_gpu_layers=0 \
--model_path /Users/allwefantasy/Downloads/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf \
--model llama_3_chat

现在我们来仔细看看上面的参数。

### 参数解析

--model

给当前部署的实例起一个名字，这个名字是唯一的，用于区分不同的模型。你可以理解为模型是一个模板，启动后的一个模型就是一个实例。比如同样一个 SaaS模型，我可以启动多个实例。每个实例里可以包含多个worker实例。

--pretrained_model_type

定义规则如下：

1. 如果是SaaS模型，这个参数是 saas/xxxxx。 如果你的 SaaS 模型（或者公司已经通过别的工具部署的模型），并且兼容 openai 协议，那么你可以使用 saas/openai，否则其他的就要根据官方文档的罗列来写。 参考这里： https://github.com/allwefantasy/byzer-llm?tab=readme-ov-file#SaaS-Models

    下面是一个兼容 openai 协议的例子,比如 moonshot 的模型：

byzerllm deploy --pretrained_model_type saas/official_openai \
    --cpus_per_worker 0.001 \
    --gpus_per_worker 0 \
    --num_workers 2 \
    --infer_params saas.api_key=${MODEL_KIMI_TOKEN} saas.base_url="https://api.moonshot.cn/v1" saas.model=moonshot-v1-32k \
    --model kimi_chat    

  还有比如如果你使用 ollama 部署的模型，就可以这样部署：

byzerllm deploy  --pretrained_model_type saas/openai \
    --cpus_per_worker 0.01 \
    --gpus_per_worker 0 \
    --num_workers 2 \
    --infer_params saas.api_key=token saas.model=llama3:70b-instruct-q4_0  saas.base_url="http://192.168.3.106:11434/v1/" \
    --model ollama_llama3_chat
 
2. 如果是私有模型，这个参数是是由 --infer_backend 参数来决定的。 如果你的模型可以使用 vllm/llama_cpp 部署，那么 --pretrained_model_type 是一个固定值 custom/auto。 如果你是用 transformers 部署，那么这个参数是 transformers 的模型名称, 具体名称目前也可以参考 https://github.com/allwefantasy/byzer-llm。 通常只有多模态，向量模型才需要使用 transformers 部署，我们大部分都有例子，如果没有的，那么也可以设置为 custom/auto 进行尝试。

--infer_backend

目前支持 vllm/transformers/deepspeed/llama_cpp 四个值。 其中 deepspeed 因为效果不好，基本不用。推荐vllm/llama_cpp 两个。

--infer_params

对于 SaaS 模型，所有的参数都以 saas. 开头，基本兼容 OpenAI 参数。 例如 saas.api_key, saas.model,saas.base_url 等等。
对于所有私有模型，如果使用 vllm 部署，则都以 backend. 开头。 具体的参数则需要参考 vllm 的文档。 对于llama_cpp 部署，则直接配置 llama_cpp相关的参数即可，具体的参数则需要参考 llama_cpp 的文档。

vllm 常见参数：

1. backend.gpu_memory_utilization GPU显存占用比例 默认0.9
2. backend.max_model_len 模型最大长度 会根据模型自动调整。 但是如果你的显存不够模型默认值，需要自己调整。
3. backend.enforce_eager 是否开启eager模式(cuda graph, 会额外占用一些显存来提数) 默认True
4. backend.trust_remote_code 有的时候加载某些模型需要开启这个参数。 默认False

llama_cpp 常见参数：

1. n_gpu_layers 用于控制模型GPU加载模型的层数。默认为 0,表示不使用GPU。尽可能使用GPU，则设置为 -1, 否则设置一个合理的值。（你可以比如从100这个值开始试）
2. verbose 是否开启详细日志。默认为True。

--model_path

--model_path 是私有模型独有的参数， 通常是一个目录，里面包含了模型的权重文件，配置文件等等。

--num_workers

--num_workers 是指定部署实例的数量。 以backend  vllm 为例，默认一个worker就是一个vllm实例，支持并发推理，所以通常可以设置为1。 如果是SaaS模型，则一个 worker 只支持一个并发，你可以根据你的需求设置合理数目的 worker 数量。

byzerllm 默认使用 LRU 策略来进行worker请求的分配。

--cpus_per_worker

--cpus_per_worker 是指定每个部署实例的CPU核数。 如果是SaaS模型通常是一个很小的值，比如0.001。


--gpus_per_worker

--gpus_per_worker 是指定每个部署实例的GPU核数。 如果是SaaS模型通常是0。

### 监控部署状态

你可以通过 byzerllm stat 来查看当前部署的模型的状态。

比如：

byzerllm stat --model gpt3_5_chat

输出：

Command Line Arguments:
--------------------------------------------------
command             : stat
ray_address         : auto
model               : gpt3_5_chat
file                : None
--------------------------------------------------
2024-05-06 14:48:17,206 INFO worker.py:1564 -- Connecting to existing Ray cluster at address: 127.0.0.1:6379...
2024-05-06 14:48:17,222 INFO worker.py:1740 -- Connected to Ray cluster. View the dashboard at 127.0.0.1:8265
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
        "637.2349605050404s"
    ]
}

解释下上面的输出：

1. total_workers: 模型gpt3_5_chat的实际部署的worker实例数量
2. busy_workers: 正在忙碌的worker实例数量
3. idle_workers: 当前空闲的worker实例数量
4. load_balance_strategy: 目前实例之间的负载均衡策略
5. total_requests: 每个worker实例的累计的请求数量
6. worker_max_concurrency: 每个worker实例的最大并发数
7. state: 每个worker实例当前空闲的并发数（正在运行的并发=worker_max_concurrency-当前state的值）
8. workers_last_work_time: 每个worker实例最后一次被调用的截止到现在的时间


## 纯客户端启动和管理模型

byzerllm 也支持纯客户端启动和管理模型。启动一个 llm 的实例方式为：

```python
llm = byzerllm.SimpleByzerLLM(default_model_name="deepseek_chat")
api_key_dir = os.path.expanduser("~/.auto-coder/keys")
api_key_file = os.path.join(api_key_dir, "api.deepseek.com")

if not os.path.exists(api_key_file):                
    raise Exception(f"API key file not found: {api_key_file}")

with open(api_key_file, "r") as f:
    api_key = f.read()

llm.deploy(
    model_path="",
    pretrained_model_type="saas/openai",
    udf_name="deepseek_chat",
    infer_params={
        "saas.base_url": "https://api.deepseek.com/v1",
        "saas.api_key": api_key,
        "saas.model": "deepseek-chat"
    }
)
```

之后就可以用 llm 实例和大模型沟通了。

## hello world

启动大模型后，我们就可以使用 byzerllm API和的大模型交流了:

```python
import byzerllm

llm = byzerllm.ByzerLLM.from_default_model(model="deepseek_chat")
# or use SimpleByzerLLM

@byzerllm.prompt(llm=llm)
def hello(q:str) ->str:
    '''
    你好, {{ q }}
    '''

s = hello("你是谁")    
print(s)

## 输出:
## '你好！我是一个人工智能助手，专门设计来回答问题、提供信息和帮助解决问题。如果你有任何疑问或需要帮助，请随时告诉我。'
```

恭喜，你和大模型成功打了招呼！

可以看到，我们通过 `@byzerllm.prompt` 装饰器，将一个方法转换成了一个大模型的调用，然后这个方法的主题是一段文本，文本中
使用了 jinja2 模板语法，来获得方法的参数。当正常调用该方法时，实际上就发起了和大模型的交互，并且返回了大模型的结果。

在 byzerllm 中，我们把这种方法称之为 prompt 函数。

## 查看发送给大模型的prompt

很多情况你可能需要调试，查看自己的 prompt 渲染后到底是什么样子的，这个时候你可以通过如下方式
获取渲染后的prompt:

```python
hello.prompt("你是谁")
## '你好, 你是谁'
```            

## 动态换一个模型

前面的 hello 方法在初始化的时候，我们使用了默认的模型 deepseek_chat，如果我们想换一个模型，可以这样做：

```python
hello.with_llm(llm).run("你是谁")
## '你好！我是一个人工智能助手，专门设计来回答问题、提供信息和帮助解决问题。如果你有任何疑问或需要帮助，请随时告诉我。'
```

通过 with_llm 你可以设置一个新的 llm 对象，然后调用 run 方法，就可以使用新的模型了。

## 超长文本生成

我们知道，大模型一次生成的长度其实是有限的，如果你想生成超长文本，你可能需手动的不断获得
生成结果，然后把他转化为输入，然后再次生成，这样的方式是比较麻烦的。

byzerllm 提供了更加易用的 API :

```python
import byzerllm
from byzerllm import ByzerLLM

llm = ByzerLLM.from_default_model("deepseek_chat")

@byzerllm.prompt()
def tell_story() -> str:
    """
    讲一个100字的故事。    
    """


s = (
    tell_story.with_llm(llm)
    .with_response_markers()
    .options({"llm_config": {"max_length": 10}})
    .run()
)
print(s)

## 从前，森林里住着一只聪明的小狐狸。一天，它发现了一块闪闪发光的宝石。小狐狸决定用这块宝石帮助森林里的动物们。它用宝石的光芒指引迷路的小鹿找到了回家的路，用宝石的温暖治愈了受伤的小鸟。从此，小狐狸成了森林里的英雄，动物们都感激它的善良和智慧。
```

实际核心部分就是这一行：

```python
tell_story.with_llm(llm)
    .with_response_markers()    
    .run()
```

我们只需要调用 `with_response_markers` 方法，系统就会自动的帮我们生成超长文本。
在上面的案例中，我们通过

```python
.options({"llm_config": {"max_length": 10}})
```

认为的限制大模型一次交互最多只能输出10个字符，但是系统依然自动完成了远超过10个字符的文本生成。

*** 尽管如此，我们还是推荐使用我们后面介绍的对话前缀续写的方式来生成超长文本。***

## 对象输出

前面我们的例子都是返回字符串，但是我们也可以返回对象，这样我们就可以更加灵活的处理返回结果。

```python
import pydantic 

class Story(pydantic.BaseModel):
    '''
    故事
    '''

    title: str = pydantic.Field(description="故事的标题")
    body: str = pydantic.Field(description="故事主体")

@byzerllm.prompt()
def tell_story()->Story:
    '''
    讲一个100字的故事。    
    '''

s = tell_story.with_llm(llm).run()
print(isinstance(s, Story))
print(s.title)

## True
## 勇敢的小鸟
```

可以看到，我们很轻松的将输出转化为格式化输出。

*** 尽管如此，我们推荐另外一个结构化输出方案 ***:

```python
import pydantic 

class Story(pydantic.BaseModel):    
    title: str
    body: str 

@byzerllm.prompt()
def tell_story()->str:
    '''
    讲一个100字的故事。
    
    返回符合以下格式的JSON:
    
    ```json
    {
        "title": "故事的标题",
        "body": "故事主体"
    }    
    ```    
    '''

s = tell_story.with_llm(llm).with_return_type(Story).run()
print(isinstance(s, Story))
print(s.title)

## True
## 勇敢的小鸟
```

这里我们显示的指定要返回的json格式，然后通过 with_return_type 指定对应的pydatic 类，自动来完成转换。

## 自定义字段抽取

前面的结构化输出，其实会消耗更多token,还有一种更加精准的结构化输出方式。
比如让大模型生成一个正则表达式，但实际上大模型很难准确只输出一个正则表达式，这个时候我们可以通过自定义抽取函数来获取我们想要的结果。


```python
from loguru import logger
import re

@byzerllm.prompt()
def generate_regex_pattern(desc: str) -> str:
    """
    根据下面的描述生成一个正则表达式，要符合python re.compile 库的要求。

    {{ desc }}

    最后生成的正则表达式要在<REGEX></REGEX>标签对里。
    """    

def extract_regex_pattern(regex_block: str) -> str:    
    pattern = re.search(r"<REGEX>(.*)</REGEX>", regex_block, re.DOTALL)
    if pattern is None:
        logger.warning("No regex pattern found in the generated block:\n {regex_block}")
        raise None
    return pattern.group(1)

pattern = "匹配一个邮箱地址"
v = generate_regex_pattern.with_llm(llm).with_extractor(extract_regex_pattern).run(desc=pattern)
print(v)
## ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
```

在上面的例子里，我们根据一句话生成一个正则表达式。我们通过 `with_extractor` 方法，传入了一个自定义的抽取函数，这个函数会在大模型生成结果后，对结果进行处理，然后返回我们想要的结果。

我们在 prompt 明确说了，生成的结果要放到 `<REGEX></REGEX>` 标签对里，然后我们通过 extract_regex_pattern 函数，从结果中提取出了我们想要的正则表达式。

## 在实例方法中使用大模型

```python
import byzerllm
data = {
    'name': 'Jane Doe',
    'task_count': 3,
    'tasks': [
        {'name': 'Submit report', 'due_date': '2024-03-10'},
        {'name': 'Finish project', 'due_date': '2024-03-15'},
        {'name': 'Reply to emails', 'due_date': '2024-03-08'}
    ]
}


class RAG():
    def __init__(self):        
        self.llm = byzerllm.ByzerLLM()
        self.llm.setup_template(model="deepseek_chat",template="auto")
        self.llm.setup_default_model_name("deepseek_chat")        
    
    @byzerllm.prompt()
    def generate_answer(self,name,task_count,tasks)->str:
        '''
        Hello {{ name }},

        This is a reminder that you have {{ task_count }} pending tasks:
        {% for task in tasks %}
        - Task: {{ task.name }} | Due: {{ task.due_date }}
        {% endfor %}

        Best regards,
        Your Reminder System
        '''        

t = RAG()

response = t.generate_answer.with_llm(llm).run(**data)
print(response)

## 输出:
## Hello Jane Doe,
##I hope this message finds you well. I wanted to remind you of your 3 pending tasks to ensure you stay on track:
## 1. **Submit report** - This task is due on **2024-03-10**. Please ensure that you allocat
```

这里我们给了个比较复杂的例子，但我们可以看到，给一个实例prompt方法和普通prompt 方法差异不大。
唯一的区别是如果你希望在定义的时候就指定大模型，使用一个lambda函数返回实例的 llm 对象即可。

```python
@byzerllm.prompt(lambda self:self.llm)
```

你也可以不返回，在调用的时候通过 `with_llm` 方法指定 llm 对象。

此外，这个例子也展示了如何通过jinja2模板语法，来处理复杂的结构化数据。

## 通过 Python 代码处理复杂入参

上面的一个例子中，我们通过 jinja2 模板语法，来处理复杂的结构化数据，但是有时候我们可能需要更加复杂的处理，这个时候我们可以通过 Python 代码来处理。

```python
import byzerllm

data = {
    'name': 'Jane Doe',
    'task_count': 3,
    'tasks': [
        {'name': 'Submit report', 'due_date': '2024-03-10'},
        {'name': 'Finish project', 'due_date': '2024-03-15'},
        {'name': 'Reply to emails', 'due_date': '2024-03-08'}
    ]
}


class RAG():
    def __init__(self):        
        self.llm = byzerllm.ByzerLLM.from_default_model(model="deepseek_chat")
    
    @byzerllm.prompt()
    def generate_answer(self,name,task_count,tasks)->str:
        '''
        Hello {{ name }},

        This is a reminder that you have {{ task_count }} pending tasks:
            
        {{ tasks }}

        Best regards,
        Your Reminder System
        '''
        
        tasks_str = "\n".join([f"- Task: {task['name']} | Due: { task['due_date'] }" for task in tasks])
        return {"tasks": tasks_str}

t = RAG()

response = t.generate_answer.with_llm(t.llm).run(**data)
print(response)

## Just a gentle nudge to keep you on track with your pending tasks. Here's a quick recap:....
```

在这个例子里，我们直接把 tasks 在方法体里进行处理，然后作为一个字符串返回，最够构建一个字典，字典的key为 tasks,然后
你就可以在 docstring 里使用 `{{ tasks }}` 来引用这个字符串。

这样对于很复杂的入参，就不用谢繁琐的 jinja2 模板语法了。

## 如何自动实现一个方法

比如我定义一个签名，但是我不想自己实现里面的逻辑，让大模型来实现。这个在 byzerllm 中叫 function impl。我们来看看怎么
实现:

```python
import pydantic
class Time(pydantic.BaseModel):
    time: str = pydantic.Field(...,description="时间，时间格式为 yyyy-MM-dd")


@llm.impl()
def calculate_current_time()->Time:
    '''
    计算当前时间
    '''
    pass 


calculate_current_time()
#output: Time(time='2024-06-14')
```

在这个例子里，我们定义了一个 calculate_current_time 方法，但是我们没有实现里面的逻辑，我们通过 `@llm.impl()` 装饰器，让大模型来实现这个方法。
为了避免每次都要“生成”这个方法，导致无法适用，我们提供了缓存，用户可以按如下方式打印速度：

```python
start = time.monotonic()
calculate_current_time()
print(f"first time cost: {time.monotonic()-start}")

start = time.monotonic()
calculate_current_time()
print(f"second time cost: {time.monotonic()-start}")

# output:
# first time cost: 6.067266260739416
# second time cost: 4.347506910562515e-05
```
可以看到，第一次执行花费了6s,第二次几乎是瞬间完成的，这是因为第一次执行的时候，我们实际上是在生成这个方法，第二次执行的时候，我们是执行已经生成好的代码，所以速度会非常快。你可以显示的调用 `llm.clear_impl_cache()` 清理掉函数缓存。

## Stream 模式

前面的例子都是一次性生成结果，但是有时候我们可能需要一个流式的输出，这个时候我们可能需要用底层一点的API来完成了：

```python
import byzerllm

llm = byzerllm.ByzerLLM.from_default_model(model="deepseek_chat")

v = llm.stream_chat_oai(model="deepseek_chat",conversations=[{
    "role":"user",
    "content":"你好，你是谁",
}],delta_mode=True)

for t,meta in v:
    print(t,flush=True)  

# 你好
# ！
# 我
# 是一个
# 人工智能
# 助手
# ，
# 旨在
# 提供
# 信息
# 、
# 解答
# 问题....
```
其中meta的结构如下：

```python
SingleOutputMeta(input_tokens_count=input_tokens_count,
                generated_tokens_count=generated_tokens_count,
                reasoning_content=reasoning_text,
                finish_reason=chunk.choices[0].finish_reason)
```

如果你不想要流式输出，但是想用底层一点的API，你可以使用 `llm.chat_oai` 方法：

```python
import byzerllm

llm = byzerllm.ByzerLLM.from_default_model(model="deepseek_chat")

v = llm.chat_oai(model="deepseek_chat",conversations=[{
    "role":"user",
    "content":"你好，你是谁",
}])

print(v[0].output)
## 你好！我是一个人工智能助手，旨在提供信息、解答问题和帮助用户解决问题。如果你有任何问题或需要帮助，请随时告诉我。
```

其中 v[9].meta 的结构如下：

```python
{
    "request_id": response.id,
    "input_tokens_count": input_tokens_count,
    "generated_tokens_count": generated_tokens_count,
    "time_cost": time_cost,
    "first_token_time": 0,
    "speed": float(generated_tokens_count) / time_cost,
    # Available options: stop, eos, length, tool_calls
    "finish_reason": response.choices[0].finish_reason,
    "reasoning_content": reasoning_text
}
```


## Function Calling 

byzerllm 可以不依赖模型自身就能提供 function calling 支持，我们来看个例子：


```python
from typing import List,Dict,Any,Annotated
import pydantic 
import datetime
from dateutil.relativedelta import relativedelta

def compute_date_range(count:Annotated[int,"时间跨度，数值类型"],
                       unit:Annotated[str,"时间单位，字符串类型",{"enum":["day","week","month","year"]}])->List[str]:
    '''
    计算日期范围

    Args:
        count: 时间跨度，数值类型
        unit: 时间单位，字符串类型，可选值为 day,week,month,year
    '''        
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    if unit == "day":
        return [(now - relativedelta(days=count)).strftime("%Y-%m-%d %H:%M:%S"),now_str]
    elif unit == "week":
        return [(now - relativedelta(weeks=count)).strftime("%Y-%m-%d %H:%M:%S"),now_str]
    elif unit == "month":
        return [(now - relativedelta(months=count)).strftime("%Y-%m-%d %H:%M:%S"),now_str]
    elif unit == "year":
        return [(now - relativedelta(years=count)).strftime("%Y-%m-%d %H:%M:%S"),now_str]
    return ["",""]

def compute_now()->str:
    '''
    计算当前时间
    '''
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
```

我们定义了两个方法，一个是计算日期范围，一个是计算当前时间。

现在我么可以来测试下，系统如何根据自然语言决定调用哪个方法：

```python
t = llm.chat_oai([{
    "content":'''计算当前时间''',
    "role":"user"    
}],tools=[compute_date_range,compute_now],execute_tool=True)

t[0].values

## output: ['2024-06-14 15:18:02']
```

我们可以看到，他正确的选择了 compute_now 方法。

接着我们再试一个：

```python
t = llm.chat_oai([{
    "content":'''最近三个月趋势''',
    "role":"user"    
}],tools=[compute_date_range,compute_now],execute_tool=True)

t[0].values

## output: [['2024-03-14 15:19:13', '2024-06-14 15:19:13']]
```

模型正确的选择了 compute_date_range 方法。

## 多模态

byerllm 也能很好的支持多模态的交互，而且统一了多模态大模型的接口，比如你可以用一样的方式使用 openai 或者 claude 的图片转文字能力， 或者一致的方式使用火山，azuer, openai的语音合成接口。

### 图生文

```python
import byzerllm
from byzerllm.types import ImagePath

vl_llm = byzerllm.ByzerLLM.from_default_model("gpt4o_mini_chat")


@byzerllm.prompt()
def what_in_image(image_path: ImagePath) -> str:
    """
    {{ image_path }}
    这个图片里有什么？
    """    


v = what_in_image.with_llm(vl_llm).run(
    ImagePath(value="/Users/allwefantasy/projects/byzer-llm/images/cat1.png")
)
v
## OUTPUT: 这张图片展示了多只可爱的猫咪，采用了艺术风格的绘画。猫咪们有不同的颜色和花纹，背景是浅棕色，上面还点缀着一些红色的花朵。整体画面给人一种温馨和谐的感觉
```

可以看到，我们只需要把 prompt 函数的图片地址入参使用 byzerllm.types.ImagePath里进行包装，就可以直接在 prompt 函数体里
带上图片。

或者你可以这样：

```python
import byzerllm

vl_llm = byzerllm.ByzerLLM.from_default_model("gpt4o_mini_chat")


@byzerllm.prompt()
def what_in_image(image_path: str) -> str:
    """
    {{ image }}
    这个图片里有什么？
    """
    return {"image": byzerllm.Image.load_image_from_path(image_path)}


v = what_in_image.with_llm(vl_llm).run(
    "/Users/allwefantasy/projects/byzer-llm/images/cat1.png"
)
v
```

通过 `image_path` 参数，然后通过 `byzerllm.Image.load_image_from_path` 方法，转化为一个图片对象 image，最后在 prompt 函数体里
使用 `{{ image }}` 引用这个图片对象。

另外我们也是可以支持配置多张图片的。

另外，我们也可以使用基础的 `llm.chat_oai` 方法来实现：

```python
import byzerllm
import json

vl_llm = byzerllm.ByzerLLM.from_default_model("gpt4o_mini_chat")
image = byzerllm.Image.load_image_from_path(
    "/Users/allwefantasy/projects/byzer-llm/images/cat1.png"
)
v = vl_llm.chat_oai(
    conversations=[
        {
            "role": "user",
            "content": json.dumps(
                [{"image": image, "text": "这个图片里有什么？"}], ensure_ascii=False
            ),
        }
    ]
)
v[0].output
```

还可以这么写：

```python
import byzerllm
import json

vl_llm = byzerllm.ByzerLLM.from_default_model("gpt4o_mini_chat")
image = byzerllm.Image.load_image_from_path(
    "/Users/allwefantasy/projects/byzer-llm/images/cat1.png"
)
v = vl_llm.chat_oai(
    conversations=[
        {
            "role": "user",
            "content": json.dumps(
                [
                    {
                        "type": "image_url",
                        "image_url": {"url": image, "detail": "high"},
                    },
                    {"text": "这个图片里有什么？", "type": "text"},
                ],
                ensure_ascii=False,
            ),
        }
    ]
)
v[0].output
```

### 语音合成

这里以 openai 的 tts 为例：

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=tts-1 \
--model openai_tts
```

此外，byzerllm 支持 azure,火山引擎等 tts 语音合成引擎。

接着你可以这么用：

```python
import byzerllm
import base64
import json

llm = byzerllm.ByzerLLM.from_default_model("openai_tts")


t = llm.chat_oai(conversations=[{
    "role":"user",
    "content": json.dumps({
        "input":"hello, open_tts",
        "voice": "alloy",
        "response_format": "mp3"
    },ensure_ascii=False)
}])

with open("voice.mp3","wb") as f:
    f.write(base64.b64decode(t[0].output))
```

tts 模型生成没有prompt函数可以用，你需要直接使用 chat_oai。


### 语音识别

这里以 openai 的 whisper-1 为例：

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.model=whisper-1 saas.api_key=${MODEL_OPENAI_TOKEN} \
--model speech_to_text
```

语音识别的使用方式和图生文类似，我们可以直接在 prompt 函数体里带上音频文件。

```python
import byzerllm
import json
import base64
from byzerllm.types import AudioPath

llm = byzerllm.ByzerLLM.from_default_model("speech_to_text")

audio_file = "/Users/allwefantasy/videos/output_audio.mp3"

@byzerllm.prompt(llm=llm)
def audio_to_text(audio_file: AudioPath):
    """
    {{ audio_file }}
    """

v = audio_to_text(AudioPath(value=audio_file))
json.loads(v)
```
输出的数据格式略微复杂：

```
{'text': 'In the last chapter, you and I started to step through the internal workings of a transformer. This is one of the key pieces of technology inside large language models, and a lot of other tools in the modern wave of AI.',
 'task': 'transcribe',
 'language': 'english',
 'duration': 10.0,
 'segments': [{'id': 0,
   'seek': 0,
   'start': 0.0,
   'end': 4.78000020980835,
   'text': ' In the last chapter, you and I started to step through the internal workings of a transformer.',
   'tokens': [50364,
    682,
    264,
    1036,
    7187,
    11,
    291,
    293,
    286,
    1409,
.....    
    31782,
    13,
    50586],
   'temperature': 0.0,
   'avg_logprob': -0.28872039914131165,
   'compression_ratio': 1.4220778942108154,
   'no_speech_prob': 0.016033057123422623},
  ....
  {'id': 2,
   'seek': 0,
   'start': 8.579999923706055,
   'end': 9.979999542236328,
   'text': ' and a lot of other tools in the modern wave of AI.',
   'tokens': [50759,
    293,
    257,
    688,
    295,
    661,
    3873,
    294,
    264,
    4363,
    5772,
    295,
    7318,
    13,
    50867],
   'temperature': 0.0,
   'avg_logprob': -0.28872039914131165,
   'compression_ratio': 1.4220778942108154,
   'no_speech_prob': 0.016033057123422623}],
 'words': [{'word': 'In', 'start': 0.0, 'end': 0.18000000715255737},
  {'word': 'the', 'start': 0.18000000715255737, 'end': 0.23999999463558197},
  {'word': 'last', 'start': 0.23999999463558197, 'end': 0.5400000214576721},
  {'word': 'chapter', 'start': 0.5400000214576721, 'end': 0.800000011920929},
  ....
  {'word': 'AI', 'start': 9.920000076293945, 'end': 9.979999542236328}]}
```

会输出每一句话以及每一个字所在的起始时间和截止时间。你可以根据需要来使用。


### 文生图

文生图和语音合成类似，首先要启动合适的模型,以openai 的 dall-e-3 为例：

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=dall-e-3 \
--model openai_image_gen
```

启动模型后，只需要记住几个模板参数即可使用，这里直接使用 chat_oai 方法来使用：

```python

import byzerllm
import json
import base64

llm = byzerllm.ByzerLLM.from_default_model("openai_image_gen")
t = llm.chat_oai(conversations=[{
    "role":"user",
    "content": json.dumps({
        "input":"a white siamese cat",
        "size": "1024x1024",
        "quality": "standard"
    },ensure_ascii=False)
}])

with open("output1.jpg","wb") as f:
    f.write(base64.b64decode(t[0].output))


import matplotlib.pyplot as plt

image_path = "output1.jpg"
image = plt.imread(image_path)

plt.imshow(image)
plt.axis('off')
plt.show()
```

## Prompt 函数的流式输出

byzerllm 底层支持流式输出，非 prompt 函数的用法是这样的：

```python
import byzerllm

llm = byzerllm.ByzerLLM.from_default_model("deepseek_chat")

v = llm.stream_chat_oai(conversations=[{
    "role":"user",
    "content":"讲一个100字的故事"
}])

for s  in v:
    print(s[0], end="")
```

如果你像用 prompt 函数，可以这么用：


```python
import byzerllm
import json
import base64
from typing import Generator

llm = byzerllm.ByzerLLM.from_default_model("deepseek_chat")

@byzerllm.prompt()
def tell_story() -> Generator[str, None, None]:
    '''
    给我讲一个一百多字的故事
    '''

v = tell_story.with_llm(llm).run()    
for i in v:
    print(i, end="")
```

可以看到，和普通的 prompt 函数的区别在于，返回值是一个生成器，然后你可以通过 for 循环来获取结果。

## 向量化模型

byzerllm 支持向量化模型,你可以这样启动一个本地的模型：

```bash
!byzerllm deploy --pretrained_model_type custom/bge \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 10 \
--model_path /home/winubuntu/.auto-coder/storage/models/AI-ModelScope/bge-large-zh \
--infer_backend transformers \
--num_workers 1 \
--model emb
```

注意两个参数:

1. --infer_backend transformers: 表示使用 transformers 作为推理后端。
2. --model_path: 表示模型的路径。

也可以启动一个 SaaS 的emb模型,比如 qwen 的 emb 模型：

```bash
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=text-embedding-v2 \
--model qianwen_emb
```

或者 openai 的 emb 模型：

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=text-embedding-3-small \
--model gpt_emb
```
SaaS 模型无需配置 `--infer_backend` 参数。

无论是本地模型还是 SaaS 模型，我们都可以这样使用：

```python
import byzerllm
llm = byzerllm.ByzerLLM.from_default_model("deepseek_chat")
llm.setup_default_emb_model_name("emb")
llm.emb_query("你好")
```

如果你配置 byzerllm 中的 Storage 使用，比如你这样启动了存储：

```bash
byzerllm storage start --enable_emb
```

那么需要这么使用：

```python
from byzerllm.apps.byzer_storage.simple_api import ByzerStorage, DataType, FieldOption,SortOption
storage = ByzerStorage("byzerai_store", "memory", "memory")
storage.emb("你好")
```

## Chat Prefix Completion

byzerllm 支持 chat prefix completion 功能，也就是对话前缀续写。该功能沿用 Chat Completion API，用户提供 assistant 开头的消息，来让模型补全其余的消息。
该功能可以达到两个效果：

1. 有效的引导大模型的回答。
2. 可以增加大模型的输出（continue） 功能。

具体使用方式：

```python
response = llm.chat_oai(
                        conversations=[
                            {"role":"user","content":"xxxxx"},
                            {"role":"assistant","content":"xxxxx"}
                        ],
                        llm_config={
                            "gen.response_prefix": True},
                    )
k = response[0].output
```

要开启该功能，需要确保两点：

1.  conversations 最后一条消息必须是 assistant
2.  llm_config 参数中添加配置： "gen.response_prefix": True 

通常，还可以配置 llm_config 中的参数 `gen.stop`（字符串数组），这样模型在输出的时候，遇到这些指定的字符就会停止输出，让你有机会控制大模型什么时候停止输出，
这样你可以再做一些处理后，通过上面的功能让大模型继续输出。

## 案例集锦

请对指定文件夹内的所有.py文件进行处理，判断是否存在不兼容 windows 文件编码读取的情况。请使用 prompt 函数来实现。

```python  
import os
from pathlib import Path
from autocoder.common.files import read_file
import byzerllm

# 初始化大模型
llm = byzerllm.ByzerLLM.from_default_model(model="deepseek_chat")

@byzerllm.prompt()
def detect_windows_encoding_issues(code: str) -> str:
    """
    分析以下Python代码是否存在读取文件时不兼容Windows的编码问题（要兼容uft8/gbk）：
    
    {{ code }}
    
    如果存在以上问题，返回如下json格式：

    ```json
    {
        "value": 是否存在问题，true 或者 false
    }
    ```
    """

from byzerllm.types import Bool
def check_directory(directory: str):
    """检查目录下所有.py文件的Windows编码兼容性"""
    issues = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                try:
                    print("processing file: ", file_path)
                    content = read_file(str(file_path))                    
                    result = detect_windows_encoding_issues.with_llm(llm).with_return_type(Bool).run(content)
                    if result.value:
                        print("found issue in file: ", file_path)
                        issues.append(str(file_path))
                except Exception as e:
                    print(f"Error reading {file_path}: {str(e)}")
    
    return issues

# 使用示例
directory_to_check = "xxxx"  # 修改为你要检查的目录
issues = check_directory(directory_to_check)

if issues:
    print("发现以下文件可能存在Windows编码问题：")
    for issue in issues:
        print(f"- {issue}")
else:
    print("未发现Windows编码问题")
``` 


## 一些辅助工具

当调用 prompt 函数返回字符串的时候，如果想从里面抽取代码，可以使用如下方式：

```python
from byzerllm.utils.client import code_utils
text_with_markdown = '''
```shell
ls -l
```
'''
code_blocks = code_utils.extract_code(text_with_markdown)
for code_block in code_blocks:
    if code_block[0] == "shell":
        print(code_block[1])
##output: ls -l        
```

TagExtractor 工具用于对任意 `<_tag_></_tag_>` 标签对的抽取，下面是一个使用示例：

```python
from byzerllm.apps.utils import TagExtractor

extractor = TagExtractor('''
大家好
<_image_>data:image/jpeg;base64,xxxxxx</_image_>
                         大家好
<_image_>data:image/jpeg;base64,xxxxxx2</_image_>
''')

v = extractor.extract()
print(v.content[0].content)
print(v.content[1].content)
```
输出为:

```
data:image/jpeg;base64,xxxxxx
data:image/jpeg;base64,xxxxxx2
```

我们成功的将 <_image_></_image_> 标签对里的内容抽取出来了。

在Python异步编程时，你还可以使用 `byzerllm.utils.langutil` 中的 asyncfy 或者 asyncfy_with_semaphore 将一个同步方法转化为异步方法。
下面是这两个方法的签名和说明：

```python
def asyncfy_with_semaphore(
    func, semaphore: Optional[anyio.Semaphore]=None, timeout: Optional[float] = None
):
    """Decorator that makes a function async, as well as running in a separate thread,
    with the concurrency controlled by the semaphore. If Semaphore is None, we do not
    enforce an upper bound on the number of concurrent calls (but it is still bound by
    the number of threads that anyio defines as an upper bound).

    Args:
        func (function): Function to make async. If the function is already async,
            this function will add semaphore and timeout control to it.
        semaphore (anyio.Semaphore or None): Semaphore to use for concurrency control.
            Concurrent calls to this function will be bounded by the semaphore.
        timeout (float or None): Timeout in seconds. If the function does not return
            within the timeout, a TimeoutError will be raised. If None, no timeout
            will be enforced. If the function is async, one can catch the CancelledError
            inside the function to handle the timeout.
    """

def asyncfy(func):
    """Decorator that makes a function async. Note that this does not actually make
    the function asynchroniously running in a separate thread, it just wraps it in
    an async function. If you want to actually run the function in a separate thread,
    consider using asyncfy_with_semaphore.

    Args:
        func (function): Function to make async
    """
```
示例用法：

```python
 async def async_get_meta(self):
        return await asyncfy_with_semaphore(self.get_meta)()

async def async_stream_chat(
            self,
            tokenizer,
            ins: str,
            his: List[Tuple[str, str]] = [],
            max_length: int = 4096,
            top_p: float = 0.7,
            temperature: float = 0.9,
            **kwargs
    ):
        return await asyncfy_with_semaphore(self.stream_chat)(tokenizer, ins, his, max_length, top_p, temperature, **kwargs)

## 还可以配合 lambda 函数使用,这样可以将一个同步方法转化为无参数的异步方法来调用，使用起来更加方便。
with io.BytesIO() as output:
    async with asyncfy_with_semaphore(
        lambda: self.client.with_streaming_response.audio.speech.create(
            model=self.model, voice=voice, input=ins, **kwargs
        )
    )() as response:
        for chunk in response.iter_bytes():
            output.write(chunk)
```


## 注意事项

1. prompt函数方法体返回只能是dict，实际的返回类型和方法签名可以不一样，但是方法体返回只能是dict。
2. 大部分情况prompt函数体为空，如果一定要有方法体，可以返回一个空字典。
3. 调用prompt方法的时候，如果在@byzerllm.prompt()里没有指定llm对象，那么需要在调用的时候通过with_llm方法指定llm对象。