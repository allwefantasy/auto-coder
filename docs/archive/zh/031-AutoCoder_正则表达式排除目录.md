# 031-AutoCoder_正则表达式排除目录

当系统在过滤文件时，会默认排除以下目录：

```
[".git", ".svn", ".hg", "build", "dist", "__pycache__", "node_modules"]
```

如果你还想排除一些其他目录或者文件，你可以使用 `exclude_files` 参数。下面是一个例子：

```yaml
include_file: 
   - ./common/remote.yml

project_type: .py
exclude_files:      
   - human://任何包含 common 的目录

query: |   
   SuffixProject 支持 exclude_files 参数，用于排除不需要处理的目录。 exclude_files 参数
   支持正则表达式，并且支持yaml的数组格式。
```

通过 project_type 我们会收集项目里所有.py后缀的文件，同时通过指定 exclude_files 参数，排除了所有包含 common 的目录。

exclude_files 支持两种模式的配置:

1. human:// 开头的字符串，AutoCoder 会根据后面的文本，自动生成正则表达式。比如上面的例子，会自动生成 `.*common.*` 的正则表达式。
2. regex:// 开头的字符串，AutoCoder 会直接使用后面的文本作为正则表达式。比如 `regex://.*common.*`。

你可以在日志中看到相关信息：

```
2024-05-19 14:54:12.498 | INFO     | autocoder.suffixproject:parse_exclude_files:58 - Generated regex pattern: .*/common/.*
```

以及哪些文件因此被排除：

```
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/code_auto_execute.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/JupyterClient.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/screenshots.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/command_templates.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/__init__.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/types.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/ShellClient.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/cleaner.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/search.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/audio.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/code_auto_merge.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/code_auto_generate.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/git_utils.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/const.py
2024-05-19 14:54:12.528 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/image_to_page.py
2024-05-19 14:54:12.528 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/llm_rerank.py
```

```



