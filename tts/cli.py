import json
import os
from dataclasses import dataclass
from typing import Any, Optional

import click

from .config import MlxQwenTTSConfig, TTSConfig, VolcTTSConfig
from .factory import create_tts

MLX_QWEN3_LANGUAGE_MAP = {
    "zh_CN": "Chinese",
    "en_US": "English",
    "ja_JP": "Japanese",
    "ko_KR": "Korean",
}


@dataclass
class CliTTSOptions:
    voice: Optional[str] = None
    volc_app_id: str = "9446257588"
    volc_access_key: Optional[str] = None
    volc_resource_id: str = "seed-tts-1.0"
    volc_speaker: str = "zh_female_shuangkuaisisi_moon_bigtts"
    volc_model: Optional[str] = None
    volc_sample_rate: int = 24000
    volc_bit_rate: Optional[int] = None
    volc_config_path: str = "key.json"
    mlx_model: str = "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16"
    mlx_language: Optional[str] = None
    mlx_instruct: Optional[str] = None
    mlx_ref_audio: Optional[str] = None
    mlx_ref_text: Optional[str] = None
    mlx_speed: float = 1.0
    mlx_max_tokens: int = 16000


def build_tts_from_cli(engine_name: str, language: str, rate: int, options: CliTTSOptions):
    base_config = TTSConfig(language=language, rate=rate, voice=options.voice)
    engine_config = None
    if engine_name == "volc_stream":
        engine_config = build_volc_config(options)
    elif engine_name == "mlx_qwen3":
        engine_config = build_mlx_qwen_config(language, options)
    return create_tts(engine_name, base_config, engine_config)


def build_volc_config(options: CliTTSOptions) -> VolcTTSConfig:
    file_config = load_json_config(options.volc_config_path).get("volc", {})
    access_key = (
        options.volc_access_key
        or file_config.get("access_key")
        or os.getenv("VOLC_ACCESS_KEY")
        or os.getenv("VOLCENGINE_ACCESS_KEY")
    )
    if not access_key:
        raise click.ClickException(
            "volc_stream requires --volc-access-key or VOLC_ACCESS_KEY"
        )

    return VolcTTSConfig(
        app_id=coalesce(options.volc_app_id, file_config.get("app_id")),
        access_key=access_key,
        resource_id=coalesce(options.volc_resource_id, file_config.get("resource_id")),
        speaker=coalesce(options.volc_speaker, file_config.get("speaker")),
        model=coalesce(options.volc_model, file_config.get("model")),
        sample_rate=coalesce(options.volc_sample_rate, file_config.get("sample_rate")),
        bit_rate=coalesce(options.volc_bit_rate, file_config.get("bit_rate")),
    )


def build_mlx_qwen_config(language: str, options: CliTTSOptions) -> MlxQwenTTSConfig:
    return MlxQwenTTSConfig(
        model=options.mlx_model,
        voice=options.voice or "serena",
        language=options.mlx_language or MLX_QWEN3_LANGUAGE_MAP.get(language, language),
        instruct=options.mlx_instruct,
        ref_audio=options.mlx_ref_audio,
        ref_text=options.mlx_ref_text,
        speed=options.mlx_speed,
        max_tokens=options.mlx_max_tokens,
    )


def load_json_config(path: Optional[str]) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as file_obj:
            return json.load(file_obj)
    except (json.JSONDecodeError, OSError):
        return {}


def coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None
