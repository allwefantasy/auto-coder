# 018-AutoCoder Index Filtering Experience

> Features in AutoCoder >= 0.1.29

In fact, we have several articles talking about indexing:

1. [006-AutoCoder Enabling Indexing, Reducing Context](006-AutoCoder%20Enabling%20Indexing%2C%20Reducing%20Context.md)
2. [017-AutoCoder Specifying a Proprietary Index Model](017-AutoCoder%20Specifying%20a%20Proprietary%20Index%20Model.md)

Today, we'll primarily discuss two topics:

0. The principle of index filtering
1. How to control the number of files filtered out
2. Some tips to compensate for files that were not filtered in

## The Principle of Index Filtering

We will read all project source files (controlled by `project_type`) with a large model, then extract symbols from each file, and store the relationship between symbols and files in the index. This process is offline, so you can build the index with the `auto-coder index` command, or when you enable indexing by setting `skip_build_index: false`, the system will automatically build or incrementally update the index when you use AutoCoder.

## How to Control the Number of Files Filtered Out

Then, when you use AutoCoder, you can describe your needs with `query`, and AutoCoder will find the files that meet the conditions from the index, which includes three steps:

0. Find suitable files based on the file names mentioned in the query. This step is a relatively accurate matching process. For example, you can say, please refer to xxxx.py file, this file is likely to be included in the context.
1. Match files and symbols inside the files based on the semantic understanding of the query. This step is a relatively fuzzy matching process. For example, you can say, please refer to the xxxx function, this file is also likely to be included in the context, as well as implicitly deduced information, which will also be matched against files and symbols.
2. Based on the files found in steps 0 and 1, find the files that these files depend on, which might lead to a large number of files being introduced into the context.

We control the filtering behavior with the following parameter:

- index_filter_level: 0, 1, 2

This parameter can be set to 2 by default, 0 means only the first step is enabled, 1 means steps 0 and 1 are enabled, and 2 means all steps are enabled.

To verify the effect of this parameter, we can use the following configuration file:

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
   Add a new command
   
```

Note that the model used for file filtering based on the index will use the `model` parameter, not the `index_model` parameter. The `index_model` parameter is used for the model that builds the index.

Here we set `index_filter_level: 0`, meaning we will only filter files based on file names. Then we run:


```shell
auto-coder index-query -f actions/014_test_index_command.yml
```        

The output is as follows:


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