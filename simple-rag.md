# auto-coder RAG 使用指南

auto-coder RAG (Retrieval-Augmented Generation) 是一个强大的工具，可以帮助您快速搭建基于文档的问答系统。本指南将介绍如何使用 auto-coder RAG 来启动服务并进行交互。

## 1. 启动 deepseek_chat 模型

首先，我们需要启动 deepseek_chat 模型。请使用以下命令：

```bash
byzerllm deploy deepseek-chat --token YOUR_API_KEY --alias deepseek_chat
```

请将 `YOUR_API_KEY` 替换为您的实际 API 密钥。

## 2. 启动 auto-coder RAG 服务

启动 deepseek_chat 模型后，我们可以使用以下命令来启动 auto-coder RAG 服务：

```bash
auto-coder doc serve --doc_dir /Users/allwefantasy/projects/llm_friendly_packages/github.com/allwefantasy --model deepseek_chat --index_filter_workers 5
```

以下是命令中使用的主要参数及其说明：

| 参数 | 描述 |
|------|------|
| `--doc_dir` | 指定文档目录路径 |
| `--model` | 指定使用的语言模型 |
| `--index_filter_workers` | 设置索引过滤工作线程数 |

## 3. 其他可选参数

auto-coder RAG 服务还支持许多其他参数，以下是一些常用的可选参数：

| 参数 | 描述 | 默认值 |
|------|------|--------|
| `--host` | 指定服务器主机地址 | 空（默认绑定所有接口） |
| `--port` | 指定服务器端口 | 8000 |
| `--uvicorn_log_level` | 设置 uvicorn 日志级别 | "info" |
| `--allow_credentials` | 是否允许凭证 | False |
| `--allowed_origins` | 允许的源列表 | ["*"] |
| `--allowed_methods` | 允许的 HTTP 方法列表 | ["*"] |
| `--allowed_headers` | 允许的 HTTP 头列表 | ["*"] |
| `--api_key` | 设置 API 密钥 | 空 |
| `--served_model_name` | 指定服务模型名称 | 空 |
| `--prompt_template` | 指定提示模板 | 空 |
| `--ssl_keyfile` | SSL 密钥文件路径 | 空 |
| `--ssl_certfile` | SSL 证书文件路径 | 空 |
| `--response_role` | 设置响应角色 | "assistant" |
| `--index_filter_file_num` | 设置索引过滤文件数量 | 3 |
| `--required_exts` | 指定所需文件扩展名 | 空 |

## 4. 服务交互

启动服务后，您可以通过 HTTP 请求与 auto-coder RAG 进行交互。服务将基于您提供的文档目录内容来回答问题。

## 注意事项

1. 确保您有足够的权限访问指定的文档目录。
2. 根据您的需求和系统资源调整 `index_filter_workers` 和 `index_filter_file_num` 参数。
3. 如果需要安全访问，请配置 SSL 证书和 API 密钥。

通过使用 auto-coder RAG，您可以快速构建一个基于您自己文档的智能问答系统。如果遇到任何问题或需要进一步的帮助，请查阅官方文档或联系支持团队。