# 001-AutoCoder自动创建模板项目

AutoCoder 系列教程开始了。作为程序员，那得先从创建一个项目开始。AutoCoder 提供了一个自动化创建项目的能力。

不过这里大家要注意的是，因为每个模型能力不一样，甚至同一个模型每次给的答案都不一定稳定，所以这部分功能并不能稳定。这里我们依然推荐 Qwen-Max 来完成下面的工作。

## 实战一，创建一个Python项目

实际上创建一个标准的符合 pip 规范的python项目，很多人并不会，一般可能都需要google下。这里用 AutoCoder 就是很好的开始。

我们实战一的目标: 在 /tmp 目录下，创建一个符合 pip 标准的 python项目 t-py,注意不需要创建conda/venv环境。

那如何让 AutoCoder 自动完成这个事情？新建一个 001_create_python_project.yml,内容如下：

```yml

source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5
execute: true

project_type: "copilot/.py"

query: |
  在 /tmp 目录下，创建一个符合 pip 标准的 python项目 t-py,注意不需要创建conda/venv环境
```

这里，你需要手动创建下 /tmp/t-py 目录，因为 source_dir 是必须要求的。执行下这个文件：

```bash
auto-coder --file ./examples/from-zero-to-hero/001_create_python_project.yml
```

这个时候系统输出如下：

