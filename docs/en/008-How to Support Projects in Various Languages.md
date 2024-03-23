# 008-How to Support Projects in Various Languages

We previously saw that the simplest configuration for AutoCoder is as follows:


```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

query: >
  Modify server.py, adding the Ray initialization code after the code app = FastAPI().
```

By default, it only processes Python projects. In fact, the explicit configuration item is `project_type`, which allows AutoCoder to support more project types. The configuration above is equivalent to:

```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: py

query: >
  Modify server.py, adding the Ray initialization code after the code app = FastAPI().

```

By default, we offer two types:

1. py
2. ts

What about projects of other types?

We support the suffix mode.

For example, if you want to support Java, you can configure it as follows:

```yml
source_dir: /tmp/JAVA_PROJECT
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: .java

query: >
  ....

```

If you have a mixed project, such as both Java and Scala, then you can configure it like this:

```yml
source_dir: /tmp/JAVA_PROJECT
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: .java,.scala

query: >
  ....

```

This way, AutoCoder will focus on files ending in .java and .scala in the project. When indexing is enabled, it will also only build indexes for these files.