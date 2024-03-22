# 007-番外篇 AutoCoder里配置的model究竟用来干嘛

AutoCoder 最简化的配置是这样的：

```yml

source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

project_type: py

query: >
  修改 server.py ，在代码 app = FastAPI()后
  增加 ray 的初始化连接代码。
```

指定项目地址，指定 AutoCoder 根据你问题生成的prompt的存储地址，项目类型以及你的需求。

这个时候，AutoCoder 是不需要大模型的。我们来看看那些参数是需要model配合的。

## urls

你可能会指定 urls ,让 AutoCoder 参考一些文档。实际上，对这个参数而言，model 是可选的，如果设置了model，那么我们会用model去对抓取的数据做清洗，从而获得更好的效果。如果没有设置，那么就是简单的去处html, 保留文本，但是可能会有很多干扰信息。

## skip_build_index

开启索引的话，是必须要配合 model 才行的。因为索引的构建需要model对文件做分析，查询的时候需要model做过滤。

## searh_engine, search_engine_token

搜索引擎的支持，model 也是必须的。因为要过滤搜索得到的文档，并且对文档做打分，避免文档太多太长或者不想管而影响最终效果。

## human_as_model

这个参数可以让 model 之完成一些基础功能，最后生成代码的部分交给 Web 版本模型。

## execute

这个参数会让 AutoCoder 让 model 直接执行Prompt，然后将结果写入到target_file 中。所以对这个参数而言，model也是必须的。



下面是一个典型model配置：

```yml

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 100000
anti_quota_limit: 5
```

首先配置 model 的实例名称，也就是你通过 Byzer-LLM 部署的模型。接着你根据你模型的要求，配置模型的最大生成token,最大输入token。

此外，因为很多模型都有限速，所以你可以设置调用一次后，多久在调用第二次，单位是秒。

## 结论

配置 model 后，可以让 AutoCoder 更加智能。如果你的项目已经很大，那么为了开启索引，则你必须使用model.

对于model的要求，请至少保证该model 的窗口长度>32K,以保证在生产环境里获得一个不错的体验。