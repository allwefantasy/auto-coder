# Why Not GitHub Copilot, Not Devin, But AutoCoder

I often say, don't go against the AGI trend, but also have a clear understanding of the current boundaries of large models.

GitHub Copilot is essentially a derivative of IDE tools, a more "intelligent" code suggestion, and its Copilot Chat is just integrating a chat box into the IDE, no different from integrating a search box into an IDE tool, still a product of classical product thinking.

More specifically, I can analyze from three dimensions:

The first dimension is the positioning of GitHub Copilot. I have always been a hardcore user of GitHub Copilot, but because its positioning is only code suggestions, it needs to pursue response time rather than effectiveness. Thus, its biggest problem is that it cannot implement new code based on the entire project's source code (this would cause unacceptable delay and too high cost).

The second dimension is that GitHub Copilot cannot simulate human development behavior. When we actually develop, we generally base it on existing functions and develop according to some "documentation," "third-party code," and "search engines."

For example, if Byzer-LLM wants to interface with the Qwen-vl multimodal large model, as a developer, I need to prepare at least three things:

1. First, we need to understand and refer to how Byzer-LLM previously interfaced with various models.
2. Secondly, I need to find the API documentation of Qwen-VL to understand its API.
3. I might also need to search for how others have interfaced with it, and if I used a third-party SDK, I would need its documentation or code.

Only after obtaining this information can we write reliable code. But can GitHub Copilot do these? Obviously not.

The third dimension is that I cannot replace the model, which means I can only use the model behind GitHub Copilot, even if I have a web subscription to GPT-4/Claude3-Opus. If it's used by a company, how can we ensure the model's private deployment?

Therefore, the essence of the GitHub Copilot product determines that it is just a smarter suggestion tool, not simulating humans programming. Although it's not against the AGI trend, it's indeed not enough AI Native, not making full use of AI.

Devin, on the other hand, went to another extreme. It is an AI-assisted programming tool, but its goal is for AI to automatically complete all processes required to meet a simple demand: demand analysis, decomposition, environment setup, project construction, code writing, automatic debugging, and even automatic operation. This goal is too grand and does not conform to the basic principles. With the current capabilities of large models, it can only serve as a demo and for scientific exploration.

Why does it not conform to the basic principles? Because anyone who has done R&D knows that requirements are a dynamic process, iterated out, and gradually understood during iteration, with too many factors like client, vendor, business, technology, and human nature involved. So, I say Devin's goals are not only too ambitious to achieve but also do not conform to the basic principles, even with AGI, it's hard to be entirely feasible.

I saw a high-star project these days, also on AI-assisted programming. The author used this tool to help themselves create a chat program with JS. The basic idea was to complete the communication through terminal shell interaction. However, during the demo, the AI-written code went into an infinite loop. Since it had already taken a lot of time, and he didn't want to edit it, he just said, anyway, the overall demonstration was done... It was awkward...

In short, even for a simple application, the failure rate of the current smartest large models is too high. When I was working on AutoCoder, I also found that even creating a basic project template based on user requirements for stable reproduction is challenging for many large models.

So, I summarize two major problems with his demonstration:

1. The biggest failure of his entire demonstration process is not allowing programmers to modify and adjust the code.
2. Besides, there is far more existing code that needs maintenance than new code to be created. Helping users to iterate existing code is more valuable and challenging than creating a new project.

Although the project members are quite rational to recognize:

I don't think A can (at least in the near future) create applications without involving developers. Thus, GPT Pilot would gradually write applications, just as developers do in real life.

But like many people who say they believe in the Scaling Law, they easily deviate from it in practice.

So, when making AI-assisted programming products, the core principles are:

1. Align with the current capabilities of models, focusing on what models can currently do well, avoiding overambition.
2. The product should facilitate rapid, small-step runs with humans, ensuring synchronization with demand iteration.
3. Retain sufficient extensibility, keeping many imaginative functions

which will qualitatively change as model capabilities improve, ensuring AutoCoder can always benefit from model advancements.

Based on these principles, some features of AutoCoder stand out:

## Focus on the Coding Phase

AutoCoder focuses on the coding phase, compared to demand analysis, decomposition, environment setup, project construction, code writing, automatic debugging, and even automatic testing. We only focus on programming, aiming to make this phase more efficient, stable, and reliable.

## Simulate the Programmer's Coding Process for Quick Iterations

We've simulated the process programmers go through in implementing code, allowing AutoCoder to read existing project source code, read third-party libraries, refer to documentation, and automatically search for problem references. This enables AutoCoder to have a clear understanding of the programmer's needs, resulting in more accurate and useful code.

Additionally, we encourage programmers to use AutoCoder for quick, tiny iterations, similar to how a large PR needs to be broken down into several smaller PRs for submission.

Furthermore, we offer varying degrees of automation - from generating prompts, automatically executing prompts, to automatically merging code. This allows users to choose their level of automation for each small iteration. As each iteration is described using YAML configuration, it enables users to review their iterative process.

## Retain Sufficient Extensibility

We also provide capabilities like target analysis, demand decomposition, planning, automatic generation of process steps, and execution. However, these are only to ensure that AutoCoder's functions become automatically available as model capabilities reach a certain level, ensuring AutoCoder can always enjoy the benefits of model progress.

## Conclusion

Therefore, AutoCoder offers a significant efficiency improvement for developers compared to GitHub Copilot and, unlike Devin, is grounded in reality, providing developers with efficiency improvements and helping businesses reduce development costs, rather than being just a demo or a research product. However, we also offer competitive features to ensure that we can quickly provide more value to users as models improve.

If you're curious about AutoCoder, feel free to check out our documentation: https://github.com/allwefantasy/auto-coder/tree/master/docs