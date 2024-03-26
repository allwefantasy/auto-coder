# 011-AutoCoder Best Practices: Combining Large Model API/Web Subscriptions

In the previous article, we introduced how to use AutoCoder at the company level, with the architecture as follows:

![](../images/client-server.png)

For R&D colleagues, this essentially means hosting the Large Model Server on their own laptops. However, due to the limitations of laptop performance, it's challenging to address window (context) length and model effectiveness issues.

Using SaaS APIs can be expensive in the short term (before model vendors significantly reduce prices or AutoCoder provides dedicated traffic).

So, how can AutoCoder be truly utilized?
The author's current best practice is to combine API and Web subscription methods to achieve a balance between effectiveness and cost.

1. The Web version's advantage is its monthly subscription, offering great value for those who use a massive amount of Tokens, and its performance is often very good. The stage where AutoCoder consumes the most Tokens is during code generation.
2. The API version is mainly used for index building, HTML body extraction, and other small features in AutoCoder, consuming fewer Tokens, but enabling AutoCoder automation.

The basic idea is:

1. Configure AutoCoder with a model for index building, HTML body extraction, and other minor features.
2. Activate the human_as_model mode, using the Web version's large model for code generation.

For specific usage, we have detailed instructions in [human as model mode](./003-%20Using%20Web%20Version%20Large%20Model%20in%20AutoCoder,%20The%20Sexy%20Human%20As%20Model%20Mode.md).

Furthermore, if you're curious about what the  model configured in AutoCoder is mainly used for, you can refer to our previous [special edition](./007-%20Special%20Edition%20What%20are%20the%20models%20configured%20in%20AutoCoder%20actually%20used%20for.md).

My personal configuration combination is:

1. qwen-max API (currently offering 1 million tokens for free)
2. Claude3 Opus Web subscription

This combination has proven to offer the best performance to cost ratio so far.
