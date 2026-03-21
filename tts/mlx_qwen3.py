import os

from .base import TTSEngine
from .config import MlxQwenTTSConfig

MLX_QWEN3_LANG_CODE_MAP = {
    "English": "en",
    "Chinese": "zh",
    "Japanese": "ja",
    "Korean": "ko",
}


class MlxQwen3TTS(TTSEngine):
    output_format = "mp3"
    text_char_limit = 200

    def __init__(self, config: MlxQwenTTSConfig):
        self.config = config

    def synthesize(self, text: str, output_path: str) -> None:
        try:
            from mlx_audio.tts.generate import generate_audio
        except ImportError as exc:
            raise RuntimeError(
                "mlx_qwen3 requires mlx-audio on Apple Silicon. Install project deps with `uv sync`."
            ) from exc

        output_dir = os.path.dirname(output_path) or "."
        file_prefix = os.path.splitext(os.path.basename(output_path))[0]
        os.makedirs(output_dir, exist_ok=True)

        generate_audio(
            text=text,
            model=self.config.model,
            voice=self.config.voice,
            language=self.config.language,
            lang_code=MLX_QWEN3_LANG_CODE_MAP.get(self.config.language, "en"),
            speed=self.config.speed,
            instruct=self.config.instruct,
            ref_audio=self.config.ref_audio,
            ref_text=self.config.ref_text,
            max_tokens=self.config.max_tokens,
            output_path=output_dir,
            file_prefix=file_prefix,
            audio_format=self.config.audio_format,
            join_audio=True,
            verbose=False,
        )

        if not os.path.exists(output_path):
            raise RuntimeError(f"mlx_qwen3 failed to generate {output_path}")
