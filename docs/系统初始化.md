在写测试的时候，需要对系统先做初始化才能完成组件的代码测试。

## 加载 token 统计

```
from autocoder.auto_coder_runner import load_tokenizer
load_tokenizer()
```

这个一般要放到最前面。

## 模型获取

```
from autocoder.utils.llms import get_single_llm
llm = get_single_llm("v3_chat", product_mode="lite")
```

这样就可以获取一个叫 v3_chat 的模型。

## 配置参数

一般需要根据被测试的对象，合理设置 AutoCoderArgs 的参数。


```
from autocoder.common import AutoCoderArgs
args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=400,  # 设置较小的token限制以触发抽取逻辑
        context_prune_sliding_window_size=10,
        context_prune_sliding_window_overlap=2,
        query="如何实现加法和减法运算？"
    )
```

