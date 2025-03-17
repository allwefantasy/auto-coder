# 022-AutoCoder Multi-Knowledge Base Support.md

In [019-AutoCoder Automatic Indexing of Local Documents](019-AutoCoder Automatic Indexing of Local Documents.md), we discussed how to build an index of local documents using AutoCoder. In practical work, we may encounter situations where multiple knowledge bases are involved,

This may be because:

1. Different business lines have different knowledge bases.
2. Putting all content in one knowledge base can lead to a decrease in query accuracy.

In such cases, we can use AutoCoder's multi-knowledge base support feature to merge the indexes of multiple knowledge bases together, and the system will automatically select the most suitable knowledge base for querying.

## Configuring Multi-Knowledge Base Support

By default, the knowledge base built by byzerllm is named default.

### Creating a New Knowledge Base

```bash
byzerllm storage collection --name llm --description "Using the ByzerLLM framework to deploy and manage various models, including how to start, stop, and configure Ray services and Byzer-LLM storage templates. In addition, it also explains how to deploy various pre-trained models to cloud services through Byzer-LLM, covering the deployment from OpenAI to custom models, and the detailed process of configuring and calling these models. These operations allow users to flexibly deploy and test various large-scale language models according to their needs."
```
The description is very important because this description will help AutoCoder choose the most suitable knowledge base based on your question.

If you feel that the description is not good later on, you can update it in the same way.

### Building the Knowledge Base

```bash
auto-coder doc build --source_dir /Users/allwefantasy/projects/doc_repo/deploy_models \
--model gpt3_5_chat \
--emb_model gpt_emb \
--collection llm
```

At this point, the data will be written to the new knowledge base llm.

### Using Multiple Knowledge Bases

```bash
auto-coder doc query --file ~/model.yml --query "How to start deepseek_chat" --collections llm,default
```We specify the multiple knowledge bases we want to query through the `--collections` parameter, so AutoCoder will choose the most suitable knowledge base for the query.

### Current Limitations

1. In chat/serve mode, only one knowledge base is supported.
2. In query mode, currently only one knowledge base will be automatically selected for querying, and cross-knowledge base joint queries are not yet supported.