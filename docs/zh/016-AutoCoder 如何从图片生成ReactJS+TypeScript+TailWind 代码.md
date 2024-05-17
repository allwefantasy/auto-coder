# 016-AutoCoder 如何从图片生成ReactJS+TypeScript+TailWind 代码

> AutoCoder >= 0.1.58 特性

需要额外安装：

```shell
pip install playwright
playwright install
```

这个功能在什么场景下有用呢，比如你有个 reactjs + typescript + tailwind 的项目，然后你有个页面想参考某个其他的网站，这个时候你就可以截个图，然后根据该图生成对应的 reactjs + typescript + tailwind 代码了。

默认情况，AutoCoder 会把图片转成 html/tailwind 格式，然后再通过 query 使用 model 将其转换成你最终需要的形态。
所以你可以只生成 html/tailwind 代码 或者是生成 reactjs + typescript + tailwind 代码。

## 只生成 HTML + Tailwind

我们看下面的例子：

```yml
source_dir: /Users/allwefantasy/projects/tt/
target_file: /Users/allwefantasy/projects/auto-coder/output.txt 
project_type: copilot/ts

image_file: /Users/allwefantasy/projects/auto-coder/screenshots/www_elmo_chat.png
image_mode: direct
image_max_iter: 1

model: deepseek_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

vl_model: gpt4o_chat

skip_build_index: false
execute: true
auto_merge: true
human_as_model: true

query: |   
   将html转换成 reactjs+typescript+tailwind 实现 ,并且保存在 /Users/allwefantasy/projects/tt/ 合适的目录下。
tt 已经是 reactjs + typescript + tailwind 项目
```

/Users/allwefantasy/projects/tt/ 是一个已经存在的 reactjs + typescript + tailwind 项目。我们希望新的代码生成到这个项目合适的目录。

这里的配置文件相比以前，几个区别：

1. 指定网页图片地址，这里通过 image_file 指定。
2. 项目配置类型为： copilot/ts 而不是 ts
3. 额外指定一个多模态模型，可以通过 vl_model 指定,推荐 gpt_4o
4. 多模态模型需要通过 byzerllm 进行部署。
5. image_max_iter 可以设置迭代次数，迭代次数越多，理论上生成的代码越接近原图，你也可以查看中间生成的 html 文件，看看是否满足你的需求。

## 生成 reactjs + typescript + tailwind

此时只需要改一行配置即可：

```yml
project_type: ts
```

我们把project_type 从 copilot/ts 改成 ts,这样中间会让我们勾选相关的一些文件，并且进行代码转换。

如果你希望转成诸如vue等，你只需要在 query中说明即可。

## 结果

我们指定的图片 www_elmo_chat.png 是这个样子：

![](../images/image16-01.png)

生成的中间 HTML 是这样的：

![](../images/image16-02.png)


可以看到整体layout 啥的都识别出来了，就是色系不太对，很多细节丢失了。不过相信多模态大模型的发展，后续效果肯定会越来越好。（PS: GPT-4o的效果已经相当好了）

最后生成的 ReactJS 代码则是这样的：

```jsx
import React from 'react';
import tw from 'tailwind-styled-components';

const Container = tw.div`
  bg-gradient-to-b from-orange to-yellow
  text-white
  font-Arial
  flex
  flex-col
  items-center
  pt-50
  min-h-screen
`;

const Title = tw.h1`
  text-3xl
  mb-20
`;

const Subtitle = tw.h2`
  text-2xl
  mb-30
`;

const InstallButton = tw.button`
  bg-green
  text-white
  border-none
  px-10 py-2
  font-semibold
  cursor-pointer
  rounded-lg
  mb-20
`;

const GoldRibbon = tw.div`
  bg-gold
  text-black
  font-medium
  px-5 py-2
  relative
  mb-10
`;

const RibbonBeforeAfter = tw.div`
  absolute
  w-full
  h-2
  bg-black
  top-1/2
  transform -translate-y-1/2
`;

const RibbonBefore = tw(RibbonBeforeAfter)`
  left[-10px]
  right[100%]
`;

const RibbonAfter = tw(RibbonBeforeAfter)`
  left[100%]
  right[-10px]
`;

const FooterText = tw.p`
  text-base
  mb-20
`;

const ElmoChat: React.FC = () => (
  <Container>
    <Title>
      Elmo{' '}
      <span role="img" aria-label="Electric Spark">
        ⚡
      </span>
    </Title>
    <Subtitle>
      Elmo is your AI chrome extension to create summaries, insights and extended knowledge.
    </Subtitle>
    <InstallButton onClick={() => window.open('https://chrome.google.com/webstore/detail/elmo/your-extension-id')}>
      Install from Chrome Web Store
    </InstallButton>
    <p>Free • No Account Needed • Supports Multiple Languages</p>

    <GoldRibbon>Featured on Chrome Web Store</GoldRibbon>
    <GoldRibbon>Developed by Established Publisher</GoldRibbon>

    <FooterText>Summaries and Bullet Points</FooterText>
  </Container>
);

export default ElmoChat;
```

然后继续使用 AutoCoder 修改和迭代该页面即可。