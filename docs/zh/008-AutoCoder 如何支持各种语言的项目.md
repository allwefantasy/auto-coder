# 008-如何支持各种语言的项目

我们之前看到， AutoCoder 最简化的配置是这样的：


```yml

source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

query: >
  修改 server.py ，在代码 app = FastAPI()后
  增加 ray 的初始化连接代码。
```

默认他会只处理 Python 项目。其实显示的配置项是 `project_type`，这个参数可以让 AutoCoder 支持更多的项目类型。上面的配置
等价于：

```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: py

query: >
  修改 server.py ，在代码 app = FastAPI()后
  增加 ray 的初始化连接代码。

```

默认我们提供了两种类型：

1.py
2.ts

那其他类型的项目怎么办？

我们支持后缀模式。

比如如果我要支持Java, 你可以按如下方式配置：

```yml
source_dir: /tmp/JAVA_PROJECT
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: .java

query: >
  ....

```

如果你是个混合项目，比如同时有 Java, Scala, 那么可以这么配置：

```yml
source_dir: /tmp/JAVA_PROJECT
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: .java,.scala

query: >
  ....

```

这样， AutoCoder 就会关注项目里的 .java, .scala 结尾的文件。当你开启了索引，也只会对
这些文件构建索引。