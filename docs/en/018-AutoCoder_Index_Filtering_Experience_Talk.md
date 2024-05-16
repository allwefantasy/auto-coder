# 018-AutoCoder Index Filtering Experience

> AutoCoder >= 0.1.29 Features

In fact, we have talked about indexing in several articles before:

1. [006-AutoCoder Open Index, Reduce Context](006-AutoCoder%20%E5%BC%80%E5%90%AF%E7%B4%A2%E5%BC%95%EF%BC%8C%E5%87%8F%E5%B0%91%E4%B8%8A%E4%B8%8B%E6%96%87.md)
2. [017-AutoCoder Specify Exclusive Index Model](017-AutoCoder%E6%8C%87%E5%AE%9A%E4%B8%93%E6%9C%89%E7%B4%A2%E5%BC%95%E6%A8%A1%E5%9E%8B.md)

Today we will mainly talk about two things:

0. The principle of index filtering
1. How to control the number of filtered files
2. What are some tips to make up for files that are not filtered in

## The Principle of Index Filtering

We will read all project source code files through a large model (controlled by project_type), extract symbols from each file, and then store the relationship between symbols and files in the index. This process is an offline process, so you can build the index through the `auto-coder index` command, or when you enable the index function by setting `skip_build_index: false`, the system will automatically build or incrementally update the index when you use AutoCoder.

## How to Control the Number of Filtered Files

Next, when you use AutoCoder, you can describe your requirements through `query`, and AutoCoder will find files that meet the conditions based on your query. This process includes three steps:

0. Find the appropriate file based on the file name mentioned in the query. This step is a relatively accurate matching process. For example, you can say, please refer to the xxxx.py file, and this file will likely be included in the context.
1. Match files and symbols within files based on the semantic understanding of the query. This step is a relatively fuzzy matching process. For example, you can say, please refer to the xxxx function, and this file will likely be included in the context as well, along with implicitly inferred information that also matches files and symbols.
2. Based on the files found in steps 0 and 1, find the files that these files depend on. This step may result in a large number of files being introduced into the context.

We control the filtering behavior with the following parameter:

- index_filter_level: 0, 1, 2

This parameter defaults to 2, where 0 means only the first step mentioned above is enabled, 1 means steps 0 and 1 are enabled, and 2 means all steps are enabled.

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

Note that the model used for file filtering based on the index will use the `model` parameter, not the `index_model` parameter. The `index_model` parameter is used to build the index model.

Here we have set `index_filter_level: 0`, which means we will only filter files based on the file name. We can verify this by using the following command:

```shell
auto-coder index-query  --file actions/014_test_index_command.yml 
```        

The output result will be as follows:

```     +-----------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| file_path                                                                         | reason                                                                                                                                                                                                                                 |
+===================================================================================+========================================================================================================================================================================================================================================+
| /Users/allwefantasy/projects/auto-coder/src/autocoder/auto_coder.py               | This file likely contains the main entry point or command handling logic for the 'auto-coder' project. Adding a new command would typically involve modifying this file.                                                               |
+-----------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-coder/src/autocoder/dispacher/actions/action.py | This file seems to define an 'Action' class or module, which might be used to implement individual commands within the project. If commands are implemented as actions, adding a new command may require creating a new subclass here. |      In the latest version, we allow users to confirm the filtered files again (yes, that ugly green selection box), removing some unnecessary files. Use Tab to move the cursor to OK and Cancel, then press Enter to confirm.

If you are annoyed by manually confirming the selected files every time, you can skip this confirmation process by using the parameter:

```yml
skip_confirm: true
```

If you believe that certain files should be selected but were not, you can choose Cancel, end the session with control + C, then modify the query again to mention the file. This way, the model will select the file.

## What are some tips to compensate for files that were not filtered in?

You can set the index_filter_level to 0 and actively mention some file names in the query to improve the filtering accuracy. Alternatively, setting the index_filter_level to 1 allows you to mention some functions or classes in the query, and the system can automatically recognize them, making your usage more natural.

Furthermore, if you know exactly which files need to be changed, you can:

1. Set index_filter_level to 0
2. Add the following statement at the end of the query: If you need to filter files, please only filter out the xxxx.xx file from the provided information.