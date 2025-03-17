# 027-AutoCoder_我只要效果好_那么最佳组合是什么

经过消耗至少 2000多万token的探索之后，我总结在 AutoCoder中 辅助编程的最佳模型组合：

1. 索引构建 DeepSeek/Haiku  (对应 index_model 参数)
2. 索引查询/AutoCoder 功能驱动 DeepSeek/GPT3.5 (对应 model 参数)
3. 代码生成  Claude Opus / GPT-4o (对应 code_model参数，推荐human_as_model 设置为true)
4. 知识库构建 OpenAI Embedding （Small） (对应 emb_model 参数)
5. 图片转web GPT-4o (对应 vl_model 参数)

此外，因为代码生成的token消耗量也很大， AutoCoder 提供了独有的 human_as_model 功能，允许你使用 web 版本的模型来完成代码生成，相当于包月，避免海量token的计费。


如果你完全不考虑成本，那么最好的组合是：
1. 索引构建/索引查询/AutoCoder功能驱动 用 GPT-3.5
2. 代码生成用 Claude Opus (human_as_model 设置为false, 这个时候会走API直接生成代码，无需人工到web里去复制黏贴)
3. 知识库构建 OpenAI Embedding （Big） (对应 emb_model 参数)
4. 图片转web GPT-4o (对应 vl_model 参数)

