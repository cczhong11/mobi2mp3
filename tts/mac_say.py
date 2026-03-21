import subprocess

from .base import TTSEngine
from .config import TTSConfig


class MacSayTTS(TTSEngine):
    output_format = "aiff"

    def __init__(self, config: TTSConfig):
        self.config = config

    def synthesize(self, text: str, output_path: str) -> None:
        cmd = ["say", "-o", output_path, "-r", str(self.config.rate)]
        if self.config.voice:
            cmd.extend(["-v", self.config.voice])
        cmd.append(text)
        subprocess.run(cmd, check=True)
