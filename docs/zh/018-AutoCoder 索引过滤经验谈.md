# 018-AutoCoder 索引过滤经验谈

> AutoCoder >= 0.1.29 特性

其实我们前面有好几篇文章都在讲索引的事情：

1. [006-AutoCoder 开启索引，减少上下文](006-AutoCoder%20%E5%BC%80%E5%90%AF%E7%B4%A2%E5%BC%95%EF%BC%8C%E5%87%8F%E5%B0%91%E4%B8%8A%E4%B8%8B%E6%96%87.md)
2. [017-AutoCoder指定专有索引模型](017-AutoCoder%E6%8C%87%E5%AE%9A%E4%B8%93%E6%9C%89%E7%B4%A2%E5%BC%95%E6%A8%A1%E5%9E%8B.md)

今天我们会主要讲两个事情：

0. 索引过滤的原理
1. 如何控制过滤出来的文件数量
2. 有哪些小技巧来弥补没有被过滤进来的文件

## 索引过滤的原理

我们会通过大模型读取所有的项目源码文件（通过project_type来控制），然后对每个文件进行符号(symbols)的提取，然后将符号和文件的关系存储在索引中。这个过程是一个离线的过程，所以你可以通过 `auto-coder index` 命令来构建索引,或者当你通过 `skip_build_index: false` 来开启索引功能时，当你使用AutoCoder的时候系统会自动构建索引或者增量更新索引。

## 如何控制过滤出来的文件数量

接着，当你使用AutoCoder的时候，你可以通过 `query` 来描述你的需求，AutoCoder会根据你的query，从索引中找到符合条件的文件，具体包含了三个步骤：

0. 根据query里提到的文件名，来找到合适的文件。这一步是一个相对准确的匹配过程。比如你可以说，请参考 xxxx.py 文件，此时这个文件大概率会被包含在上下文中。
1. 根据对query的语义理解，对文件以及文件内部的符号(symbols)进行匹配。这一步是一个相对模糊的匹配过程。比如你可以说，请参考  xxxx 函数，此时这个文件大概率也会被包含在上下文中，当然还有隐式推倒出来的信息，也会对文件和符号进行匹配。
2. 根据0,1找到的文件，再找到这些文件依赖的文件，该步骤可能导致大量的文件被引入到上下文。

我们通过如下一个参数来控制过滤行为：

- index_filter_level: 0, 1, 2

该参数可以默认为2, 0表示值开启前面第一个步骤，1，表示卡开启0,1两个步骤，2表示开启所有步骤。

为了验证这个参数的作用，我们可以通过如下的配置文件：

```yml
source_dir: /Users/allwefantasy/projects/auto-coder
target_file: /Users/allwefantasy/projects/auto-coder/output.txt 
project_type: py

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

index_model: sparkdesk_chat
index_model_max_length: 2000
index_model_max_input_length: 10000
index_model_anti_quota_limit: 1
index_filter_level: 0

skip_build_index: false

query: |   
   添加一个新命令
   
```

注意，根据索引做文件过滤的模型会使用  model 参数，而不是 index_model 参数。 index_model 参数是用来构建索引的模型。

这里我们设置了 `index_filter_level: 0`，这意味着我们只会根据文件名来过滤文件，我们可以通过下面的命令来验证：


```shell
auto-coder index-query  --file actions/014_test_index_command.yml 
```        

输出结果如下：

```
+-----------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| file_path                                                                         | reason                                                                                                                                                                                                                                 |
+===================================================================================+========================================================================================================================================================================================================================================+
| /Users/allwefantasy/projects/auto-coder/src/autocoder/auto_coder.py               | This file likely contains the main entry point or command handling logic for the 'auto-coder' project. Adding a new command would typically involve modifying this file.                                                               |
+-----------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-coder/src/autocoder/dispacher/actions/action.py | This file seems to define an 'Action' class or module, which might be used to implement individual commands within the project. If commands are implemented as actions, adding a new command may require creating a new subclass here. |
+-----------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-coder/src/autocoder/index/for_command.py        | The file name and location suggest it may contain code related to handling commands, possibly providing functionality or infrastructure for implementing new commands in the project.                                                  |
+-----------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
```

## 有哪些小技巧来弥补没有被过滤进来的文件

可以将 index_filter_level 设置为 0, 然后主动在 query 中提到一些文件名，这样可以提高过滤的准确性。
亦或者将 index_filter_level 设置为 1, 这样你可以在 query 中提到一些函数或者类，系统也能自动识别，你用起来也会更自然一些。

此外，如果你明确知道要改的文件，你可以这么做：

1. index_filter_level设置为0
2. 在query 最后一行中添加如下语句： 请从提供的信息中只过滤出xxxx.xx文件
