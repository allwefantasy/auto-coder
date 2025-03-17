
# AutoCoder 参数大全

AutoCoder 是一个强大的代码自动生成工具,可以根据用户的需求自动生成相应的代码。本文档详细介绍了 AutoCoder 支持的各种可选参数,方便用户进行查阅和使用。

## 通用参数

- `--source_dir`: 项目源代码目录路径
- `--git_url`: 用于克隆源代码的 Git 仓库 URL
- `--target_file`: 生成的源代码的输出文件路径  
- `--query`: 用户查询或处理源代码的指令
- `--template`: 生成源代码使用的模板。默认为 'common'
- `--project_type`: 项目类型。可选值:py、ts、py-script、translate 或文件后缀名。默认为 'py'
- `--execute`: 是否执行生成的代码。默认为 False
- `--package_name`: 仅适用于 py-script 项目类型。脚本的包名。默认为空。
- `--script_path`: 仅适用于 py-script 项目类型。Python 脚本路径。默认为空。
- `--model`: 使用的模型名称。默认为空  
- `--model_max_length`: 模型生成代码的最大长度。默认为 2000。仅在指定模型时生效。
- `--model_max_input_length`: 模型的最大输入长度。默认为 6000。仅在指定模型时生效。
- `--vl_model`: 要使用的多模态模型的名称。默认为空
- `--sd_model`: 要使用的稳定扩散模型的名称。默认为空  
- `--emb_model`: 要使用的嵌入模型的名称。默认为空
- `--index_model`: 用于构建索引的模型名称。默认为空
- `--index_model_max_length`: 索引模型生成代码的最大长度。默认为 0,表示使用 `--model_max_length` 的值  
- `--index_model_max_input_length`: 索引模型的最大输入长度。默认为 0,表示使用 `--model_max_input_length` 的值
- `--index_model_anti_quota_limit`: 每次索引模型 API 请求后等待的秒数。默认为 0,表示使用 `--anti_quota_limit` 的值
- `--index_filter_level`: 索引过滤级别,0:仅过滤 query 中提到的文件名,1. 过滤 query 中提到的文件名以及可能会隐含会使用的文件 2. 从 0,1 中获得的文件,再寻找这些文件相关的文件。默认为 0。
- `--index_filter_workers`: 用于通过索引过滤文件的工作线程数。默认为 1。
- `--file`: YAML配置文件路径。默认为空。
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto'  
- `--anti_quota_limit`: 每次 API 请求后等待的秒数。默认为 1 秒  
- `--skip_build_index`: 是否跳过构建源代码索引。默认为 False
- `--print_request`: 是否打印发送到模型的请求。默认为 False
- `--py_packages`: 添加到上下文的 Python 包,仅适用于 py 项目类型。默认为空。
- `--human_as_model`: 是否使用人工作为模型。默认为 False
- `--urls`: 要爬取并提取文本的 URL,多个 URL 以逗号分隔。默认为空。
- `--urls_use_model`: 是否使用模型处理 urls 中的内容。默认为 False
- `--search_engine`: 要使用的搜索引擎。支持的引擎:bing、google。默认为空
- `--search_engine_token`: 搜索引擎 API 的令牌。默认为空  
- `--enable_rag_search`: 是否开启使用搜索的检索增强生成。默认为 False
- `--enable_rag_context`: 是否开启使用上下文的检索增强生成。默认为 False
- `--auto_merge`: 是否自动将生成的代码合并到现有文件中。默认为 False。
- `--image_file`: 要处理的图像文件路径。默认为空
- `--image_max_iter`: 图像转 html 的最大迭代次数。默认为 1  
- `--enable_multi_round_generate`: 是否开启多轮对话生成。默认为 False

## 子命令参数

### revert 

- `--file`: 要撤销更改的文件路径

撤销指定文件所做的更改。

### store

- `--source_dir`: 项目源代码目录路径
- `--ray_address`: 要连接的Ray集群的地址。默认为'auto'

一些统计信息,比如 token 使用等。

### index

