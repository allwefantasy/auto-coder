# 016-AutoCoder 如何从图片生成ReactJS+TypeScript+TailWind 代码

> AutoCoder >= 0.1.25 特性

这个功能在什么场景下有用了，比如你有个 reactjs + typescript + tailwind 的项目，然后你有个页面想参考某个其他的网站，这个时候你就可以截个图，然后根据该图生成对应的 reactjs + typescript + tailwind 代码。

我们看下面的例子：

```yml
source_dir: /Users/allwefantasy/projects/tt/
target_file: /Users/allwefantasy/projects/auto-coder/output.txt 
project_type: copilot/ts
image_file: /Users/allwefantasy/projects/auto-coder/screenshots/www_elmo_chat.png

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5

vl_model: qianwen_vl_chat

skip_build_index: false
execute: true
auto_merge: true
human_as_model: true

query: |   
   将html转换成 reactjs+typescript+tailwind 实现 ,并且保存在 /Users/allwefantasy/projects/tt/ 合适的目录下。
tt 已经是 reactjs + typescript + tailwind 项目
```

这里和以前的项目相比，还有几个区别：

1. 指定网页图片地址，这里通过 image_file 指定。
2. 项目配置类型为： copilot/ts 而不是 ts
3. 额外指定一个多模态模型，可以通过 vl_model 指定。
4. 多模态模型需要通过 byzerllm 进行部署。

默认情况，AutoCoder 会把图片转成 html/css 格式，然后再通过 query 转换成你要的形态。比如在我们的例子里是 reactjs+typescript+tailwind， 其他情况可能比如是用vue等。

我们指定的图片 www_elmo_chat.png 是这个样子：

![](../images/image16-01.png)

生成的中间 HTML 是这样的：

![](../images/image16-02.png)


可以看到整体layout 啥的都识别出来了，就是色系不太对，很多细节丢失了。不过相信多模态大模型的发展，后续效果肯定会越来越好。我们也支持设置逼近原图迭代次数，默认一次，但是目前还没有开放该参数。

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