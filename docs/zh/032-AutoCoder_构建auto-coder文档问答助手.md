# 032-AutoCoder_构建auto-coder文档问答助手

AutoCoder 现在文档慢慢开始多起来了，自己查找很多细节其实挺麻烦的。用户可以自己利用AutoCoder构建一个文档小助手，这样可以
方便自己使用AutoCoder。

我们其实已经在 [019-AutoCoder对本地文档自动构建索引](019-AutoCoder对本地文档自动构建索引.md)中介绍了如何构建索引。

## 启动Byzer Storge服务

```bash
byzerllm storage start
```

## 启动emb/chat模型

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 1 \
--worker_concurrency 10 \
--infer_params  saas.api_key=${MODEL_OPENAI_TOKEN} saas.model=text-embedding-3-small \
--model gpt_emb

byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--worker_concurrency 30 \
--num_workers 1 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```
这里你可以自己随意组合，我比较喜欢上面两个模型。

## 构建索引

克隆auto-coder，然后对文档构建索引：

```bash
git clone https://github.com/allwefantasy/auto-coder
cd auto-coder
auto-coder doc build --model deepseek_chat \
--emb_model gpt_emb \
--source_dir ./docs/zh \
--collection auto-coder \
--description "AutoCoder文档"
```

如果你文档有更新，那么再执行一次这条命令就可以了。

## 命令行查询

```bash
auto-coder doc query --model deepseek_chat --emb_model gpt_emb  --collection auto-coder \
--query "urls 参数怎么使用，有示例么？"
```

下面是输出内容：

```
=============RESPONSE==================


2024-05-19 22:06:09.241 | INFO     | autocoder.utils.llm_client_interceptors:token_counter_interceptor:16 - Input tokens count: 0, Generated tokens count: 0
 urls 参数用于配置文档的链接，可以是HTTP(S)链接、本地文件或目录。多个地址可以用逗号分隔。例如，如果你想让AutoCoder参考一个在线文档和一个本地文件，你可以这样配置：

```
urls: https://example.com/documentation, /path/to/local/file.txt
```

这样，AutoCoder将同时打开这两个文档供你参考。需要注意的是，urls的内容不会被索引，而是完整地显示在AutoCoder的窗口中，因此需要考虑文件大小以确保不会影响性能。

=============CONTEXTS==================
/Users/allwefantasy/projects/auto-coder/docs/zh/007-番外篇 AutoCoder里配置的model究竟用来干嘛.md
```

## 使用聊天软件查询

```bash
auto-coder doc serve --model deepseek_chat --emb_model gpt_emb  --collection auto-coder
```
会开启一个兼容 OpenAI 的API接口，默认端口8000,你可以在你的聊天软件里做下配置,然后就可以有一个 auto-coder 文档小助手了：

![](images/032-01.png)








