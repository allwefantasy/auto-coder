from openai import OpenAI, AsyncOpenAI
import inspect
import asyncio
from autocoder.utils.stream_thinking import print_streaming_response_async

# client = OpenAI(api_key="xxxx", base_url="http://127.0.0.1:8106/v1")

client2 = AsyncOpenAI(api_key="xxxx", base_url="http://127.0.0.1:8106/v1")

# response = client.chat.completions.create(
#     messages=[{
#         "role": "user",
#         "content": "auto-coder是啥"
#     }],
#     stream=True,
#     model="v_r1_chat",
#     extra_body={
#         "extra_body": {
#             "jack": "123"
#         }
#     }
# )


async def print_streaming_response():
    response = await client2.chat.completions.create(
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

    await print_streaming_response_async(response)


def main():
    asyncio.run(print_streaming_response())


if __name__ == "__main__":
    main()

# 使用示例：
# print_streaming_response(response)

# 如果是异步环境，则使用：
# import asyncio
# asyncio.run(print_streaming_response_async(response))
