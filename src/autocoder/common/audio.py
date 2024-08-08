import os
import queue
import threading
import byzerllm
import time
import json
import base64
from concurrent.futures import ThreadPoolExecutor
import shutil

from prompt_toolkit import PromptSession
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
import numpy as np
import wave
import tempfile
import os
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from typing import Optional
from prompt_toolkit.shortcuts import confirm


def play_wave(filename: str):
    try:
        import simpleaudio as sa
    except ImportError:
        raise ImportError(
            "The simpleaudio module is required to play audio files. Try running 'pip install simpleaudio'"
        )

    wave_obj = sa.WaveObject.from_wave_file(filename)
    play_obj = wave_obj.play()
    play_obj.wait_done()


class PlayStreamAudioFromText:
    def __init__(self, tts_model_name: str = "openai_tts"):
        self.q = queue.Queue()
        self.pool = ThreadPoolExecutor(max_workers=5)
        self.llm = byzerllm.ByzerLLM()
        self.llm.setup_default_model_name(tts_model_name)
        self.wav_num = -1
        self.tempdir = tempfile.mkdtemp()

    def text_to_speech(self, text, file_path):
        print(f"Converting text to speech: {text}")
        t = self.llm.chat_oai(
            conversations=[
                {
                    "role": "user",
                    "content": json.dumps(
                        {"input": text, "voice": "echo", "response_format": "wav"},
                        ensure_ascii=False,
                    ),
                }
            ]
        )
        temp_file_path = file_path + ".tmp"
        with open(temp_file_path, "wb") as f:
            f.write(base64.b64decode(t[0].output))
        shutil.move(temp_file_path, file_path)
        print(f"Converted successfully: {file_path}")

    def play_audio_files(self):
        idx = 1
        while True:
            if self.wav_num == -2:
                break
            file_path = os.path.join(self.tempdir, f"{idx:03d}.wav")
            if not os.path.exists(file_path):
                time.sleep(0.1)  # Reduce CPU usage
                continue
            play_wave(file_path)
            idx += 1
            if idx > self.wav_num:
                self.wav_num = -2

    def process_texts(self):
        idx = 1
        s = ""
        done = False
        while not done:
            text = self.q.get()
            if text is None:
                done = True
                if len(s) == 0:
                    break
            if text:
                s += text
            if not done and len(s) < 10:
                continue
            sentences = s.split("。")
            for sentence in sentences:
                if len(sentence) == 0:
                    continue
                file_path = os.path.join(self.tempdir, f"{idx:03d}.wav")
                print(f"Processing: {sentence} to {file_path}")
                self.pool.submit(self.text_to_speech, sentence, file_path)
                idx += 1
            s = ""
        self.wav_num = idx - 1

    def run(self, text_generator):
        threading.Thread(target=self.play_audio_files).start()
        threading.Thread(target=self.process_texts).start()
        for text in text_generator:
            self.q.put(text)
        self.q.put(None)
        while self.wav_num != -2:
            time.sleep(0.1)
        shutil.rmtree(self.tempdir)


class TranscribeAudio:
    def __init__(self):
        self.console = Console()

    def record_audio(self, filename, session: Optional[PromptSession] = None):
        import pyaudio

        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        p = pyaudio.PyAudio()

        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        self.console.print(
            Panel(
                "Recording... Press Enter to stop.",
                title="Voice Input",
                border_style="cyan",
            )
        )
        frames = []
        recording = True

        def stop_recording():
            nonlocal recording
            recording = False
        
        # If no session is provided, create a simple input loop
        from prompt_toolkit.shortcuts import confirm

        def input_thread():
            if confirm("Press Enter to stop recording"):
                stop_recording()

        threading.Thread(target=input_thread, daemon=True).start()

        def record():
            nonlocal recording, frames
            while recording:
                data = stream.read(CHUNK)
                frames.append(data)

        record_thread = threading.Thread(target=record)
        record_thread.start()

        # Wait for the recording to stop
        while recording:
            time.sleep(0.1)

        record_thread.join()

        self.console.print(
            Panel(
                "Recording stopped.",
                title="Voice Input",
                border_style="green",
            )
        )

        stream.stop_stream()
        stream.close()
        p.terminate()

        wf = wave.open(filename, "wb")
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))
        wf.close()

    def transcribe_audio(self, filename, llm:byzerllm.ByzerLLM):        
        with open(filename, "rb") as audio_file:
            audio_content = audio_file.read()
            audio = "data:audio/wav;base64,"+base64.b64encode(audio_content).decode("utf-8")
        
        conversations = [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "audio": audio,
                    }
                ),
            }
        ]

        response = llm.chat_oai(conversations=conversations)
        transcription = json.loads(response[0].output)["text"]
        return transcription

    def voice_input_handler(self,llm):
        self.console.print(
            Panel(
                "Starting audio recording... Please speak now.",
                title="Voice Input",
                border_style="cyan",
            )
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_filename = temp_wav.name

        try:
            self.record_audio(temp_filename)
            self.console.print(
                Panel(
                    "Recording finished. Transcribing...",
                    title="Voice Input",
                    border_style="green",
                )
            )
            transcription = self.transcribe_audio(temp_filename, llm)
            self.console.print(
                Panel(
                    f"Transcription: {transcription}",
                    title="Result",
                    border_style="magenta",
                )
            )
            # session.default_buffer.insert_text(transcription)
        finally:
            # Ensure the temporary file is deleted
            os.unlink(temp_filename)


# byzerllm.connect_cluster()
# player = PlayStreamAudioFromText()
# player.run(["hello everyone", "i'am william", "auto coder is a great tool", "i hope you like it", "goodbye"])
