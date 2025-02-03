import os
from openai import OpenAI

client = OpenAI(
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key="sk-xxx",
    api_key="", # 如何获取API Key：https://help.aliyun.com/zh/model-studio/developer-reference/get-api-key
    base_url="https://qianfan.baidubce.com/v2",
)

completion = client.chat.completions.create(
    model="deepseek-r1", 
    messages=[        
        {'role': 'user', 'content': '你是谁？'}
        ]
)
print(completion.choices[0].message.content)