# 011-AutoCoder最佳实践之组合大模型API/Web订阅

前面一篇文章，我们介绍了如何在公司级别使用AutoCoder，架构是这样的：

![](../images/client-server.png)


而作为研发同学，实际上相当于把 大模型 Server 也放在自己的笔记本上。但受限于笔记本的性能，
难以解决窗口（上下文）长度以及模型效果问题。

而如果使用 SaaS API的话，这个Token费用在短期内又受不了（在模型厂商没有大规模降价或者AutoCoder 没有提供专有流量的时候）。

那怎么真正把 AutoCoder 给利用起来呢？
笔者目前的最佳实践是，组合API和Web订阅两种方式，获得效果和成本的平衡。


1. Web 版本的优势是按月订阅，对于Token使用量巨大的同学而言，性价比很高，而且他的效果也往往很不错。AutoCoder Token消耗量最大的环节就是生成代码的环节。
2. API 版本对于 AutoCoder 主要应用于索引构建，HTML 正文抽取等小功能点，相对来说，Token消耗量小一些，但能让 AutoCoder自动化运转起来。

基本思路就是：

1. 给 AutoCoder 配置一个模型，用于索引构建，HTML 正文抽取等小功能点。
2. 开启 human_as_model模式，使用 Web 版本的大模型，用于生成代码。

具体用法，我们之前在 [human as model 模式](./003-%20AutoCoder%20使用Web版大模型，性感的Human%20As%20Model%20模式.md)有详细的使用介绍。

此外，如果你好奇 AutoCoder 配置的模型主要都会被用在哪些地方，可以参考我们的之前的[番外篇](./007-%E7%95%AA%E5%A4%96%E7%AF%87%20AutoCoder%E9%87%8C%E9%85%8D%E7%BD%AE%E7%9A%84model%E7%A9%B6%E7%AB%9F%E7%94%A8%E6%9D%A5%E5%B9%B2%E5%98%9B.md)

笔者本人的组合配置是：

1. qwen-max API （目前免费送 100w token）
2. Claude3 Opus Web 订阅

目前实测效果成本最佳。



