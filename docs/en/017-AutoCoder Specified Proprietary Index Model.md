# 017-AutoCoder Specified Proprietary Index Model

> AutoCoder >= 0.1.27 Features

If your project is large with massive amounts of code, using a larger model indeed results in higher speed and cost. Therefore, we have separated the indexing functionality, allowing you to specify a model exclusively for this task.

Let's take a look at the following example:

```yml
source_dir: /Users/allwefantasy/projects/tt/
target_file: /Users/allwefantasy/projects/auto-coder/output.txt 
project_type: ts


model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5


index_model: sparkdesk_chat
index_model_max_length: 2000
index_model_max_input_length: 6000
index_model_anti_quota_limit: 1

skip_build_index: false
execute: true
auto_merge: true
human_as_model: true

query: |   
   Convert HTML to ReactJS+TypeScript+Tailwind implementation   
```

In this example, we enabled indexing through the `skip_build_index` parameter, then for the default model we used QwenMax, but since this model is slower and more expensive, I specified an index model through the `index_model` parameter. Similarly, for indexing, you can specify the maximum input and output for a single request, as well as set a pause time after each request to prevent model throttling.

This way, you can use some private or cheaper models for model building. However, it's important to note that many models are too weak; building an index requires the model to recognize package statements, variables, functions, etc., within the code, but many models are incapable of even this.

Execute the following command:

```bash
auto-coder index --model kimi_chat --index_model sparkdesk_chat --project_type py --source_dir YOUR_PROJECT
```

Now, the project will use the `sparkdesk_chat` model for index building, and after completion, you can see the content of the index in the project's .auto-coder/index.json file.

Then, you can use the index to search for files:

```bash
auto-coder index-query --model kimi_chat --index_model sparkdesk_chat --source_dir YOUR_PROJECT --query "add a new command"
```

After that, you can check whether the search is accurate. You can set both model and index_model to the same value.

For the above commands, if you want more fine-grained control, you can use the `--file` option to specify a YAML file.