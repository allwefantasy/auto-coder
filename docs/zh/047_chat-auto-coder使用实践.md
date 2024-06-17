# 047_chat-auto-coder使用实践

Chat-Auto-Coder 是一个命令行聊天工具，可以让你以对话的方式与 AI 进行沟通，可以无需打开编辑器，就能完成代码的开发。

## 准备工作

首先，进入你的项目，并且初始化

```bash
auto-coder init --source_dir .
```

如果你想使用索引功能，你需要先构建索引

```bash
auto-coder index --file ./actions/base/base.yml
```

现在可以进入 Chat-Auto-Coder 了。

```bash
chat-auto-coder
```

## 实践

进去后，比如我想让他给我创建一个文件（当前我这个文档）：

![](../images/047-01.png)

点击回车后，AI 会自动创建一个该文档。

这篇文章我们会演示如何使用 chat-auto-coder 给 chat-auto-coder 添加排除目录的功能。

### 起手：添加你想修改的文件

我需要修改的文件是 chat_auto_coder.py，我通过 `/add_files` 指令进行添加，系统会自动补全命令和文件。

![](../images/047-02.png)

### 查看当前有多少活动文件

我通过 `/list_files` 指令查看当前有多少活动文件。

![](../images/047-03.png)

可以看到，我们成功的添加了 chat_auto_coder.py 文件。

### 对代码进行修改

我通过 `/chat` 指令对 chat_auto_coder.py 进行修改,我现在想新增一个 `/exclude_dirs` 指令，用于排除目录。

下面是我的需求描述：

```
新增/exclude_dirs 指令, 逻辑和/add_files 指令一样,
只是保存到 memory 的exclude_dirs 字段下,和 current_files 同级别
```

![](../images/047-04.png)

点击回车后，AI 会自动帮你修改代码。在终端你可以看到提交后diff 的内容：

![](../images/047-05.png)

此外，你还可以点击 vscode 右侧的 source_control 查看提交：

![](../images/047-06.png)


