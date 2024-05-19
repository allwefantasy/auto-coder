# 032-AutoCoder_Building auto-coder document Q&A assistant

The AutoCoder documentation is gradually becoming more extensive, and it can be quite cumbersome to search for many details on your own. Users can use AutoCoder to build a document assistant, making it easier to use AutoCoder.

We have actually introduced how to build an index in [019-AutoCoder_Automatic indexing of local documents](019-AutoCoder_Automatic indexing of local documents.md).

## Start Byzer Storage service

```bash
byzerllm storage start
```

## Start emb/chat model

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
You can freely combine the above two models here.

## Build index

Clone auto-coder and then build an index for the documents:

```bash
git clone https://github.com/allwefantasy/auto-coder
cd auto-coder
auto-coder doc build --model deepseek_chat \
--emb_model gpt_emb \
--source_dir ./docs/en \
--collection auto-coder \
--description "AutoCoder Documentation"
```

If your documents are updated, then simply execute this command again.

## Command line query

```bash
auto-coder doc query --model deepseek_chat --emb_model gpt_emb  --collection auto-coder \
--query "How to use the urls parameter, are there any examples?"
```

The output is as follows:

```
=============RESPONSE==================

2024-05-19 22:06:09.241 | INFO     | autocoder.utils.llm_client_interceptors:token_counter_interceptor:16 - Input tokens count: 0, Generated tokens count: 0
The urls parameter is used to configure the links of the document, which can be HTTP(S) links, local files, or directories. Multiple addresses can be separated by commas. For example, if you want AutoCoder to reference an online document and a local file, you can configure it like this:

```
urls: https://example.com/documentation, /path/to/local/file.txt
```

In this way, AutoCoder will open both documents for your reference. It is important to note that the content of urls will not be indexed but will be displayed in full in the AutoCoder window, so you need to consider the file size to ensure it does not affect performance.

=============CONTEXTS==================
/Users/allwefantasy/projects/auto-coder/docs/en/007-Extra Episode What is the model configured in AutoCoder for?.md
```

## Use chat software to query

```bash
auto-coder doc serve --model deepseek_chat --emb_model gpt_emb  --collection auto-coder
```It will start a compatible OpenAI API interface, default port is 8000, you can configure it in your chat software, and then you will have an auto-coder document assistant:

![](images/032-01.png)