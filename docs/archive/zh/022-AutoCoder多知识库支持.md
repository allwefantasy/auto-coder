# 022-AutoCoder多知识库支持.md

在 [019-AutoCoder对本地文档自动构建索引](019-AutoCoder对本地文档自动构建索引.md) 中，我们提到了如何通过 AutoCoder 对本地文档进行索引构建。在实际工作中，我们可能会遇到多个知识库的情况，

这可能是因为：

1. 业务线不同，知识库不同。
2. 所有内容都放在一个知识库中，会导致查询精度下降。

这时我们可以通过 AutoCoder 的多知识库支持功能，将多个知识库的索引合并到一起，系统会自动
选择最匹配的知识库进行查询。

## 如何配置多知识库支持


默认 byzerllm 构建的知识库名字叫default. 

### 创建一个新的知识库

```bash
byzerllm storage collection --name llm --description "使用ByzerLLM框架来部署和管理多种模型，包括如何启动、停止及配置Ray服务和Byzer-LLM的存储模板。此外，还介绍了如何通过Byzer-LLM部署各种预训练模型到云服务，涵盖了从OpenAI到自定义模型的部署，以及如何配置和调用这些模型的详细过程。这些操作使用户能够根据需求灵活部署和测试多种大规模语言模型。"
```
其中description非常重要，因为这个描述会在使用时，让 AutoCoder 根据你的问题，参考该信息选择最匹配的知识库。

如果你后续觉得描述不好，你可以按相同的方式更新描述。

### 构建知识库

```bash
auto-coder doc build --source_dir /Users/allwefantasy/projects/doc_repo/deploy_models \
--model gpt3_5_chat \
--emb_model gpt_emb \
--collection llm
```

这个时候会将数据写入新的知识库llm中。

### 使用多知识库

```bash
auto-coder doc query --file ~/model.yml --query "如何启动 deepseek_chat" --collections llm,default
```
我们通过 `--collections` 参数指定了我们要查询的多个知识库，这样 AutoCoder 就会选择最匹配的知识库进行查询。

### 当前限制

1. chat/serve 模式下，只支持一个知识库。
2. query 模式下，目前只会自动选择一个知识库来查询，目前还不能跨知识库联合查询。