```text
Intent: UserIntent.CREATE_NEW_PROJECT
try to get the total steps...
total steps to finish the user's question: 5
=============================Collect AUTO STEPS===========================================
user: 
你熟悉各种编程语言以及相关框架对应的项目结构。现在，你需要
根据用户的问题，根据提供的信息，对问题进行拆解，然后生成执行步骤，当执行完所有步骤，最终帮生成一个符合对应编程语言规范以及相关框架的项目结构。
整个过程只能使用 python/shell。

现在请参考下面内容：

根据用户的问题，创建一个符合 pip 标准的 Python 项目不需要创建 conda/virtualenv 环境，但需要初始化项目结构，包括 setup.py、requirements.txt 和项目的目录结构。以下是详细的执行步骤：

1. **创建项目目录**：
   \```bash
   mkdir /tmp/t-py
   cd /tmp/t-py
   \```

2. **创建项目文件夹结构**：
   在 `/tmp/t-py` 下创建 `t_py`（假设这是你的实际Python包名称）目录和 `src` 目录，以及其他可能需要的如 `tests` 目录等。
   \```bash
   mkdir t_py
   mkdir -p src/t_py
   mkdir tests
   \```

3. **在 `src/t_py` 下创建一个 __init__.py 文件**：
   \```bash
   touch src/t_py/__init__.py
   \```
   这个文件是标识该目录为 Python 包所必需的。

4. **创建 setup.py 文件**：
   在 `/tmp/t-py` 根目录下创建一个 `setup.py` 文件，用于定义项目信息及依赖项：
   \```bash
   cat << EOF > setup.py
   from setuptools import setup, find_packages

   with open("README.md", "r") as fh:
       long_description = fh.read()

   setup(
       name="t-py",
       version="0.0.1",
       author="Your Name",
       author_email="your.email@example.com",
       description="A brief description of your project",
       long_description=long_description,
       long_description_content_type="text/markdown",
       url="https://github.com/yourusername/t-py",
       packages=find_packages(where="src"),
       package_dir={"": "src"},
       classifiers=[
           "Programming Language :: Python :: 3",
           "License :: OSI Approved :: MIT License",
           "Operating System :: OS Independent",
       ],
       python_requires='>=3.6',
   )
   EOF
   \```
   请根据实际情况修改上述 `setup.py` 中的项目信息。

5. **创建 requirements.txt 文件**：
   在 `/tmp/t-py` 根目录下创建一个 `requirements.txt` 文件，列出项目所需的依赖包：
   \```bash
   touch requirements.txt
   \```
   如果有具体的依赖包，可以打开此文件并添加它们的版本号，例如：
   \```
   numpy==1.23.0
   pandas==1.4.3
   \```

总计共5步。

每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。

assistant: \```json
{
  "current_step": 1,
  "total_steps": 5,
  "code": "mkdir /tmp/t-py",
  "lang": "shell",
  "cwd": null,
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
请确认是否已执行此步骤并准备继续？

user: 继续

assistant: \```json
{
  "current_step": 2,
  "total_steps": 5,
  "code": "cd /tmp/t-py",
  "lang": "shell",
  "cwd": null,
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
请确认是否已执行此步骤并准备继续？

user: 继续

assistant: \```json
{
  "current_step": 3,
  "total_steps": 5,
  "code": "mkdir t_py\nmkdir -p src/t_py\nmkdir tests",
  "lang": "shell",
  "cwd": "/tmp/t-py",
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
请确认是否已执行此步骤并准备继续？

user: 继续

assistant: \```json
{
  "current_step": 4,
  "total_steps": 5,
  "code": "touch src/t_py/__init__.py",
  "lang": "shell",
  "cwd": "/tmp/t-py",
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
请确认是否已执行此步骤并准备继续？

user: 继续

assistant: \```json
{
  "current_step": 5,
  "total_steps": 5,
  "code": "cat << EOF > setup.py\nfrom setuptools import setup, find_packages\n\nwith open(\"README.md\", \"r\") as fh:\n    long_description = fh.read()\n\nsetup(\n    name=\"t-py\",\n    version=\"0.0.1\",\n    author=\"Your Name\",\n    author_email=\"your.email@example.com\",\n    description=\"A brief description of your project\",\n    long_description=long_description,\n    long_description_content_type=\"text/markdown\",\n    url=\"https://github.com/yourusername/t-py\",\n    packages=find_packages(where=\"src\"),\n    package_dir={\"\": \"src\"},\n    classifiers=[\n        \"Programming Language :: Python :: 3\",\n        \"License :: OSI Approved :: MIT License\",\n        \"Operating System :: OS Independent\",\n    ],\n    python_requires='>=3.6',\n)\nEOF",
  "lang": "shell",
  "cwd": "/tmp/t-py",
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
请确认是否已执行此步骤并准备继续？

user: 继续

Shell Command:
mkdir /tmp/t-py
Output:

Error: mkdir: cannot create directory ‘/tmp/t-py’: File exists

--------------------
Shell Command:
cd /tmp/t-py
Output:

--------------------
Shell Command:
mkdir t_py
mkdir -p src/t_py
mkdir tests
Output:

--------------------
Shell Command:
touch src/t_py/__init__.py
Output:

--------------------
Shell Command:
cat << EOF > setup.py
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="t-py",
    version="0.0.1",
    author="Your Name",
    author_email="your.email@example.com",
    description="A brief description of your project",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/t-py",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
EOF
Output:

--------------------
```

自动创建项目的目录如下：

![](./images/image2.png)

注意，因为模型的差异性以及概率性，你最后的结果可能和我略有区别。但整体而言，是能够正确创建对应的目录结构的。

## Case2，创建一个前端项目

如果希望结果能够稳定重现，大家可以尝试开启搜索支持。因为目前 AutoCoder 仅支持 Bing 和 Google, 所以推荐大家使用 Bing, 可以到这里  https://www.microsoft.com/en-us/bing/apis/bing-web-search-api 申请一个免费的 Token,从而可以使用 Bing的API。

```yml

source_dir: /tmp/t-project
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 6000
anti_quota_limit: 5
execute: true

search_engine: bing
search_engine_token: ENV {{BING_SEARCH_TOKEN}}

project_type: "copilot/.ts,.jsx"
query: |
  帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project

```

你需要手动线创建下 t-project 目录，或者任何一个空目录，source_dir 是必须配置的目录。

现在可以执行了：

```bash

auto-coder --file ./examples/from-zero-to-hero/001_create_python_project.yml
```

