# 013-AutoCoder How To Check Token Consuming

> This feature is available when auto-coder >= 0.1.20 

You can use the following command:

```shell
auto-coder store --source_dir YOUR_PROJECT
```

Note that you need to make sure that there is a .auto-coder directory in your project.

The output is:

```
+-----------------+----------------------+--------------------------+
| project         |   input_tokens_count |   generated_tokens_count |
+=================+======================+==========================+
| ByzerRawCopilot |                51391 |                     3321 |
+-----------------+----------------------+--------------------------+
```