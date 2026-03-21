from .config import MlxQwenTTSConfig, TTSConfig, VolcTTSConfig
from .mac_say import MacSayTTS
from .mlx_qwen3 import MlxQwen3TTS
from .volc_stream import VolcStreamTTS


def create_tts(engine_name: str, config: TTSConfig, engine_config=None):
    if engine_name == "mac_say":
        return MacSayTTS(config)
    if engine_name == "volc_stream":
        if not isinstance(engine_config, VolcTTSConfig):
            raise ValueError("volc_stream requires VolcTTSConfig")
        return VolcStreamTTS(engine_config)
    if engine_name == "mlx_qwen3":
        if not isinstance(engine_config, MlxQwenTTSConfig):
            raise ValueError("mlx_qwen3 requires MlxQwenTTSConfig")
        return MlxQwen3TTS(engine_config)
    raise ValueError(f"Unknown tts engine: {engine_name}")
