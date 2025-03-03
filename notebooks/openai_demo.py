from openai import OpenAI

client = OpenAI(api_key="xxxx", base_url="http://127.0.0.1:8106/v1")

response = client.chat.completions.create(
    messages=[{
        "role": "user",
        "content": "auto-coder是啥"
    }],
    stream=True,
    model="v_r1_chat",
    extra_body={
        "extra_body": {
            "jack": "123"
        }
    }
)

for chunk in response:
    print(chunk.choices[0].delta.content,end="",flush=True)
