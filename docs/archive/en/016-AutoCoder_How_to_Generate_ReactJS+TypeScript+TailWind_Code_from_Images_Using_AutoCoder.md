# 016-AutoCoder How to Generate ReactJS+TypeScript+TailWind Code from Images

> AutoCoder >= 0.1.58 Features

Additional installation required:

```shell
pip install playwright
playwright install
```

When is this feature useful? For example, if you have a reactjs + typescript + tailwind project and you want to reference a page from another website, you can take a screenshot and generate corresponding reactjs + typescript + tailwind code based on that image.

By default, AutoCoder will convert the image into html/tailwind format, and then use the model through query to transform it into the final form you need. So you can generate html/tailwind code only or generate reactjs + typescript + tailwind code.

## Generate HTML + Tailwind Only

Let's look at the example below:

```yml
source_dir: /Users/allwefantasy/projects/tt/
target_file: /Users/allwefantasy/projects/auto-coder/output.txt 
project_type: copilot/ts

image_file: /Users/allwefantasy/projects/auto-coder/screenshots/www_elmo_chat.png
image_mode: direct
image_max_iter: 1

model: deepseek_chat
model_max_length: 2000
model_max_input_length: 30000
anti_quota_limit: 5

vl_model: gpt4o_chat

skip_build_index: false
execute: true
auto_merge: true
human_as_model: true

query: |   
   Convert html to reactjs+typescript+tailwind implementation, and save it in the appropriate directory /Users/allwefantasy/projects/tt/.
tt is already a reactjs + typescript + tailwind project
```

/Users/allwefantasy/projects/tt/ is an existing reactjs + typescript + tailwind project. We want the new code to be generated in the appropriate directory of this project.

In this configuration file, there are a few differences compared to before:

1. Specify the webpage image address through image_file.
2. Project configuration type is: copilot/ts instead of ts.
3. Specify an additional multimodal model, which can be specified through vl_model, recommended gpt_4o.
4. Multimodal models need to be deployed by byzerllm.
5. image_max_iter can be set to the number of iterations. The more iterations, the code generated should theoretically be closer to the original image. You can also check the intermediate generated html files to see if they meet your requirements.

## Generate ReactJS + TypeScript + Tailwind

To do this, simply change one line of configuration:

```yml
project_type: ts
```

Change project_type from copilot/ts to ts, which will allow us to select related files and perform code conversion.

If you want to convert to other frameworks like vue, you just need to specify it in the query.

## Results

Finally, the generated ReactJS code looks like this:

```jsx
import React from 'react';
import tw from 'tailwind-styled-components';

const Container = tw.div`
  bg-gradient-to-b from-orange to-yellow
  text-white
  font-Arial
  flex
``````markdown
# How to Generate ReactJS+TypeScript+TailWind Code from Images

## flex-col
## items-center
## pt-50
## min-h-screen

# Elmo
Elmo ⚡

## Elmo is your AI chrome extension to create summaries, insights and extended knowledge.

<button>Install from Chrome Web Store</button>
Free • No Account Needed • Supports Multiple Languages

<div>Featured on Chrome Web Store</div>
<div>Developed by Established Publisher</div>

<p>Summaries and Bullet Points</p>
```