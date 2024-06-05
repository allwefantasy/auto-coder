# 044_AutoCoder_新手顺手指南

当你完成了第一篇内容 [000-AutoCoder_准备旅程](./000-AutoCoder_准备旅程.md),你应该把你电脑的开发环境设置好了。


设置好环境后，务必阅读下这篇文章：[037-AutoCoder_项目快速修bug实战](./037-AutoCoder_项目快速修bug实战.md)来了解 auto-coder 的基本使用流程，当你阅读完这篇内容之后，你应该在脑海里形成一个全新的开发流程。

您的开发新方式是：

1. 编写一个YAML文件来描述您的需求，Auto-Coder将生成代码并将代码合并到您的项目中。
2. 检查Auto-Coder的提交，并在vscode或其他IDE中审查被提交的代码。
3. 如果提交是基本满意，您可以选择使用github copilot或其他工具手动对代码进行微调，或者直接继续下一步工作。
4. 如果提交的代码不满足你需求，您需要撤销提交并修改YAML文件，重新执行。
5. 重复上述步骤，直到完成你的需求。

好了。有了大概之后，我们就可以开始看看细节。

## 如何把已有老项目auto-coder化

如果你有一个老项目，你想把它auto-coder化，你可以使用 

```bash
auto-coder init --source_dir /path/to/your/project
```

更多内容参考这篇： [021-AutoCoder初始化项目](./021-AutoCoder初始化项目.md)。

最重要的是会在你的项目里新增一个 actions 目录。 目录里有一个 `000_example.yml`。

我们知道，我们是通过在 yml 文件描述自己的需求或者对代码的修改逻辑，然后auto-coder 会完成对项目源码的修改。这里
你的第一步不是去修改 000_example.yml，而是从新建一个新的 yml 文件开始：

```bash
auto-coder next "我的第一个修改"
```

系统会自动在 actions 目录下创建一个新的文件 `001_我的第一个修改.yml`,并且会自动打开这个文件（vscode/idea都支持）。

## 如何和 Yaml 文件交互

001_我的第一个修改.yml 实际自动帮你拷贝了000_example.yml的内容,所以他的内容是这样的：

```yaml

include_file:
  - ./base/base.yml
  - ./base/enable_index.yml
  - ./base/enable_wholefile.yml    

query: |
  YOUR QUERY HERE
```

这个yaml文件引入了一些基础配置，诸如 base.yml, enable_index.yml, enable_wholefile.yml。

1. base.yml 是一个基础配置，里面包含了一些基础的配置，比如你的项目的根目录，你的项目的语言，你使用的模型等。
2. enable_index.yml 开启索引。
3. enable_wholefile.yml 确定代码的生成和合并模式。

你可能唯一需要修改是 project_type 字段，该字段默认为 py。 如果你的项目是其他语言，你需要修改这个字段,你可以直接使用后缀名。比如你是一个java项目，那么最后的配置看起来是这样的：

```yaml
include_file:
  - ./base/base.yml
  - ./base/enable_index.yml
  - ./base/enable_wholefile.yml    

project_type: .java
query: |
  YOUR QUERY HERE
```

除了该参数以外，强烈建议你遵循默认配置。

你唯一要做的就是修改 query 字段。query 字段是一个多行字符串，你可以在这里写你的需求。

如何去描述你想对项目的更改，参考 [038-AutoCoder_为什么你需要经过反复练习才能用好](./038-AutoCoder_为什么你需要经过反复练习才能用好.md) 以及 [036-AutoCoder_编码_prompt实践_1](./036-AutoCoder_编码_prompt实践_1.md)。

## 运行 YAML 并且完成交互

当你完成了你的需求描述，你可以使用下面的命令来运行你的YAML文件：

```bash
auto-coder --file ./actions/001_我的第一个修改.yml
```

该命令执行后，会需要你和进行两次交互：

1. auto-coder 会根据你的描述，找到你需要修改以及为了完成这些修改还可能需要的文件，这是一个大绿屏。
2. 到最后的代码生成环节，auto-coder 会停下来，等待你的输入。

我们来看看第一个交互，也就是那个大绿屏：

![](../images/044-01.png)

这大绿屏其实展示了两个部分：

1. 根据你的 query 描述，auto-coder 找到的相关文件。 
2. 文件名后面的其实还有一部分，就是告诉你为什么这个文件被选上了。

默认都被勾选上，你用Tab 切换到 OK ，点击回车就会继续下一步。







