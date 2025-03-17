# AutoCoder Parameter Guide

AutoCoder is a powerful code auto-generation tool that can automatically generate corresponding code based on user requirements. This document provides a detailed introduction to the various optional parameters supported by AutoCoder for users to refer to and use.

## General Parameters

- `--source_dir`: Path to the project source code directory
- `--git_url`: URL of the git repository to clone the source code from
- `--target_file`: The file path to write the generated source code to
- `--query`: The user query or instruction to handle the source code
- `--template`: The template to use for generating the source code. Default is 'common'
- `--project_type`: The type of the project. Options: py, ts, py-script, translate, or file suffix. Default is 'py'
- `--execute`: Whether to execute the generated code. Default is False
- `--package_name`: Only works for py-script project type. The package name of the script. Default is empty.
- `--script_path`: Only works for py-script project type. The path to the Python script. Default is empty.
- `--model`: The name of the model to use. Default is empty
- `--model_max_length`: The maximum length of the generated code by the model. Default is 2000. This only works when model is specified.
- `--model_max_input_length`: The maximum length of the input to the model. Default is 6000. This only works when model is specified.
- `--vl_model`: The name of the multi-modal model to use. Default is empty
- `--sd_model`: The name of the stable diffusion model to use. Default is empty
- `--emb_model`: The name of the embedding model to use. Default is empty
- `--index_model`: The name of the model used to build index. Default is empty
- `--index_model_max_length`: The maximum length of the generated code by the index model. Default is 0, which means using the value of `--model_max_length`
- `--index_model_max_input_length`: The maximum length of the input to the index model. Default is 0, which means using the value of `--model_max_input_length`
- `--index_model_anti_quota_limit`: Time to wait in seconds after each API request for the index model. Default is 0, which means using the value of `--anti_quota_limit`  
- `--index_filter_level`: Index filter level, 0: only filter the file names mentioned in query, 1. filter the file names mentioned in query and possibly implicitly used files 2. files obtained from 0,1 and then find files related to these files. Default is 0.
- `--index_filter_workers`: Number of workers to use for filtering files by index. Default is 1.
- `--file`: Path to the YAML configuration file. Default is empty.
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'
- `--anti_quota_limit`: Time to wait in seconds after each API request. Default is 1s
- `--skip_build_index`: Whether to skip building the source code index. Default is False   
- `--print_request`: Whether to print the request sent to the model. Default is False
- `--py_packages`: The Python packages added to context, only works for py project type. Default is empty.
- `--human_as_model`: Use human as model or not. Default is False
- `--urls`: The urls to crawl and extract text from, separated by comma. Default is empty.
- `--urls_use_model`: Whether to use model to process content in urls. Default is False
- `--search_engine`: The search engine to use. Supported engines: bing, google. Default is empty
- `--search_engine_token`: The token for the search engine API. Default is empty
- `--enable_rag_search`: Whether to enable retrieval augmented generation using search. Default is False
- `--enable_rag_context`: Whether to enable retrieval augmented generation using context. Default is False
- `--auto_merge`: Whether to automatically merge the generated code into the existing file. Default is False.
- `--image_file`: The path of the image file to process. Default is empty
- `--image_max_iter`: The maximum number of iterations for image to html. Default is 1
- `--enable_multi_round_generate`: Whether to enable multi-round conversation for generation. Default is False

## Subcommand Parameters

### revert

- `--file`: Path to the file to revert changes

Revert the changes made by the specified file.

### store

- `--source_dir`: Path to the project source code directory
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'

Some statistics, such as token usage, etc.

### index

- `--file`: Path to the YAML configuration file
- `--model`: The name of the model to use. Default is empty
- `--index_model`: The name of the model used to build index. Default is empty
- `--source_dir`: Path to the project source code directory
- `--project_type`: The type of the project. Options: py, ts, py-script, translate, or file suffix. Default is 'py'
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'

Build the source code index.

### index-query

- `--file`: Path to the YAML configuration file
- `--model`: The name of the model to use. Default is empty
- `--index_model`: The name of the model used to build index. Default is empty
- `--source_dir`: Path to the project source code directory  
- `--query`: The user query or instruction to handle the source code
- `--index_filter_level`: Index filter level, 0: only filter the file names mentioned in query, 1. filter the file names mentioned in query and possibly implicitly used files 2. files obtained from 0,1 and then find files related to these files. Default is 2.
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'

Query related files based on the index.

### doc

- `--urls`: The urls to crawl and extract text from, separated by comma. Default is empty.
- `--model`: The name of the model to use. Default is empty
- `--target_file`: The file path to write the generated source code to. Default is empty.
- `--file`: Path to the YAML configuration file. Default is empty.
- `--source_dir`: Path to the project source code directory
- `--human_as_model`: Use human as model or not. Default is False
- `--urls_use_model`: Whether to use model to process content in urls. Default is False
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'

Some operation on doc, e.g. extract text from html.

#### doc build

- `--source_dir`: Path to the project source code directory. Default is empty.
- `--model`: The name of the model to use. Default is empty
- `--emb_model`: The name of the embedding model to use. Default is empty
- `--file`: Path to the YAML configuration file. Default is empty.
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'
- `--required_exts`: The required file extensions for doc build. Default is empty string

#### doc query

- `--query`: The user query or instruction to handle the source code. Default is empty.
- `--source_dir`: Path to the project source code directory. Default is '.'
- `--model`: The name of the model to use. Default is empty
- `--emb_model`: The name of the embedding model to use. Default is empty
- `--file`: Path to the YAML configuration file. Default is empty.
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'
- `--execute`: Whether to execute the generated code. Default is False

#### doc chat

- `--file`: Path to the YAML configuration file. Default is empty.
- `--model`: The name of the model to use. Default is empty
- `--emb_model`: The name of the embedding model to use. Default is empty
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'
- `--source_dir`: Path to the project source code directory. Default is '.'

#### doc serve

- `--file`: Path to the YAML configuration file. Default is empty.
- `--model`: The name of the model to use. Default is empty
- `--emb_model`: The name of the embedding model to use. Default is empty
- `--ray_address`: The address of the Ray cluster to connect to. Default is 'auto'
- `--source_dir`: Path to the project source code directory. Default is '.'
- `--host`: The host to bind the server to. Default is empty.
- `--port`: The port to bind the server to. Default is 8000.
- `--uvicorn_log_level`: Uvicorn log level. Default is 'info'.
- `--allow_credentials`: Whether to allow credentials. Default is False.
- `--allowed_origins`: List of allowed origins. Default is ['*'].
- `--allowed_methods`: List of allowed HTTP methods. Default is ['*'].
- `--allowed_headers`: List of allowed HTTP headers. Default is ['*'].
- `--api_key`: API key. Default is empty.
- `--served_model_name`: The name of the served model. Default is empty.
- `--prompt_template`: Prompt template. Default is empty.
- `--ssl_keyfile`: Path to the SSL key file. Default is empty.
- `--ssl_certfile`: Path to the SSL certificate file. Default is empty.
- `--response_role`: Response role. Default is 'assistant'.

The above is a detailed introduction to the various optional parameters supported by AutoCoder. Users can choose appropriate parameters according to their needs to use AutoCoder, thus improving the efficiency and quality of code generation. If you have any questions, please feel free to contact us.