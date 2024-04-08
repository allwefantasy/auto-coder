# 017-AutoCoder指定专有索引模型

> AutoCoder >= 0.1.27 特性

如果你的项目很大，里面有海量的代码，如果用比较大的模型，速度和成本确实比较高。所以我们将构建索引的功能单独了出来，允许
你单独指定一个模型来完成。

我们来看下面一个例子：

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
   将html转换成 reactjs+typescript+tailwind 实现    
```

在这个例子里，我们通过 `skip_build_index` 参数开启了索引，然后默认模型我们用 QwenMax, 但是这个模型速度比较慢，比较贵，所以 我又通过参数 `index_model` 来指定一个专门的索引模型。 同样的，对于索引，你可以指定单次请求的最大输入和输出，以及为了防止模型的限速，你可以设置每次请求 后的停顿时间。

这样你就可以使用一些私有的或者较便宜的模型来完成索引的构建。但是注意的是，很多模型能力实在太弱，构建索引需要该模型能够识别代码里面的包导入语句，变量，函数等，但是很多模型连这个都做不到。

为此，我们提供了一些校验命令，方便你快速的测试哪些模型可以达到合适的效果。

执行下面的命令可以构建索引：

```bash
auto-coder index --model kimi_chat --index_model sparkdesk_chat --project_type py --source_dir YOUR_PROJECT
```

此时项目会使用 `sparkdesk_chat` 模型来构建索引，构建完成后，你可以在项目的 .auto-coder/index.json 文件中看到索引的内容。

接着你可以使用索引来查找文件：

```bash
auto-coder index-query --model kimi_chat --index_model sparkdesk_chat --source_dir YOUR_PROJECT --query "添加一个新命令"
```

之后就可以看看查找是否准确。你可以将 model 和 index_model 设置为相同的值。

对于上面的命令，如果你想做更精细的控制，可以使用 `--file` 来指定 YAML 文件。
