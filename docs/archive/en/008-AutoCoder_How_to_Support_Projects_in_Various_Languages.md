# 008-How to Support Projects in Various Languages

Previously, we saw that the simplest configuration for AutoCoder looks like this:

```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

query: >
  Modify server.py, add ray initialization connection code after the code app = FastAPI().
```

By default, it will only process Python projects. The displayed configuration item is actually `project_type`, which allows AutoCoder to support more project types. The above configuration is equivalent to:

```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: py

query: >
  Modify server.py, add ray initialization connection code after the code app = FastAPI().
```

By default, we provide two types:

1. py
2. ts

What if you have other types of projects?

We support suffix patterns.

For example, if you want to support Java, you can configure it as follows:

```yml
source_dir: /tmp/JAVA_PROJECT
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: .java

query: >
  ....
```

If you have a mixed project, such as having both Java and Scala, you can configure it like this:

```yml
source_dir: /tmp/JAVA_PROJECT
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: .java,.scala

query: >
  ....
```

In this way, AutoCoder will focus on files ending with .java and .scala in the project. When you enable indexing, it will only build indexes for these files.

## Additional Filtering

Sometimes you may want to implement more refined project file filtering, such as excluding a certain directory. In this case, you can refer to [031-AutoCoder_Regular_Expression_Exclude_Directory](./031-AutoCoder_正则表达式排除目录.md).

In general, when you define project types by suffix, you can use the `exclude_files` parameter to exclude some directories, using either regular expressions or text descriptions (which will be automatically converted to regular expressions).

```yaml
exclude_files:      
   - human://Any directory containing common
```

exclude_files supports two modes of configuration:

1. Strings starting with human://, AutoCoder will generate a regular expression based on the following text. For example, the above example will generate the regular expression `.*common.*`.
2. Strings starting with regex://, AutoCoder will directly use the following text as a regular expression. For example, `regex://.*common.*`.