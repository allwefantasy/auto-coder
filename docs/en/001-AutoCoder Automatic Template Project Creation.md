# 001-AutoCoder Automatic Template Project Creation

The AutoCoder series tutorial begins. As programmers, we should start by creating a project. AutoCoder provides the ability to automatically create projects.

However, it's important to note that because each model's capabilities are different, and even the same model may not provide stable answers every time, this part of the function is not stable. Here, we still recommend using Qwen-Max to complete the following tasks.

## Practical Exercise One: Create a Python Project

In fact, many people don't know how to create a standard Python project that complies with pip specifications, and they usually need to search on Google. Using AutoCoder is a great start.

Our goal for this practical exercise: Create a pip-compliant Python project named t-py in the /tmp directory, noting that there is no need to create a conda/venv environment.

How can we let AutoCoder automatically complete this task? Create a new file named 001_create_python_project.yml with the following content:

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
  Create a pip-compliant Python project named t-py in the /tmp directory, noting that there is no need to create a conda/venv environment.
```

Here, you need to manually create the /tmp/t-py directory first because the source_dir is a required field. Execute this file:

```bash
auto-coder --file ./examples/from-zero-to-hero/001_create_python_project.yml
```

At this point, the system outputs as follows:

```text
Intent: UserIntent.CREATE_NEW_PROJECT
try to get the total steps...
total steps to finish the user's question: 5
=============================Collect AUTO STEPS===========================================
user: 
You are familiar with various programming languages and their corresponding project structures. Now, you need
to decompose the question based on the user's problem and the provided information, then generate execution steps. When all steps are executed, ultimately help to generate a project structure that complies with the corresponding programming language specifications and related frameworks.
The entire process can only use python/shell.

Now please refer to the following content:

Based on the user's question, creating a pip-compliant Python project does not require creating a conda/virtualenv environment, but it does require initializing the project structure, including setup.py, requirements.txt, and the project directory structure. Here are the detailed execution steps:

1. **Create the project directory**:
   \```bash
   mkdir /tmp/t-py
   cd /tmp/t-py
   \```

2. **Create the project folder structure**:
   Create a directory named `t_py` (assuming this is your actual Python package name) and a `src` directory under `/tmp/t-py`, as well as other potentially needed directories like `tests`.
   \```bash
   mkdir t_py
   mkdir -p src/t_py
   mkdir tests
   \```

3. **Create an `__init__.py` file under `src/t_py`**:
   \```bash
   touch src/t_py/__init__.py
   \```
   This file is necessary to identify the directory as a Python package.

4. **Create a `setup.py` file**:
   Create a `setup.py` file in the root directory of `/tmp/t-py` to define project information and dependencies:
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
   Please modify the project information in the above `setup.py` according to the actual situation.

5. **Create a `requirements.txt` file**:
   Create a `requirements.txt` file in the root directory of `/tmp/t-py` to list the required dependency packages for the project:
   \```bash
   touch requirements.txt
   \```
   If there are specific dependency packages, you can open this file and add their version numbers, for example:
   \```
   numpy==1.23.0
   pandas==1.4.3
   \```

A total of 5 steps.

Each time an execution step is generated, ask me if you want to continue. When I reply "continue," proceed to generate the next execution step.

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
Please confirm whether this step has been executed and are you ready to continue?

user: continue

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
Please confirm whether this step has been executed and are you ready to continue?

user: continue

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
Please confirm whether this step has been executed and are you ready to continue?

user: continue

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
Please confirm whether this step has been executed and are you ready to continue?

user: continue

assistant: \```json
{
  "current_step": 5,
  "total_steps": 5,
  "code": "cat << EOF > setup.py\nfrom setuptools import setup, find_packages\n\nwith open(\"README.md\", \"r\") as fh:\n    long_description = fh.read()\n\nsetup(\n    name=\"t-py\",\n    version=\"0.0.1\",\n    author=\"Your Name\",\n    author_email=\"your.email@example.com\",\n    description=\"A brief description of your project\",\n    long_description=long_description,\n    long_description_content_type=\"text/markdown\",\n    url=\"https://github.com/yourusername/t-py\",\n     packages=find_packages(where=\"src\"),\n    package_dir={\"\": \"src\"},\n    classifiers=[\n        \"Programming Language :: Python :: 3\",\n        \"License :: OSI Approved :: MIT License\",\n        \"Operating System :: OS Independent\",\n    ],\n    python_requires='>=3.6',\n)\nEOF",
  "lang": "shell",
  "cwd": "/tmp/t-py",
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
Please confirm whether this step has been executed and are you ready to continue?

user: continue

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

The automatically created project directory is as follows:

![](./images/image2.png)

Note that due to the variability and probabilistic nature of the model, your final result may differ slightly from mine. But overall, it is able to correctly create the corresponding directory structure.

## Case 2, Create a Front-end Project

If you want the results to be reliably reproducible, you can try enabling search support. Since AutoCoder currently only supports Bing and Google, it is recommended to use Bing. You can apply for a free Token here: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api to use Bing's API.

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
  Help me create a project composed of typescript + reactjs in the /tmp/ directory, named t-project

```

