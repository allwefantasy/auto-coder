# 004-AutoCoder Code While Reading and Documenting

The core programming tasks for a programmer essentially involve:

1. Understanding requirements

2. Searching to see how others have solved similar problems to clarify one's thoughts

3. Reviewing the code of existing projects

4. Reading the source code or documentation of third-party libraries to be used

AutoCoder simulates this behavior of a program to complete code writing. Let's see how we can get AutoCoder to accomplish this task.

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
  with the corresponding REST path as /llm. This interface accepts two parameters: query and model.
  Call the llm.chat_oai method and then return the result.
  You need to refer to the previous byzer-llm documentation to complete the call to the llm.chat_oai method.
  Note that the initialization of ByzerLLM should be placed inside the new method.

```

Here, compared to before, we have added a new urls parameter, where you can specify one or more documents. Since I am preparing to add a large model service feature to our web server, I provided the byzerllm documentation to it.

Because the document is quite long, I used the human_as_model feature, which allows the use of web models with a super long window.

Now, let's open the server.py file and see that a new /llm interface has been added.

```yml


import os
import ray
from fastapi import FastAPI
from byzerllm.utils.client import ByzerLLM

# Create an instance of the FastAPI application
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

# Define the GET request handler for the root path, returning "Hello, World!"
@app.get("/")
def read_root():
    return {"message": "Hello, World!"}
    
if __name__ == "__main__":
    # Start the web service, changing the port to 9001
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9001)
```

The code is perfect, but it actually missed a statement to connect to the ByzerLLM cluster, just one line of code, which you can manually modify.

However, considering you might prefer to command large models to do the work, you can modify the query and execute it again:

```yml
...
query: >
  Modify server.py, after the line app = FastAPI(),
  add the initialization code for the ray connection.
```

At this point, it will modify the code, and you can see it correctly added the code on line 10.

```python
import os
import ray
from fastapi import FastAPI
from byzerllm.utils.client import ByzerLLM

# Create an instance of the FastAPI application
app = FastAPI()

# Initialize the ray connection
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

Alright, it's time to test our results. Start this web service:

```shell
python /tmp/t-py/server/server.py
```

Visit our /llm interface:

http://127.0.0.1:9001/llm?query=你好&model=qianwen_chat 

Response:

![](./images/image11.png)

Congratulations, you have successfully completed a large model service!

Considering the length of today's article, we will discuss how to use search engines in the next one.