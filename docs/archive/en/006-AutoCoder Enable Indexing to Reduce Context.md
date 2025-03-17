# 006-AutoCoder Enable Indexing to Reduce Context

As of today, we have found that AutoCoder actually collects the following data:

1. The source code directory specified by `source_dir`
2. The documents specified by `urls`
3. The search results from the search engine specified by `search_engine`
4. Your requirement description
5. Third-party packages (currently only supports Python)

In practice, when you are working on a project that has accumulated over many years, you will find that the project code consists of hundreds of thousands of lines, especially Java code, which makes the context window of most models insufficient to meet the needs.

In fact, bringing all the source code directly is indeed a bit wasteful. The correct approach should be:

Based on the user's requirement description, automatically filter the relevant source code files.

From the filtered source code files, further filter the first-level files they depend on.

Under normal circumstances, after such filtering, there should only be a few or a dozen files, which can also meet most of the code generation needs.

But how to filter these files? It is necessary to build an index. Now let's see how to build an index in AutoCoder.

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
  Modify server.py, after the code app = FastAPI()
  Add initialization connection code for ray.
```

To enable the indexing feature, the following two parameters must be turned on:

1. `skip_build_index` should be set to false
2. The `model` parameter must be set

Now, let's execute the above query:

```shell

auto-coder --file ./examples/from-zero-to-hero/006_index_cache.yml
```

At this point, the following information will appear in the terminal:

```
try to build index for /tmp/t-py/server/server.py md5: ad3f4e16f2a2804f973bdd67868eac5d
parse and update index for /tmp/t-py/server/server.py md5: ad3f4e16f2a2804f973bdd67868eac5d
Target Files: [TargetFile(file_path='/tmp/t-py/server/server.py', reason="The file includes the initialization of the FastAPI instance, and the user requests to add the initialization connection code for ray after 'app = FastAPI()'")]
Related Files: []
```

You can see that because we are working on a Python project, the system will collect files with the .py extension and then build an index for each file.

Open the /tmp/t-py directory:

```

(byzerllm-dev) (base) winubuntu@winubuntu:~/projects/ByzerRawCopilot$ ll /tmp/t-py
total 164
drwxrwxr-x   4 winubuntu winubuntu   4096  3月 22 19:37 ./
drwxrwxrwt 251 root      root      151552  3月 22 19:09 ../
drwxrwxr-x   2 winubuntu winubuntu   4096  3月 22 19:38 .auto-coder/
drwxrwxr-x   2 winubuntu winubuntu   4096  3月 21 19:50 server/
```

You can see there is a .auto-coder directory, which contains our index files.

Next, you should see that according to the user's query, we found the target file TargetFile(file_path='/tmp/t-py/server/server.py', and provided the reason why this file was chosen:

```
The file includes the initialization of the FastAPI instance,
and the user requests to add the initialization connection code for ray
after 'app = FastAPI()'
```

It will then look for files that this file depends on. Since our project only has one file, no other files are found.

In this way, we can greatly reduce the context given to the large model for code generation.