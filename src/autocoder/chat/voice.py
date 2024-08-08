from prompt_toolkit import PromptSession
import pyaudio
import wave
import threading
import byzerllm
import base64
import json
import tempfile
import os

def record_audio(filename, duration=5):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("* 录音中...")

    frames = []

    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* 录音结束")

    stream.stop_stream()
    stream.close()
    p.terminate()

    wf = wave.open(filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

def transcribe_audio(filename, llm):
    with open(filename, "rb") as audio_file:
        audio_content = audio_file.read()
    
    base64_audio = base64.b64encode(audio_content).decode('utf-8')
    
    conversations = [{
        "role": "user",
        "content": json.dumps({
            "audio": base64_audio,
        })
    }]

    response = llm.chat_oai(conversations=conversations)
    transcription = json.loads(response[0].output)["text"]
    return transcription

def voice_input_handler(session: PromptSession, llm):
    print("开始录音，请说话...")
    
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
        temp_filename = temp_wav.name
    
    try:
        record_audio(temp_filename)
        print("录音结束，正在识别...")
        transcription = transcribe_audio(temp_filename, llm)
        print(f"识别结果: {transcription}")
        session.default_buffer.insert_text(transcription)
    finally:
        # 确保临时文件被删除
        os.unlink(temp_filename)