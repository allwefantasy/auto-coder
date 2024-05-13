# 025-AutoCoder知识库写代码的两种上下文模式

我们在 [019-AutoCoder对本地文档自动构建索引](./019-AutoCoder%E5%AF%B9%E6%9C%AC%E5%9C%B0%E6%96%87%E6%A1%A3%E8%87%AA%E5%8A%A8%E6%9E%84%E5%BB%BA%E7%B4%A2%E5%BC%95.md) 提及了
如何两条命令就构建好一个RAG索引，也在 [022-AutoCoder多知识库支持.md](./022-AutoCoder%E5%A4%9A%E7%9F%A5%E8%AF%86%E5%BA%93%E6%94%AF%E6%8C%81.md)
提及了多知识库的支持。

但是对于召回的内容，如何给到大模型参考，实际上  AutoCoder 提供了两种上下文模式：

1. enable_rag_context
2. enable_rag_search

## enable_rag_context

enable_rag_context 会取第一个chunk 对应的文章，作为上下文，这个上下文会被作为一个普通的文件给到大模型。

## enable_rag_search

enable_rag_search 会对 topN 个chunk 根据问题进行回答，把回答结果作为上下文，这个上下文也会被作为一个普通的文件给到大模型。


## 最佳使用实践

enable_rag_context/enable_rag_search 两个参数都支持 bool 或者字符串参数。我们推荐使用字符串参数。比如：

```yml
enable_rag_search: | 
   byzerllm  使用 openai_tts模型的 python 代码
collections: byzerllm

query: | 
   我们要在 audio.py 中实现一个新的类叫 PlayStreamAudioFromText，
   该类有一个方法 run,
   该方法输入是一个字符串generator，在方法内部会将文本转换为语音，并且播放出来。
   
   具体逻辑是：
   1. PlayStreamAudioFromText 维护一个queue，一个线程池
   1. 运行时，从generator中读取文本，然后将文本放入queue中
   2. 从queue中取出文本，按中英文句号或者换行符对语句进行切割调用，
      并行调用 openai_tts 模型将文本转换为语音，保存在 /tmp/wavs 目录下。
      音频文件用 001.wav, 002.wav, 003.wav...的命名规则保存在一个目录下.
   3. 使用一个独立的线程播放音频文件，播放完一个音频文件后，再播放下一个音频文件，直到播放完毕。   
```

如果 enable_rag_search 被设置为 bool 值(true),那么 AutoCoder 会把 query 作为问题，到指定的 byzerllm 知识库中检索信息。但实际效果可能非常差。
在上面的示例中，我们直接明确的告诉RAG，我需要你检索 "byzerllm  使用 openai_tts模型的 python 代码" 的代码，然后他会给我一个完整的示例代码，然后这个
示例代码会被作为上下文，配合你的 query, 一起给到大模型。

下面是上面示例生成一段代码:

```python
def text_to_speech(self, text, file_path):
        print(f"Converting text to speech: {text}")
        t = self.llm.chat_oai(conversations=[{
            "role":"user",
            "content": json.dumps({
                "input": text,
                "voice": "echo",
                "response_format": "wav"
            }, ensure_ascii=False)
        }])
        temp_file_path = file_path + ".tmp"
        with open(temp_file_path, "wb") as f:
            f.write(base64.b64decode(t[0].output))
        shutil.move(temp_file_path, file_path)
        print(f"Converted successfully: {file_path}") 
```

大模型自身兵不知道 openai_tts 模型的具体实现，但是通过RAG检索给到的示例代码，他最后知道如何调用 openai_tts 模型，并且写出了很漂亮的代码。

