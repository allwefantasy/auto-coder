


import os
import tempfile
from rich.console import Console
from rich.panel import Panel

from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    DefaultValue,
    RequestOption,
)


class Voice2TextAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args
        self.console = Console()

    def run(self):
        """执行 voice2text 命令的主要逻辑"""
        from autocoder.common.audio import TranscribeAudio

        transcribe_audio = TranscribeAudio()
        temp_wav_file = os.path.join(
            tempfile.gettempdir(), "voice_input.wav")

        transcribe_audio.record_audio(temp_wav_file)
        self.console.print(
            Panel(
                "Recording finished. Transcribing...",
                title="Voice",
                border_style="green",
            )
        )

        if self.llm and self.llm.get_sub_client("voice2text_model"):
            voice2text_llm = self.llm.get_sub_client("voice2text_model")
        else:
            voice2text_llm = self.llm
        
        transcription = transcribe_audio.transcribe_audio(
            temp_wav_file, voice2text_llm
        )

        self.console.print(
            Panel(
                f"Transcription: <_transcription_>{transcription}</_transcription_>",
                title="Result",
                border_style="magenta",
            )
        )

        with open(os.path.join(".auto-coder", "exchange.txt"), "w", encoding="utf-8") as f:
            f.write(transcription)

        request_queue.add_request(
            self.args.request_id,
            RequestValue(
                value=DefaultValue(value=transcription),
                status=RequestOption.COMPLETED,
            ),
        )

        os.remove(temp_wav_file)


