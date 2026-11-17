from pathlib import Path

import requests

from .base import TTSEngine
from .config import OmlxTTSConfig


class OmlxTTS(TTSEngine):
    output_format = "mp3"
    text_char_limit = 200
    combine_group_size = 50

    def __init__(self, config: OmlxTTSConfig):
        self.config = config

    def synthesize(self, text: str, output_path: str) -> None:
        headers = {}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        payload = {
            "model": self.config.model,
            "input": text,
            "voice": self.config.voice,
            "language": self.config.language,
            "speed": self.config.speed,
            "response_format": "mp3",
            "stream": False,
        }
        if self.config.instructions:
            payload["instructions"] = self.config.instructions

        url = self.config.base_url.rstrip("/") + "/audio/speech"
        with requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=(10, self.config.timeout_seconds),
        ) as response:
            if response.status_code in (401, 403):
                raise RuntimeError(
                    "oMLX authentication failed. Set OMLX_API_KEY to your server's API key."
                )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if not content_type.startswith("audio/") or not response.content:
                raise RuntimeError("oMLX returned no audio or an unexpected response type")
            audio = response.content

        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(audio)
