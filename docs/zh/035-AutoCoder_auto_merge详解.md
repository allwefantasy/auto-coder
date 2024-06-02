# 035-AutoCoder_auto_merge详解

通过 auto_merge 用户相当于可以控制三个东西：

1. 是不是要自动合并到现有源码中
2. 生成/修改代码的格式
3. 生成修改代码合并的方式

auto_merge 接受两种类型的参数：

1. bool 类型.
2. 字符串类型. 可选值为 wholefile,diff,strict_diff,editblock

如果设置为 true, 那么等价于 wholefile。

我们详细说明下这几种模式。

## wholefile

这种模式下，AutoCoder 会要求大模型生成修改后的完整代码，合并的时候会把生成的代码直接替换到源码中。
这种模式对于新文件以及有大量修改的文件非常适用。缺点当修改很小时也需要消费大量Token,并且大部分模型都很难做到
几乎原模原样输出修改后的完整代码。

## editblock

这种模式下，AutoCoder 会让大模型生成 git 里的 "合并冲突标记" 格式，比如：

```tsx
##File: /Users/allwefantasy/projects/auto-coder.example_01/frontend/src/pages/ListExamples.tsx
<<<<<<< SEARCH
import React, { useEffect, useState } from 'react';
import axios from 'axios';
=======
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useHistory } from 'react-router-dom';
>>>>>>> REPLACE
```

该模式优点:

1. 可以减少token消耗
2. 生成格式复杂度也不高，较多大模型能够支持

缺点:
1. 因为是根据 SEARCH 不分进行替换，有概率一个文件中有多个 SEARCH，导致合并错误
2. 串行执行，当一个文件有多个 SEARCH 时，会串行自行，期间也可能导致 1 的问题。

## diff

这是一种宽松的diff模式，AutoCoder 会要求大模型直接生成 diff 格式，但是该 diff 格式不要求大模型生成行号，只需要生成 @@ *** @@ 这种格式即可。
然后通过字符匹配的方式找到修改的点，进行合并。这种模式对模型要求较低，并且大部分情况下都能很好的工作，但是对于一些特殊情况，可能会出现合并错误。

diff 最大的价值在于，可以减少几百倍的token生成量，并且极大的提升了生成速度。未来边写文字，就可以边看到修改后的效果很快可以来临。

缺点和 editblock 类似。

## strict_diff

这是一种严格的diff模式，AutoCoder 会将源文件带行号发送给大模型，并要求大模型直接生成 unified diff 格式该 diff 格式需要生成@@ -7,10 +7,10 @@ 这种的行号，然后使用 patch 工具进行进行合并。这种模式对模型要求最高，但只要模型生成的diff 是正确的，则一定能够正确合并。

缺点是对大模型要求较高，大模型很难正确生成这种格式的diff。

## 使用经验

目前推荐使用 wholefile 和 editblock 两种模式。editblock 模式兼具 diff 优势又相对来说易于阅读。
需要程序员有个预判，如果会有较多文件修改，但每个文件修改不大，那么使用 editblock 模式。如果修改较大，那么使用 wholefile 模式。

因为不同的模型支持能力不一致，如果你发现 editblock 经过多次修改描述后依然合并错误，再使用 auto-coder revert 进行回滚，
可以再次尝试 diff 模式。

## 搭配参数

enable_multi_round_generate 与 auto_merge 搭配使用，可以实现按文件多轮生成（每一次只生成一个文件），最后再做统一合并的效果，但对模型的要求也更高。一般情况下，建议如下组合：

1. diff/editblock + enable_multi_round_generate=false
2. wholefile + enable_multi_round_generate=true

















