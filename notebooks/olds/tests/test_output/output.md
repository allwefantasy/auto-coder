002-auto-coder.chat 初级入门指南
我们在上一篇介绍了如何安装 auto-coder.chat 回 Windows: auto-coder.chat 安装指南
MacOS/Linux 直接 pip install -U auto-coder 即可。测试过的 python 版本为：3.10/3.11
初始化设置
在 PowerShell/CMD 或者 VSCode 内置的 terminal 中输入如下指令（auto-coder.chat）：
PS C: \Users\Administrator\projects\auto-coder> auto-coder.chat
记得不要忘记了使用 conda activate auto-coder 切换到合适的环境虚拟环境哟。
第一次运行，系统会自动要求你提供一个大模型供应商（你后续可以改，比如用本地的模型或者其他第三方模型），此时会弹出一个对话框：

我们分别给了官网，你可以去官网注册一个账号，你可以用上下箭头来切换网站，最后用 Tab 键切换到 Ok 按钮，然后点击 Enter 回车键确认。

假设我使用的是 Deepseek 官网，你应该和我一样，在 API Keys 页面创建好了一个 API Key：![一个包含两个选项的界面，选项分别是 '硅基互动' 和 'Deepseek 官方'，并提供 Ok 和 Cancel 按钮。](./test_output/_images/cropped_002-auto-coder.chat-初级入门指南.pdf_page2.png)

另外你可以冲比如一两块钱，这样你就用可用的 Token 数余额了：