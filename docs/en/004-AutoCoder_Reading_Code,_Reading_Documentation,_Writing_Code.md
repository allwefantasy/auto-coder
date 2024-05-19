# 004-AutoCoder Coding while Reading Code and Documentation

For programmers, the coding process is simply:

1. Understanding requirements
2. Searching for how others have solved similar problems, and clarifying ideas
3. Reading existing project code
4. Reading the source code or documentation of third-party libraries to be used

AutoCoder simulates this behavior of a programmer to complete the coding process. Let's see how AutoCoder accomplishes this specifically.

```yml
source_dir: /tmp/t-py
target_file: /home/winubuntu/projects/ByzerRawCopilot/output.txt 

model: qianwen_chat
model_max_length: 2000
model_max_input_length: 100000
anti_quota_limit: 5

execute: true
auto_merge: true

project_type: py

human_as_model: true

urls: >
  https://raw.githubusercontent.com/allwefantasy/byzer-llm/master/README.md

query: >
  Add a new method before the read_root method,
  corresponding to the REST path /llm. This interface accepts two parameters: query and model.
  Call the llm.chat_oai method and then return the result.
  You need to refer to the documentation of byzer-llm to complete the call to llm.chat_oai method.
  Note that the initialization of ByzerLLM should be placed in the new method.

```

Here, compared to before, we have added a new parameter called urls, where you can specify one or multiple documents. I am planning to add a large model service feature to our web server, so I provided the documentation of byzerllm to it.

In addition, urls also support the YAML array format, making it easy for you to specify multiple documents:

```yml
urls:
  - https://raw.githubusercontent.com/allwefantasy/byzer-llm/master/README.md
  - /tmp/t-py/README.md
```

Note that urls support both REST and local path formats, and support multiple text formats such as PDF, Word, txt, md, etc.

Here, because the document is quite long, I used the human_as_model feature, allowing the use of web models with extremely long windows.

Now, if we open the server.py file, we can see a new /llm interface has been added.

```yml
import os
import ray
from fastapi import FastAPI
from byzerllm.utils.client import ByzerLLM

# Create a FastAPI application instance
app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "world"}

@app.get("/llm")
def llm_chat(query: str, model: str):
    llm = ByzerLLM()
    llm.setup_default_model_name(model)

    result = llm.chat_oai(conversations=[{
        "role": "user",
        "content": query
    }])

    return {"response": result[0].output}

# Define the GET request handling function for the root path, returning "Hello, World!"
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
    
if __name__ == "__main__":
    # Start the web service, changing the port to 9001
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9001)
```

The code is perfect, but it actually missed a line of code to connect to the ByzerLLM cluster, just one line, you can manually add it.

However, considering that you might prefer to command the large model to do the work, you can modify the query and then execute it again:

```yml
...
query: >
  Modify server.py, after the code app = FastAPI(),
  add the ray initialization connection code.
```At this point, he will start modifying the code, and you can see that he correctly added code on line 10.

```python
import os
import ray
from fastapi import FastAPI
from byzerllm.utils.client import ByzerLLM

# Create FastAPI application instance
app = FastAPI()

# Initialize ray connection
ray.init(address="auto", namespace="default", ignore_reinit_error=True)

@app.get("/hello")
def hello():
    return {"message": "world"}

@app.get("/llm")
def llm_chat(query: str, model: str):
    llm = ByzerLLM()
    llm.setup_default_model_name(model)

    result = llm.chat_oai(conversations=[{
        "role": "user",
        "content": query
```

Alright, it's time to test the results. Start this web service:

```shell
python /tmp/t-py/server/server.py
```

Access our /llm endpoint:

http://127.0.0.1:9001/llm?query=Hello&model=qianwen_chat

Returns:

![](../images/image11.png)

Congratulations, you have successfully completed a large model service!

Considering that today's article is lengthy, we will cover how to use search engines in the next article.