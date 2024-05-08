# 024-AutoCoder并行索引构建和查询
> 版本要求：
> - auto-coder >= 0.1.51
## 什么模型比较适合做索引构建和查询？
deepseek 和 haiku 都属于性价比较高的模型，可以用来做索引构建。
索引查询则可以使用 gpt-3.5-turbo，这个模型的速度比较快，效果不错，适合做索引查询。

## 并行度设置

正常一个 python文件，一般使用 haiku 构建索引消耗时间为 2-7s 之间，而使用 deepseek 则消耗在10-30s 之间。
如果用户第一次构建索引，会导致等待时间过长，所以我们可以使用并行的方式来构建索引。

```yaml
# 开启索引
skip_build_index: false
# 索引查询时的级别
index_filter_level: 1
# 查询索引的并行度设置
index_filter_workers: 4

# 单次构建最大的输入长度，建议设置较大值
index_model_max_input_length: 30000
# 构建索引的并行度设置
index_build_workers: 4
```

如上所示，我们可以通过设置 `index_build_workers` 来设置构建索引的并行度，比如我这里设置为4。
不过单单设置这个为4 可能还不够，我们还需要在部署模型的时候把并行度也匹配下：

```bash
byzerllm deploy --pretrained_model_type saas/openai \
--cpus_per_worker 0.001 \
--gpus_per_worker 0 \
--num_workers 4 \
--infer_params saas.base_url="https://api.deepseek.com/v1" saas.api_key=${MODEL_DEEPSEEK_TOKEN} saas.model=deepseek-chat \
--model deepseek_chat
```

这里我部署了deepseek 模型，然后设置了 `--num_workers 4`，这样就可以保证构建索引和查询索引设置的并行度不会被 byzerllm 代理阻塞。一般而言，我们可以把 num_workers 的值设置的比 index_build_workers 大一点，这样可以保证索引构建的时候不会被阻塞。

