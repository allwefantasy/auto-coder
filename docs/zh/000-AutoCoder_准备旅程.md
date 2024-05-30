# 000-AutoCoder_准备旅程

本篇内容会介绍使用 SaaS API 快速为你的已有项目设置auto-coder。

## 安装 auto-coder

```shell
conda create --name auto-coder python=3.10.11
conda activate auto-coder
pip install -U auto-coder
ray start --head
```

## 启动推荐的模型代理

大语言模型(你需要去deepseek官网申请token),然后执行下面的命令。

> 注意要替换 ${MODEL_DEEPSEEK_TOKEN} 和 ${MODEL_QIANWEN_TOKEN} 为你的实际token。

```shell
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 30 \
--num_workers 1 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```

向量模型(可选，你需要去qwen官网申请token，如果麻烦，可以跳过先),然后执行下面的命令。

```shell
byzerllm deploy --pretrained_model_type saas/qianwen \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 2 \
--infer_params saas.api_key=${MODEL_QIANWEN_TOKEN}  saas.model=text-embedding-v2 \
--model qianwen_emb
```

## 初始化已有项目

进入你的项目根目录，执行下面的命令。

```shell
auto-coder init --source_dir .
```
系统会自动在当前目录下生成 `.auto-coder`,`actions` 两个目录。
在 actions 目录下会生成一个 `101_current_work.yaml` 文件，你可以以这个作为模板。

记得在 actions/base/base.yml 或者你独立的yaml文件中修改你的 project_type，支持：

1. py
2. ts
3. 任何文件后缀名组合，使用逗号分隔，比如：.java,.scala

## 开始你的旅程

[002- 用 AutoCoder 添加和修改代码](./002-%20%E7%94%A8%20AutoCoder%20%E6%B7%BB%E5%8A%A0%E5%92%8C%E4%BF%AE%E6%94%B9%E4%BB%A3%E7%A0%81.md)

## 给自己构建一个本地 auto-coder 小助手

这一步依赖前面启动的向量模型。

启动知识库：

```shell
byzerllm storage start
```

导入 auto-coder 文档：

```shell
git clone https://github.com/allwefantasy/auto-coder
cd auto-coder 
auto-coder doc build --model deepseek_chat --emb_model qianwen_emb --source_dir ./docs/zh --collection auto-coder --description "AutoCoder文档"
```

大概等个几分钟，完工。

现在可以和小助手聊天了：

```shell
auto-coder doc query --model deepseek_chat --emb_model qianwen_emb --query "如何开启搜索引擎" --collection auto-coder
```

你也可以启动一个服务，方便使用一些聊天软件：

```shell
auto-coder doc serve --model deepseek_chat --emb_model qianwen_emb  --collection auto-coder
```

下面是一些效果：

![](../images/000-01.png)
![](../images/000-02.png)

以 NextChat 软件为例，配置如下：

![](../images/000-03.png)

密码随意填写。


