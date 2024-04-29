import byzerllm

@byzerllm.prompt()
def init_command_template():
    '''
    ## Location of your project
    ## 你项目的路径
    source_dir: /Users/allwefantasy/projects/xxxx
    target_file: /Users/allwefantasy/projects/xxxx/output.txt

    ## The type of your project. py,ts or you can use the suffix e.g. .java .scala .go 
    ## If you use the suffix, you can combind multiple types with comma e.g. .java,.scala
    ## 你项目的类型，py,ts或者你可以使用后缀，例如.java .scala .go
    ## 如果你使用后缀，你可以使用逗号来组合多个类型，例如.java,.scala
    project_type: py

    ## The model you want to drive AutoCoder to run
    model: gpt3_5_chat


    ## Enable the index building which can help you find the related files by your query
    ## 启用索引构建，可以帮助您通过查询找到相关文件
    skip_build_index: false
    ## The model to build index for the project (Optional)
    index_model: haiku_chat

    ## the filter level to find the related files
    ## 0: only find the files with the file name
    ## 1: find the files with the file name and the symbols in the file
    ## 2. find the related files reffered by the files in 0 and 1
    ## 0 is recommended for the first time
    ## 用于查找相关文件的过滤级别
    ## 0: 仅查找文件名
    ## 1: 查找文件名和文件中的符号
    ## 2. 查找0和1中的文件引用的相关文件
    ## 第一次建议使用0
    index_filter_level: 0
    index_model_max_input_length: 30000

    ## enable RAG context
    ## 启用RAG上下文
    # enable_rag_context: true
    ##  The model to build index for the project
    ## 用于为项目构建索引的模型
    # emb_model: gpt_emb

    ## The model will generate the code for you
    ## 模型将为您生成代码
    execute: true

    ## If you want to generate multiple files, you can enable this option to generate the code in multiple rounds
    ## to avoid exceeding the maximum token limit of the model
    ## 如果您想生成多个文件，可以启用此选项，以便在多个回合中生成代码
    ## 以避免超过模型的最大令牌限制
    enable_multi_round_generate: false

    ## AutoCoder will merge the generated code into your project
    ## AutoCoder将合并生成的代码到您的项目中
    auto_merge: true

    ## AutoCoder will ask you to deliver the content to the Web Model,
    ## then paste the answer back to the terminal
    ## AutoCoder将要求您将内容传递给Web模型，然后将答案粘贴回终端
    human_as_model: true

    ## What you want the model to do
    ## 你想让模型做什么
    query: |  
    YOUR QUERY HERE   
  
    
    ## You can execute this file with the following command
    ## And check the output in the target file
    ## 您可以使用以下命令执行此文件
    ## 并在目标文件中检查输出
    ## auto-coder --file 101_current_work.yml
    '''