输出如下：

```text
Intent: UserIntent.CREATE_NEW_PROJECT
search SearchEngine.BING for 帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project...
reraking the search result by snippets...
etch https://blog.csdn.net/weixin_42429718/article/details/117402097 and answer the quesion (帮我在/tmp/目录下创建一个 typescript + reactjs 组成的项目，项目名字叫 t-project) based on the full content...
try to get the total steps...
total steps to finish the user's question: 2
=============================Collect AUTO STEPS===========================================
user: 
你熟悉各种编程语言以及相关框架对应的项目结构。现在，你需要
根据用户的问题，根据提供的信息，对问题进行拆解，然后生成执行步骤，当执行完所有步骤，最终帮生成一个符合对应编程语言规范以及相关框架的项目结构。
整个过程只能使用 python/shell。

现在请参考下面内容：

根据用户的问题，以下是详细的执行步骤：

总共分为两步来完成。

\**步骤 1：全局安装Create React App**

\```bash
# 使用npm全局安装Create React App
npm install -g create-react-app

# 或者，如果你的系统中已经配置了yarn，使用yarn全局安装
\yarn global add create-react-app
```

\**步骤 2：在 /tmp/ 目录下创建名为 t-project 的 TypeScript + ReactJS 项目**

```bash
# 首先，确保你位于 /tmp/ 目录下
cd /tmp/

# 使用npx创建新项目，并指定TypeScript模板
npx create-react-app t-project --template typescript

# 或者，如果你习惯使用yarn进行包管理
yarn create react-app t-project --template typescript
```

以上步骤完成后，你将在 `/tmp/` 目录下得到一个名为 `t-project` 的React项目，该项目已集成TypeScript支持。

每次生成一个执行步骤，然后询问我是否继续，当我回复继续，继续生成下一个执行步骤。

assistant: \```json
{
  "current_step": 1,
  "total_steps": 2,
  "code": "# 使用npm全局安装Create React App\nnpm install -g create-react-app",
  "lang": "shell",
  "cwd": null,
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```

请确认，是否已成功执行了第一步（全局安装Create React App），如果完成，请回复“继续”，我将为您生成下一个执行步骤。

user: 继续

assistant: \```json
{
  "current_step": 2,
  "total_steps": 2,
  "code": "# 首先，确保你位于 /tmp/ 目录下\ncd /tmp/\n\n# 使用npx创建新项目，并指定TypeScript模板\nnpx create-react-app t-project --template typescript",
  "lang": "shell",
  "cwd": "/tmp/",
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```

请确认您已成功执行了上一步并现在位于 `/tmp/` 目录下。如果完成，请回复“继续”，我将为您生成最后一个执行步骤来创建名为 `t-project` 的 TypeScript + ReactJS 项目。

user: 继续

Shell Command:
\# 使用npm全局安装Create React App
npm install -g create-react-app
Output:

--------------------
Shell Command:
\# 首先，确保你位于 /tmp/ 目录下
cd /tmp/

\# 使用npx创建新项目，并指定TypeScript模板
npx create-react-app t-project --template typescript
Output:

--------------------
```

可以看到，AutoCoder 会自动搜索文章，并且找到了 CSDN的一篇博文：https://blog.csdn.net/weixin_42429718/article/details/117402097 觉得很不错，所以采用了他的方案作为参考，最后产生具体的执行步骤。

最后生成的目录：

![](./images/image3.png)

当然了，如果你自己找到合适的文章，也可以通过 urls 参数配置，那么AutoCoder 就可以通过参考你给的文章来完成项目的创建了。

## 总结

实际上，上面的生成效果并没有很理想。比如没有检测你是否具有相应的环境。比如是不是npm 没有安装？ 所以很多人执行可能会失败。随着模型能力的不断提升，包括后续我们会介入更加智能的搜索引擎，我相信这些很快会解决。

下一期 002, 我们可以开始着手代码了！ 