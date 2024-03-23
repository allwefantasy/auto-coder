# 009-How AutoCoder Reads Third-Party Library Source Code

For programmers, third-party libraries are an important part of daily work, usually with the following workflow:

1. Read existing code.
2. Read documentation for third-party libraries or interfaces to be integrated.
3. Use search engines to find documentation on how others use third-party libraries.
4. Read the third-party library's source code themselves.

Generally, steps 1, 2, and 3 should suffice. Moreover, if your third-party library is mature, large models should have adequate knowledge about it. Usually, there's no need for AutoCoder to read the source code of third-party libraries.

However, some libraries are new, or older libraries may have new versions, or you might need a deeper understanding and usage, which requires reading the source code. So, how do you make AutoCoder read the source code of third-party libraries?

Currently, there are three ways:

## Create a symbolic link to the third-party library in the `source_dir`

In AutoCoder, the `source_dir` is configured for our project directory. You can create a directory, for example, named `pkg` in this project, and link the source code of the third-party libraries you need (or parts of their directories) there. The advantage is that you can control which third-party library source code AutoCoder references. Another benefit is that this source code will also be indexed (if indexing is enabled).

## Control through the `urls` parameter

The `urls` parameter is intended for users to configure documentation, but it can also configure local files or directories in addition to http(s) links. Multiple addresses can be separated by commas. You can configure the specified third-party library source code files or directories here.
Note, the contents of `urls` will not be indexed and will be fully displayed in AutoCoder's window, so you need to consider the size.

## Control through the `py_packages` parameter

This parameter is specifically provided for Python projects, allowing you to specify the name of a third-party package. AutoCoder will automatically find the source code of this package. This parameter is the simplest but also the least flexible, as you can only specify the package name, not specific files or directories.

```yml
source_dir: /home/winubuntu/projects/ByzerRawCopilot 
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

py_packages: openai

query: |
    Read the source code of openai and write a demo code that connects to openai in src/clients/, with the filename openai_demo.py
```

However, third-party libraries often have a vast amount of code, and we usually only need a part of it. Therefore, the first method is recommended, controlling it through symbolic links.