You need to manually create the t-project directory first, or any empty directory, as the source_dir is a required configuration.

Now you can execute:

```bash

auto-coder --file ./examples/from-zero-to-hero/001_create_python_project.yml
```

The output is as follows:

```text
Intent: UserIntent.CREATE_NEW_PROJECT
search SearchEngine.BING for Help me create a project composed of typescript + reactjs in the /tmp/ directory, named t-project...
reraking the search result by snippets...
etch https://blog.csdn.net/weixin_42429718/article/details/117402097  and answer the quesion (Help me create a project composed of typescript + reactjs in the /tmp/ directory, named t-project) based on the full content...
try to get the total steps...
total steps to finish the user's question: 2
=============================Collect AUTO STEPS===========================================
user: 
You are familiar with various programming languages and their corresponding project structures. Now, you need
to decompose the question based on the user's problem and the provided information, then generate execution steps. When all steps are executed, ultimately help to generate a project structure that complies with the corresponding programming language specifications and related frameworks.
The entire process can only use python/shell.

Now please refer to the following content:

Based on the user's question, here are the detailed execution steps:

The task is divided into two steps.

\**Step 1: Globally install Create React App**

\```bash
# Use npm to globally install Create React App
npm install -g create-react-app

# Or, if you have yarn configured in your system, use yarn to globally install
yarn global add create-react-app
\```

\**Step 2: Create a TypeScript + ReactJS project named t-project in the /tmp/ directory**

\```bash
# First, ensure you are in the /tmp/ directory
cd /tmp/

# Use npx to create a new project and specify the TypeScript template
npx create-react-app t-project --template typescript

# Or, if you are accustomed to using yarn for package management
yarn create react-app t-project --template typescript
\```

After completing these steps, you will have a React project named `t-project` integrated with TypeScript support in the `/tmp/` directory.

Each time an execution step is generated, ask me if you want to continue. When I reply "continue," proceed to generate the next execution step.

assistant: \```json
{
  "current_step": 1,
  "total_steps": 2,
  "code": "# Use npm to globally install Create React App\nnpm install -g create-react-app",
  "lang": "shell",
  "cwd": null,
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
Please confirm whether you have successfully executed the first step (globally installing Create React App). If completed, please reply "continue," and I will generate the next execution step for you.

user: continue

assistant: \```json
{
  "current_step": 2,
  "total_steps": 2,
  "code": "# First, ensure you are in the /tmp/ directory\ncd /tmp/\n\n# Use npx to create a new project and specify the TypeScript template\nnpx create-react-app t-project --template typescript",
  "lang": "shell",
  "cwd": "/tmp/",
  "env": null,
  "timeout": null,
  "ignore_error": false
}
\```
Please confirm that you have successfully executed the previous step and are now in the `/tmp/` directory. If completed, please reply "continue," and I will generate the last execution step to create a TypeScript + ReactJS project named `t-project`.

user: continue

Shell Command:
\# Use npm to globally install Create React App
npm install -g create-react-app
Output:

--------------------
Shell Command:
\# First, ensure you are in the /tmp/ directory
cd /tmp/

\# Use npx to create a new project and specify the TypeScript template
npx create-react-app t-project --template typescript
Output:

\--------------------
```

It can be seen that AutoCoder automatically searches for articles and found a blog post on CSDN: https://blog.csdn.net/weixin_42429718/article/details/117402097 which seems quite good, so it adopted its solution as a reference, and finally produced specific execution steps.

The final generated directory:

![](./images/image3.png)

Of course, if you find a suitable article yourself, you can also configure it through the urls parameter, so AutoCoder can complete the project creation by referring to the articles you provide.

## Summary

In fact, the above generation effect is not very ideal. For example, it does not check whether you have the corresponding environment. For instance, is npm not installed? So many people may fail when executing. With the continuous improvement of the model's capabilities, including the more intelligent search engines we will introduce later, I believe these issues will be resolved soon.

In the next issue 002, we can start working on the code!