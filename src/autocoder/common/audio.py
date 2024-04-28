import io
import os
import queue
import threading
import byzerllm
import time

def play_mp3(path):
    try:
        import pygame
    except ImportError:
        raise ImportError("The pygame module is required to play audio files. Try running 'pip install pygame'")

    # Initialize the mixer module
    pygame.mixer.init()

    # Load the MP3 file 
    pygame.mixer.music.load(path)
    
    # Start playing the music
    pygame.mixer.music.play()

    # Wait for the music to finish playing
    while pygame.mixer.music.get_busy():
        time.sleep(1)

def play_wave(filename:str):  
    try:
        import simpleaudio as sa
    except ImportError:
        raise ImportError("The simpleaudio module is required to play audio files. Try running 'pip install simpleaudio'")
        
    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()
        
        
class PlayStreamAudioFromText:
    def __init__(self):
        self.q = queue.Queue()
        self.pool = byzerllm.ThreadPoolExecutor(max_workers=5)
        byzerllm.connect_cluster()
        self.llm = byzerllm.ByzerLLM()
        self.llm.setup_default_model_name("open_tts")
        
    def text_to_speech(self, text, file_path):
        t = self.llm.chat_oai(conversations=[{ 
            "role":"user",
            "content": json.dumps({
                "input": text,
                "voice": "alloy",
                "response_format": "wav" 
            }, ensure_ascii=False)
        }])
        
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(t[0].output))

    def play_audio_files(self):
        idx = 1
        while True:
            file_path = f"/tmp/wavs/{idx:03d}.wav"
            if not os.path.exists(file_path):
                time.sleep(0.1)
                continue
            play_wave(file_path)
            idx += 1
            
    def process_texts(self):
        idx = 1
        while True:
            text = self.q.get()
            if text is None:
                break
            sentences = text.split("。")
            for sentence in sentences:
                file_path = f"/tmp/wavs/{idx:03d}.wav"
                self.pool.submit(self.text_to_speech, sentence, file_path)
                idx += 1
            self.q.task_done()
        
    def run(self, text_generator):
        os.makedirs("/tmp/wavs", exist_ok=True)
        
        threading.Thread(target=self.play_audio_files).start()
        threading.Thread(target=self.process_texts).start()
        
        for text in text_generator:
            self.q.put(text)
            
        self.q.put(None)
        self.q.join()