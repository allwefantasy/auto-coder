from prompt_toolkit import PromptSession
import simpleaudio as sa
import numpy as np
import wave
import byzerllm
import base64
import json
import tempfile
import os
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress

class AudioTranscribe:
    def __init__(self):
        self.console = Console()

    def record_audio(self, filename, duration=5):
        SAMPLE_RATE = 44100
        NUM_CHANNELS = 1
        SAMPLE_WIDTH = 2  # 16-bit

        recording = np.zeros(SAMPLE_RATE * duration * NUM_CHANNELS, dtype=np.int16)
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Recording...", total=duration)
            
            for i in range(duration):
                recording[i*SAMPLE_RATE:(i+1)*SAMPLE_RATE] = np.frombuffer(
                    sa.play_buffer(np.zeros(SAMPLE_RATE, dtype=np.int16), 1, 2, SAMPLE_RATE).raw_data,
                    dtype=np.int16
                )
                progress.update(task, advance=1)

        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(NUM_CHANNELS)
            wf.setsampwidth(SAMPLE_WIDTH)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(recording.tobytes())

    def transcribe_audio(self, filename, llm):
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

    def voice_input_handler(self, session: PromptSession, llm):
        self.console.print(Panel("Starting audio recording... Please speak now.", title="Voice Input", border_style="cyan"))
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_filename = temp_wav.name
        
        try:
            self.record_audio(temp_filename)
            self.console.print(Panel("Recording finished. Transcribing...", title="Voice Input", border_style="green"))
            transcription = self.transcribe_audio(temp_filename, llm)
            self.console.print(Panel(f"Transcription: {transcription}", title="Result", border_style="magenta"))
            session.default_buffer.insert_text(transcription)
        finally:
            # Ensure the temporary file is deleted
            os.unlink(temp_filename)