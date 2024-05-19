# 031-AutoCoder_Regular Expression Exclude Directory

When you use file suffix to filter files, the system will automatically exclude the following directories:

```
[".git", ".svn", ".hg", "build", "dist", "__pycache__", "node_modules"]
```

If you want to exclude other directories or files, you can use the `exclude_files` parameter. Here is an example:

```yaml
include_file: 
   - ./common/remote.yml

project_type: .py
exclude_files:      
   - human://Any directory containing common

query: |   
   SuffixProject supports the `exclude_files` parameter to exclude directories that do not need to be processed. The `exclude_files` parameter
   supports regular expressions and supports YAML array format.
```

By specifying the `project_type`, we collect all files with the .py suffix in the project, and at the same time, by specifying the `exclude_files` parameter, we exclude all directories containing common.

There are two modes of configuration for `exclude_files`:

1. Strings starting with human://, AutoCoder will automatically generate a regular expression based on the following text. For example, the example above will generate the regular expression `.*common.*`.
2. Strings starting with regex://, AutoCoder will directly use the following text as the regular expression. For example, `regex://.*common.*`.

You can see relevant information in the logs:

```
2024-05-19 14:54:12.498 | INFO     | autocoder.suffixproject:parse_exclude_files:58 - Generated regex pattern: .*/common/.*
```

As well as which files are excluded as a result:

```
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/code_auto_execute.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/JupyterClient.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/screenshots.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/command_templates.py
2024-05-19 14:54:12.526 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/__init__.py
2024-05-19 14:54:12.527 | INFO     | autocoder.suffixproject:should_exclude:67 - Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/types.py     Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/ShellClient.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/cleaner.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/search.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/audio.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/code_auto_merge.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/code_auto_generate.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/git_utils.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/const.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/image_to_page.py
Excluding file: /Users/allwefantasy/projects/auto-coder/src/autocoder/common/llm_rerank.py