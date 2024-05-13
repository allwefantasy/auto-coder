# 025-AutoCoder knowledge base writing code in two context modes

We have mentioned in [019-AutoCoder Automatically Builds Index for Local Documents](./019-AutoCoder%E5%AF%B9%E6%9C%AC%E5%9C%B0%E6%96%87%E6%A1%A3%E8%87%AA%E5%8A%A8%E6%9E%84%E5%BB%BA%E7%B4%A2%E5%BC%95.md)
how to build an RAG index with just two commands, and also in [022-AutoCoder Supports Multiple Knowledge Bases.md](./022-AutoCoder%E5%A4%9A%E7%9F%A5%E8%AF%86%E5%BA%93%E6%94%AF%E6%8C%81.md)
it mentioned support for multiple knowledge bases.

However, for the content of the recall, how to provide references to large models, in fact AutoCoder provides two context modes:

1. enable_rag_context
2. enable_rag_search

## enable_rag_context

enable_rag_context takes the article corresponding to the first chunk as the context, and this context is provided to the large model as a normal file.

## enable_rag_search

enable_rag_search answers the top N chunks according to the question, and the answer result is provided to the large model as the context, which is also provided to the large model as a normal file.

## Best Practices

Both enable_rag_context/enable_rag_search parameters support bool or string parameters. We recommend using string parameters. For example:

```yml
enable_rag_search: | 
   byzerllm  Python code using the openai_tts model
collections: byzerllm

query: | 
   We want to implement a new class called PlayStreamAudioFromText in audio.py,
   which has a method run,
   the input of this method is a string generator, and the text will be converted into speech and played.
   
   Specific logic is:
   1. PlayStreamAudioFromText maintains a queue and a thread pool
   1. At runtime, read text from the generator, and then put the text into the queue
   2. Take the text from the queue, split the sentences by Chinese and English periods or line breaks,
      and call the openai_tts model in parallel to convert the text into speech, save it in the /tmp/wavs directory.
      The audio files are saved in a directory with the naming rule of 001.wav, 002.wav, 003.wav...
   3. Use a separate thread to play the audio files, play the next audio file after playing one audio file, until all the audio files are played.
```

If enable_rag_search is set to a bool value (true), then AutoCoder will search for information in the specified byzerllm knowledge base with the query as the question. However, the actual effect may be very poor.
In the example above, we directly tell RAG that I need you to search for the code of "byzerllm Python code using the openai_tts model", then it will give me a complete sample code, which will be provided as context, together with your query, to the large model.

Below is the code generated from the example above:

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
``````python
shutil.move(temp_file_path, file_path)
print(f"Converted successfully: {file_path}")
```

The big model itself didn't know the specific implementation of the openai_tts model, but through the example code retrieved by RAG, he eventually figured out how to call the openai_tts model and wrote very beautiful code.