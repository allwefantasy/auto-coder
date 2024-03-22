As of today, we have discovered that AutoCoder actually collects the following data:

1. Source code directory specified by `source_dir`
2. Documents specified through `urls`
3. Search engine results obtained using the `search_engine`
4. Your requirement description
5. Third-party packages (currently supporting only Python)

In reality, when working on a project that has accumulated over several years, you may find that it contains hundreds of thousands of lines of code, especially in the case of Java, which makes it challenging for most models' context windows to meet the requirements.

In fact, directly providing all source code is quite wasteful. The correct approach should be:

Automatically filter out relevant source code files based on the user's requirement description.

From the filtered source code files, further filter out the files they depend on.

Under normal circumstances, after such filtering, there would typically be just a few or a dozen files, which can satisfy the majority of code generation needs.

But how do we filter these files? Building an index is essential. Let's now see how to build an index in AutoCoder.

```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 100000
anti_quota_limit: 5

project_type: py

skip_build_index: false

query: >
  Modify server.py and add initialization connection code for Ray after the line 'app = FastAPI()'.
```

To enable the indexing feature, ensure the following two parameters are set accordingly:

1. Set `skip_build_index` to `false`
2. The `model` parameter must be configured

Now, let's execute the above query:

```shell
auto-coder --file ./examples/from-zero-to-hero/006_index_cache.yml
```

At this point, the following information will appear in the terminal:

```
Try to build index for /tmp/t-py/server/server.py md5: ad3f4e16f2a2804f973bdd67868eac5d 

Please start translating the content now.Parse and update the index for `/tmp/t-py/server/server.py` with md5 hash: ad3f4e16f2a2804f973bdd67868eac5d.

**Target Files:**
```json
[TargetFile(file_path='/tmp/t-py/server/server.py', reason="This file contains the initialization of a FastAPI instance, and the user has requested to add ray initialization connection code after 'app = FastAPI()'")]
```
**Related Files:**
```json
[]
```

As we can see, since this is a Python project, the system collects files ending in `.py` and builds an index for each one.

Opening the `/tmp/t-py` directory:

```bash
(byzerllm-dev) (base) winubuntu@winubuntu:~/projects/ByzerRawCopilot$ ll /tmp/t-py
total 164
drwxrwxr-x   4 winubuntu winubuntu   4096 Mar 22 19:37 ./
drwxrwxrwt 251 root      root      151552 Mar 22 19:09 ../
drwxrwxr-x   2 winubuntu winubuntu   4096 Mar 22 19:38 .auto-coder/
drwxrwxr-x   2 winubuntu winubuntu   4096 Mar 21 19:50 server/
```
Here, you'll notice a directory named `.auto-coder`, which contains our index files.

Next, as per the user's query, we've identified the target file `TargetFile(file_path='/tmp/t-py/server/server.py')` and provided the reason why it's the target:

```markdown
This file initializes a FastAPI instance,
and the user wants to add ray initialization connection code 
after 'app = FastAPI()'
```

Subsequently, it searches for files that the target file depends on. Since our project only consists of one file, no other related files are found.

This way, we significantly narrow down the context passed to the large model for generating code. 

---

Now, please proceed with translating the content directly.