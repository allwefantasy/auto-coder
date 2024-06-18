# Chat-Auto-Coder

Chat-Auto-Coder 是一款基于 AutoCoder 开发的交互式聊天工具,可以让你以对话的方式与 AI 进行沟通,可以无需打开编辑器，就能完成代码的开发。

![](../images/046-01.png)

## 功能特点

- 支持添加/移除项目文件到当前会话中
- 支持与 AI 就选定文件进行对话交流 
- 支持查询项目索引，获得相关文件
- 支持配置 AI 生成代码的参数
- 命令行交互界面,操作便捷
- 完善的自动补全功能

## 使用方法

1. 将 Chat-Auto-Coder 集成到你的项目中
2. 在项目根目录下运行 `chat-auto-coder` 启动工具，进入命令行交互界面
3. 通过 `/add_files` 命令添加需要讨论的项目文件  
4. 通过 `/chat` 命令开始与 AI 对话
5. 对上次commit的代码不满意，可以通过 `/revert` 命令进行回滚
6. 使用其他命令如 `/conf`, `/index/query` 进行辅助操作
7. `/exit` 退出程序
8. `/shell` 可以执行shell命令


比如我想修改一个然后我只需要说出需求即可：

![](../images/046-02.png)

然后 AI 会自动修改代码，你可以看到修改结果：

![](../images/046-03.png)

你也可以打开编辑器自己再改改。

## 安装

该命令被包含在 `auto-coder` 包中，你可以通过以下命令安装。你可以参考以下文档来安装配置 `auto-coder`。

[000-AutoCoder_准备旅程](./000-AutoCoder_准备旅程.md)


## 示例

```shell
add_files main.py,utils.py
Added files: ['main.py', 'utils.py'] (关注你想修改的文件)
/chat 在main中新添加一个hello方法
... (AI 直接修改代码，然后你可以看到修改结果)
/conf human_as_model: true
Set human_as_model to true (这个时候可以拦截auto-coder 和大模型的交互)
/index/query 查找所有调用了 request 库的文件
... (返回查询结果,主要是你可能不知道哪些文件是你想改的，可以通过这个来自动找到，然后手动添加)
/exit
Exiting...
```

## 常见配置

1. human_as_model: 是否使用人类作为模型，默认为 false。 你可以通过 `/conf human_as_model: true` 来设置。[003-使用Web版本大模型，性感的Human As Model 模式](./003-%20AutoCoder%20使用Web版大模型，性感的Human%20As%20Model%20模式.md)
2. code_model: 代码生成模型，默认为 deepseek_chat。 你可以通过 `/conf code_model: xxxx` 来设置其他通过 byzerllm 启动的模型。 

## 了解项目，但不想改代码

可以用 `/ask` 指令， 该指令会自动带上活动文件，然后回答你的问题，但不会对你的代码做任何变更。

## 对项目不熟悉，但是又想改项目怎办？

默认我们是通过 `/add_files` 来添加 chat-auto-coder 关注的文件，这需要你清晰的知道你想修改的文件，以及为了修改这个文件，你还需要哪些文件。
为了帮助大家更好的找到文件，我们提供了半自动挡的 `/index/query` 命令，你可以通过这个命令来查找你想要的文件。
如果你想完全让 chat-auto-coder 自动找到你想要的文件，你可以通过如下配置开启：

```shell
/conf skip_build_index: false
```

当执行你的需求时，系统会自动寻找相关文件。全自动档速度较慢，并且可能存在找的文件不对。如果你想人工确认找到的文件，可以
通过如下配置开启确认步骤：

```shell
/conf skip_confirm: false
```

记得，`/conf` 配置的这些参数即使重启后依然会一直有效。

你可以通过如下指令查看当前所有的配置：

```shell
/conf
```

## 常见问题

Q: 如何选择项目文件?

A: 使用 `/add_files` 命令,多个文件用逗号分隔。文件路径支持自动补全。

Q: AI 生成的代码如何合并?

A: 默认使用 editblock 方式合并。你可以通过 `/conf auto_merge: xxx` 命令修改合并方式。


Q: Chat-Auto-Coder 适合什么样的项目?

A: 理论上支持任何编程语言的项目。但建议项目文件数不要过多,否则可能影响效率。
  