- `--file`: YAML配置文件路径
- `--model`: 使用的模型名称。默认为空
- `--index_model`: 用于构建索引的模型名称。默认为空
- `--source_dir`: 项目源代码目录路径
- `--project_type`: 项目类型。可选值:py、ts、py-script、translate或文件后缀名。默认为'py' 
- `--ray_address`: 要连接的Ray集群的地址。默认为'auto'

构建源代码索引。

### index-query

- `--file`: YAML 配置文件路径
- `--model`: 使用的模型名称。默认为空
- `--index_model`: 用于构建索引的模型名称。默认为空
- `--source_dir`: 项目源代码目录路径
- `--query`: 用户查询或处理源代码的指令
- `--index_filter_level`: 索引过滤级别,0:仅过滤 query 中提到的文件名,1. 过滤 query 中提到的文件名以及可能会隐含会使用的文件 2. 从 0,1 中获得的文件,再寻找这些文件相关的文件。默认为 2。
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto'

根据索引查询相关文件。

### doc 

- `--urls`: 要爬取并提取文本的 URL,多个 URL 以逗号分隔。默认为空。
- `--model`: 使用的模型名称。默认为空
- `--target_file`: 生成的源代码的输出文件路径。默认为空。
- `--file`: YAML 配置文件路径。默认为空。
- `--source_dir`: 项目源代码目录路径
- `--human_as_model`: 是否使用人工作为模型。默认为 False
- `--urls_use_model`: 是否使用模型处理 urls 中的内容。默认为 False
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto'

对文档进行一些操作,诸如获取 html 的正文内容。

#### doc build

- `--source_dir`: 项目源代码目录路径。默认为空。
- `--model`: 使用的模型名称。默认为空
- `--emb_model`: 要使用的嵌入模型的名称。默认为空
- `--file`: YAML 配置文件路径。默认为空。
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto'
- `--required_exts`: doc 构建所需的文件扩展名。默认为空字符串

#### doc query

- `--query`: 用户查询或处理源代码的指令。默认为空。
- `--source_dir`: 项目源代码目录路径。默认为 '.'
- `--model`: 使用的模型名称。默认为空
- `--emb_model`: 要使用的嵌入模型的名称。默认为空
- `--file`: YAML 配置文件路径。默认为空。
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto'  
- `--execute`: 是否执行生成的代码。默认为 False

#### doc chat

- `--file`: YAML 配置文件路径。默认为空。  
- `--model`: 使用的模型名称。默认为空
- `--emb_model`: 要使用的嵌入模型的名称。默认为空
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto'
- `--source_dir`: 项目源代码目录路径。默认为 '.'

#### doc serve

- `--file`: YAML 配置文件路径。默认为空。
- `--model`: 使用的模型名称。默认为空  
- `--emb_model`: 要使用的嵌入模型的名称。默认为空
- `--ray_address`: 要连接的 Ray 集群的地址。默认为 'auto' 
- `--source_dir`: 项目源代码目录路径。默认为 '.'
- `--host`: 服务绑定的主机。默认为空。
- `--port`: 服务绑定的端口。默认为 8000。
- `--uvicorn_log_level`: Uvicorn 日志级别。默认为 'info'。
- `--allow_credentials`: 是否允许凭证。默认为 False。
- `--allowed_origins`: 允许的来源列表。默认为 ['*']。
- `--allowed_methods`: 允许的 HTTP 方法列表。默认为 ['*']。  
- `--allowed_headers`: 允许的 HTTP 头列表。默认为 ['*']。
- `--api_key`: API 密钥。默认为空。
- `--served_model_name`: 服务的模型名称。默认为空。  
- `--prompt_template`: 提示模板。默认为空。
- `--ssl_keyfile`: SSL 密钥文件路径。默认为空。
- `--ssl_certfile`: SSL 证书文件路径。默认为空。
- `--response_role`: 响应角色。默认为 'assistant'。

以上就是 AutoCoder 支持的各种可选参数的详细介绍。用户可以根据自己的需求选择合适的参数来使用 AutoCoder,从而提高代码生成的效率和质量。如有任何疑问,欢迎随时联系我们。