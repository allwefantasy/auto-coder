# 012-AutoCoder如何保障auto_merge模式下的代码安全

代码安全实际有两部分，一部分是代码不能被泄露，这个可以通过 [010-AutoCoder 如何在公司级别使用](./010-AutoCoder%20%E5%A6%82%E4%BD%95%E5%9C%A8%E5%85%AC%E5%8F%B8%E7%BA%A7%E5%88%AB%E4%BD%BF%E7%94%A8.md)
来解决。

另一部分是如果开启了 auto_merge 模式，因为模型大模型的不确定性，很有可能破坏用户已有代码。比如用户可能忘了提交代码，马上又运行 AutoCoder ，并且开启了 auto_merge，很可能就覆盖掉了用户的代码。

所以我们需要一些措施来保障代码的安全，这里我们鼓励大家在开启 auto_merge 模式的时候，务必保证你的代码被 git 管控。
如果是一个被git 管控的项目，那么 AutoCoder 会通过 git 来保证代码的安全：

1. 在修改代码之前，我们会执行一次 commit 操作，确保用户原有的代码被保存，message消息是 pre-AutoCoder文件名。
2. 在修改之后，我们会执行一次 commit 操作，确保留下这个commit后，可以随时进行回滚，对应的commit message消息是 “AutoCoder文件名”。

我们来举个例子。

我们随意修改 AutoCoder 的一个文件，比如 git_utils.py ，我们在这个文件中新增一个方法叫：echo。
注意，这里我们开启了 execute/auto_merge 模式。
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
   在 git_utils.py 中新增一个方法叫：echo,可以随意发挥。
```

我们执行下:

```bash
auto-coder --file ./examples/003_test_revert.yml 
```        

用户看日志输出，应该看到两次 commit 提交：

```
try to build index for /home/winubuntu/projects/ByzerRawCopilot/src/autocoder/dispacher/actions/copilot.py md5: 19aa36056c1a9eea6da98baf12501446
try to build index for /home/winubuntu/projects/ByzerRawCopilot/src/autocoder/tsproject/__init__.py md5: 513677056b4c3120025f0c69c56df604
2024-03-26 09:20:26.249 | INFO     | autocoder.dispacher.actions.action:process_content:238 - Auto merge the code...
2024-03-26 09:20:26.259 | INFO     | autocoder.common.git_utils:commit_changes:21 - Committed changes with message: pre_/home/winubuntu/projects/ByzerRawCopilot/output.txt
2024-03-26 09:20:26.259 | INFO     | autocoder.common.code_auto_merge:merge_code:54 - Upsert path: ./git_utils.py
2024-03-26 09:20:26.259 | INFO     | autocoder.common.code_auto_merge:merge_code:58 - Merged 1 files into the project.
2024-03-26 09:20:26.267 | INFO     | autocoder.common.git_utils:commit_changes:21 - Committed changes with message: /home/winubuntu/projects/ByzerRawCopilot/output.txt
```





