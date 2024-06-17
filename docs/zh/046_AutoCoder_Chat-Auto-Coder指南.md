# Chat-Auto-Coder

Chat-Auto-Coder 是一款基于 AutoCoder 开发的交互式聊天工具,可以让你以对话的方式与 AI 进行沟通,辅助代码开发。

## 功能特点

- 支持添加/移除项目文件到当前会话中
- 支持与 AI 就选定文件进行对话交流 
- 支持查询项目索引
- 支持配置 AI 生成代码的参数
- 命令行交互界面,操作便捷

## 使用方法

1. 将 Chat-Auto-Coder 集成到你的项目中
2. 在项目根目录下运行 `python chat_auto_coder.py` 启动工具
3. 通过 `/add_files` 命令添加需要讨论的项目文件  
4. 通过 `/chat` 命令开始与 AI 对话
5. 使用其他命令如 `/conf`, `/index/query` 进行辅助操作
6. `/exit` 退出程序

## 安装

将 `chat_auto_coder.py` 文件复制到你的项目中即可。Chat-Auto-Coder 依赖 AutoCoder,请确保你的项目已经集成了 AutoCoder。

## 示例