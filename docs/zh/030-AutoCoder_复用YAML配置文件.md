# 030-AutoCoder_如何复用YAML配置文件

在开发一个需求的时候，我们可能会拆分成多个 yml 文件(实际上每个yml对应一次小迭代),大部分情况下，我们只会变换 query等少数
几个参数。

AutoCoder 在 YAML 配置文件中提供了 `include_file` 字段，允许你复用其他的 YAML 配置文件。

比如我把一些公共配置放在了 `./actions/common/remote.yml` 文件总，
然后我新建一个 `041_new_feature.yml` 文件,我可以在 `041_new_feature.yml` 文件中
这么写：

```yaml
include_file: 
   - ./common/remote.yml

query: |   
   AutoCoder 当检测到 include_file 参数（该参数用于指定需要 include 的文件路径，支持yml 数组格式），自动加载该参数，并且
   优先合并到 args 里去。注意，可能存在递归场景，最大递归深度为 10。
```

include_file 支持数组格式，可以指定多个文件,AutoCoder 会按照数组顺序加载。



