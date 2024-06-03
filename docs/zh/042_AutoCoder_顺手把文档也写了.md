## 042_AutoCoder_顺手把文档也写了

准备给 auto-coder 加一个自动创建下一个需求yaml文件的功能。分成了两个步骤：

```yaml
include_file: 
   - ./common/editblock.yml

query: |   
   关注 auto_coder.py, command_args.py, lang.py 三个文件。添加一个 next 命令

   ```
   auto-coder next [name]
   ```

   具体功能为：

   1. 在当前目录下，寻找是否有 actions 目录，如果没有则告诉用户 "当前目录下没有 actions 目录(用英文逗号分隔)" 并退出。
   2. 如果有 actions 目录，获得 actions 所有以 三个数字开头的文件名，然后找到最大的序列号，然后在这个序列号上加 1，得到新的序列号。
   3. 将得到的序列号，转换为 3 位的字符串，然后在 actions 目录下创建一个新的文件，文件名为这个序列号加上下划线加上 name，文件为上一个文件（序列号比他小一）的内容。   
   
```

这次我们开启了 editblock 功能，可以让大模型以最少的生成token数，实现对多文件进行更改，相比diff 也有更加稳定，对模型要求也更低一些。 更多参考这篇文档[035-AutoCoder_auto_merge详解.md](./035-AutoCoder_auto_merge详解.md)。

执行完上面的 yaml文件实际上基本功能就做完了，可以用了，用的过程发现，没有自动获取上一次需求的yaml文件内容，所以这次特意强调下：

```yaml
include_file: 
   - ./common/editblock.yml

query: |   
   关注 auto_coder.py 中的next命令，新创建的文件的内容需要是上一个比他序列号小的那个文件的内容。   
```

执行：

```bash
auto-coder --file actions/064_修正内容.yml
```

本来到这里就可以收工了。但我想文档也让 auto-coder 写了把。于是

```bash
auto-coder next 生成next文档
```
自动创建了 `065_生成next文档.yml` 文件，点击打开，描述需求：

```yaml
include_file: 
   - ./common/local.yml

query: |   
   关注 auto_coder.py 中的next命令，生成一份名字叫 `041_AutoCoder_快速生成下一个需求YAML文件.md` 的文档，
   放在 docs/zh 目录下。
   要说明解决的问题是什么，怎么解决，如何使用。   
```

再执行：

```bash
auto-coder --file ./actions/065_生成next文档.yml
```

最后我们这篇文档就出现了: [041_AutoCoder_快速生成下一个需求YAML文件.m](./041_AutoCoder_快速生成下一个需求YAML文件.md)

看着还不错。