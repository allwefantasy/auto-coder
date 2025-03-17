# 006-AutoCoder 开启索引，减少上下文

到今天为止，我们发现，AutoCoder 实际上会收集以下数据：

1. 通过 source_dir 指定的源码目录
2. 通过 urls 指定的文档
3. 通过search_engine 指定的搜索引擎检索结果
4. 你的需求描述
5. 第三方包（目前仅支持python）


实际上当你在一个积累了很多年的项目上，你会发现项目代码有几十万行，尤其是 Java 代码，这导致大部门模型的上下文窗口无法满足需求。

如果直接把所有源码都带上，确实也有点太浪费了，正确的做法应该是：

1. 根据用户的需求描述，自动筛选相关的源码文件。

2. 从筛选出来的源码文件，再筛选一级他们依赖的文件。

一般情况，经过这样的筛选，应该也就几个或者十几个文件，也能满足大部分代码生成的需求。

但是如何筛选这些文件呢？必须要构建索引。现在让我们看看如何在 AutoCoder 中构建索引。

```yml

source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: deepseek_chat
model_max_length: 2000
model_max_input_length: 30000
anti_quota_limit: 0

project_type: py

skip_build_index: false

query: >
  修改 server.py ，在代码 app = FastAPI()后
  增加 ray 的初始化连接代码。
```

为了能够开启索引功能，需要保证如下两个参数开启：

1. skip_build_index 设置为 false
2. model 参数必须设置

现在，让我们执行下上面的query:

```shell

auto-coder --file ./examples/from-zero-to-hero/006_index_cache.yml
```

此时，会在终端出现如下信息：

```
try to build index for /tmp/t-py/server/server.py md5: ad3f4e16f2a2804f973bdd67868eac5d
parse and update index for /tmp/t-py/server/server.py md5: ad3f4e16f2a2804f973bdd67868eac5d
Target Files: [TargetFile(file_path='/tmp/t-py/server/server.py', reason="该文件包含了初始化 FastAPI 实例，并且用户要求在 'app = FastAPI()' 之后增加 ray 的初始化连接代码")]
Related Files: []
```

可以看到，因为我们是python项目，所以系统会收集 .py 结尾的文件，然后对每一个文件构建索引。

打开 /tmp/t-py 目录：

```

(byzerllm-dev) (base) winubuntu@winubuntu:~/projects/ByzerRawCopilot$ ll /tmp/t-py
total 164
drwxrwxr-x   4 winubuntu winubuntu   4096  3月 22 19:37 ./
drwxrwxrwt 251 root      root      151552  3月 22 19:09 ../
drwxrwxr-x   2 winubuntu winubuntu   4096  3月 22 19:38 .auto-coder/
drwxrwxr-x   2 winubuntu winubuntu   4096  3月 21 19:50 server/
```

可以看到有个 .auto-coder 目录，里面就是有我们的索引文件。

接着你应该看到，根据用户的query,我们找到了目标文件TargetFile(file_path='/tmp/t-py/server/server.py'，并且给出了为什么是这个文件的原因：

```

该文件包含了初始化 FastAPI 实例，
并且用户要求在 'app = FastAPI()' 
之后增加 ray 的初始化连接代码
```

接着他会找这个文件依赖的文件，因为我们这个项目只有一个文件，所以找不到其他的文件了。

这样，我们就能大大缩小最后给到大模型去生成代码的上下文了。

