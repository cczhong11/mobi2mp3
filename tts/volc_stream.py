import base64
import json
import subprocess
import tempfile
import uuid
from typing import Optional

import requests

from tools import resolve_executable
from .base import TTSEngine
from .config import VolcTTSConfig


class VolcStreamTTS(TTSEngine):
    output_format = "mp3"

    def __init__(self, config: VolcTTSConfig):
        self.config = config

    def _build_headers(self) -> dict:
        headers = {
            "Content-Type": "application/json",
            "X-Api-App-Id": self.config.app_id,
            "X-Api-Access-Key": self.config.access_key,
            "X-Api-Request-Id": str(uuid.uuid4()),
        }
        if self.config.resource_id:
            headers["X-Api-Resource-Id"] = self.config.resource_id
        return headers

    def _build_payload(self, text: str) -> dict:
        audio_params = {
            "format": "mp3",
            "sample_rate": self.config.sample_rate,
        }
        if self.config.bit_rate is not None:
            audio_params["bit_rate"] = self.config.bit_rate
        req_params = {
            "text": text,
            "speaker": self.config.speaker,
            "audio_params": audio_params,
        }
        if self.config.model:
            req_params["model"] = self.config.model
        return {
            "user": {"uid": self.config.user_id},
            "namespace": self.config.namespace,
            "req_params": req_params,
        }

    def _extract_audio_chunk(self, payload: dict) -> Optional[bytes]:
        data = payload.get("data")
        if isinstance(data, str):
            return base64.b64decode(data)
        if isinstance(data, dict):
            audio = data.get("audio")
            if isinstance(audio, str):
                return base64.b64decode(audio)
        return None

    def synthesize(self, text: str, output_path: str) -> None:
        response = requests.post(
            self.config.url,
            headers=self._build_headers(),
            json=self._build_payload(text),
            stream=True,
            timeout=self.config.timeout_seconds,
        )
        response.raise_for_status()

        audio_bytes = bytearray()
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            line = line.strip()
            if line.startswith("data:"):
                line = line[len("data:") :].strip()
            try:
                chunk = json.loads(line)
            except json.JSONDecodeError:
                continue
            code = chunk.get("code")
            if code not in (None, 0, 20000000):
                raise RuntimeError(f"volc tts error: {chunk}")
            audio_chunk = self._extract_audio_chunk(chunk)
            if audio_chunk:
                audio_bytes.extend(audio_chunk)

        if not audio_bytes:
            raise RuntimeError("volc tts returned no audio data")

        if output_path.lower().endswith(".mp3"):
            with open(output_path, "wb") as file_obj:
                file_obj.write(audio_bytes)
            return

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_mp3 = tmp_file.name
        ffmpeg = resolve_executable("ffmpeg", "/opt/homebrew/bin/ffmpeg")
        subprocess.run(
            [ffmpeg, "-y", "-i", tmp_mp3, output_path],
            check=True,
        )
