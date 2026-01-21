from dataclasses import dataclass
import subprocess
from typing import Optional


@dataclass
class TTSConfig:
    language: str
    rate: int
    voice: Optional[str] = None


class TTSEngine:
    def synthesize(self, text: str, output_path: str) -> None:
        raise NotImplementedError


class MacSayTTS(TTSEngine):
    def __init__(self, config: TTSConfig):
        self.config = config

    def synthesize(self, text: str, output_path: str) -> None:
        cmd = ["say", "-o", output_path, "-r", str(self.config.rate)]
        if self.config.voice:
            cmd.extend(["-v", self.config.voice])
        cmd.append(text)
        subprocess.run(cmd, check=True)


def create_tts(engine_name: str, config: TTSConfig) -> TTSEngine:
    if engine_name == "mac_say":
        return MacSayTTS(config)
    raise ValueError(f"Unknown tts engine: {engine_name}")
