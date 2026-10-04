from dataclasses import dataclass
from typing import Optional


@dataclass
class TTSConfig:
    language: str
    rate: int
    voice: Optional[str] = None


@dataclass
class VolcTTSConfig:
    app_id: str
    access_key: str
    resource_id: str
    speaker: str
    user_id: str = "mobi2mp3"
    url: str = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
    sample_rate: int = 24000
    bit_rate: Optional[int] = None
    model: Optional[str] = None
    namespace: str = "BidirectionalTTS"
    timeout_seconds: int = 60


@dataclass
class MlxQwenTTSConfig:
    model: str
    voice: str
    language: str
    speed: float = 1.0
    instruct: Optional[str] = None
    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None
    max_tokens: int = 16000
    audio_format: str = "mp3"

