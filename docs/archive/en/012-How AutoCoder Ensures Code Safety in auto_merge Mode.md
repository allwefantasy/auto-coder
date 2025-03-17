# 012-AutoCoder How To Ensures Code Security in auto_merge Mode

Code security actually consists of two parts. One part is to prevent code leakage, which can be resolved through [010-AutoCoder How to Use at the Company Level](./010-How%20to%20Use%20AutoCoder%20at%20the%20Company%20Level.md).

The other part is that if the auto_merge mode is enabled, due to the uncertainty of the large model, it is very likely to damage the user's existing code. For example, a user may forget to commit the code, run AutoCoder immediately, and enable auto_merge, which could easily overwrite the user's code.

Therefore, we need some measures to ensure the security of the code. Here, we encourage everyone to ensure that your code is managed by git when enabling the auto_merge mode. If it is a project managed by git, AutoCoder will ensure the security of the code through git:

1. Before modifying the code, we will perform a commit operation to ensure that the user's original code is saved, with a commit message similar to auto_coder_pre_文件名_文件md5.
2. After modification, we will perform a commit operation to ensure that after this commit, it is possible to roll back at any time. The corresponding commit message is "auto_coder_文件名_文件md5".

Let's take an example.

We randomly modify a file of AutoCoder, for example, git_utils.py, and add a method called: echo.
Note, here we have enabled the execute/auto_merge mode.
```yml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

skip_build_index: false
execute: true
auto_merge: true

query: |
   Add a method called: echo to git_utils.py, feel free to create.
```

Let's execute it:

```bash
auto-coder --file ./examples/003_test_revert.yml 
```        

The user should see two commit submissions in the log output:

```shell
2024-03-26 09:58:51.905 | WARNING  | autocoder.index.index:get_target_files_by_query:184 - Fail to find targed files for chunk 5. this may be caused by the model limit or the query is not suitable for the files.
2024-03-26 09:58:56.908 | INFO     | autocoder.index.index:build_index_and_filter_files:213 - Target File: /home/winubuntu/projects/ByzerRawCopilot/src/git_utils.py reason: As the user requested to add a method named 'echo' to this file, it is the target file.
2024-03-26 09:59:49.503 | INFO     | autocoder.dispacher.actions.action:process_content:238 - Auto merge the code...
2024-03-26 09:59:49.513 | INFO     | autocoder.common.git_utils:commit_changes:21 - Committed changes with message: auto_coder_pre_003_test_revert.yml_dca749b7ffddde8136a334a627221d3a
2024-03-26 09:59:49.513 | INFO     | autocoder.common.code_auto_merge:merge_code:59 - Upsert path: ./git_utils.py
2024-03-26 09:59:49.513 | INFO     | autocoder.common.code_auto_merge:merge_code:63 - Merged 1 files into the project.
2024-03-26 09:59:49.521 | INFO     | autocoder.common.git_utils:commit_changes:21 - Committed changes with message: auto_coder_003_test_revert.yml_dca749b7ffddde8136a334a627221d3a
```

The system automatically made two submissions. You can check through git:

```shell
commit 9813a6e5e52d92bb6151e0473f0abb7d4b8ddc71 (HEAD -> master)
Author: WilliamZhu <allwefantasy@gmail.com>
Date:   Tue Mar 26 09:59:49 2024 +0800

    auto_coder_003_test_revert.yml_dca749b7ffddde8136a334a627221d3a

commit 5aef905e14759aa0b513f493c5a879c0b921447f
Author: WilliamZhu <allwefantasy@gmail.com>
Date:   Tue Mar 26 09:59:49 2024 +0800

    auto_coder_pre_003_test_revert.yml_dca749b7ffddde8136a334a627221d3a
```

If you find any issues with the code, you can use auto-coder to roll back:

```shell
auto-coder revert --file ./examples/003_test_revert.yml
```

Or you can manually roll back through git commands.