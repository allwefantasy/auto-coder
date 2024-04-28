import io
import os
import queue
import threading
import byzerllm
import time
import json
import base64
from concurrent.futures import ThreadPoolExecutor
import shutil

def play_wave(filename:str):
    try:
        import simpleaudio as sa
    except ImportError:
        raise ImportError("The simpleaudio module is required to play audio files. Try running 'pip install simpleaudio'")

    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()

class PlayStreamAudioFromText:
    def __init__(self, tts_model_name:str="openai_tts"):
        self.q = queue.Queue()
        self.pool = ThreadPoolExecutor(max_workers=5)
        self.llm = byzerllm.ByzerLLM()
        self.llm.setup_default_model_name(tts_model_name)
        self.wav_num = -1

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
        self.q.task_done()

    def play_audio_files(self):
        idx = 1
        while True:
            if self.wav_num == -2:
                break
            file_path = f"/tmp/wavs/{idx:03d}.wav"
            if not os.path.exists(file_path):
                time.sleep(0.1) # Reduce CPU usage
                continue
            play_wave(file_path)
            idx += 1
            if idx > self.wav_num:
                self.wav_num = -2

    def process_texts(self):
        idx = 1
        s = ""
        while True:
            text = self.q.get()
            if text is None:
                self.q.task_done()
                break
            s += text
            if len(s) < 10:
                continue
            sentences = s.split("。")
            for sentence in sentences:
                if len(sentence) == 0:
                    continue
                file_path = f"/tmp/wavs/{idx:03d}.wav"
                print(f"Processing: {sentence} to {file_path}")
                self.pool.submit(self.text_to_speech, sentence, file_path)
                idx += 1
            s = ""
        self.wav_num = idx - 1

    def run(self, text_generator):
        os.makedirs("/tmp/wavs", exist_ok=True)
        threading.Thread(target=self.play_audio_files).start()
        threading.Thread(target=self.process_texts)._start()
        for text in text_generator:
            self.q.put(text)
        self.q.put(None)
        while self.wav_num != -2:
            time.sleep(0.1)