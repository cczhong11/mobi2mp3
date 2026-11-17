import click
import os
from pathlib import Path
from dotenv import load_dotenv

from book import Book
from tts import CliTTSOptions, build_tts_from_cli

load_dotenv()

home = str(Path.home())


def create_folder(path):
    def create_folder_single(folder_name):
        os.makedirs(os.path.join(path, folder_name), exist_ok=True)

    create_folder_single("txt")
    create_folder_single("mp3")
    create_folder_single("tmp")


@click.command()
@click.option("-i", "--inputfile", help="input file path", type=str)
@click.option(
    "-o",
    "--outputpath",
    help="output file path",
    default=os.path.join(home, "Documents", "mobi2mp3"),
)
@click.option(
    "-l", "--language", help="language setting like zh_CN/en_US", default="zh_CN"
)
@click.option("-r", "--rate", help="rate setting 100-400", default=400, type=int)
@click.option(
    "--tts",
    "tts_engine",
    help="tts engine name",
    default="mac_say",
    type=click.Choice(["mac_say", "volc_stream", "mlx_qwen3", "omlx"]),
)
@click.option("--voice", help="voice name for macOS say, mlx qwen3 or oMLX", default=None)
@click.option("--omlx-url", help="oMLX API base URL including /v1", default="http://localhost:8000/v1")
@click.option("--omlx-model", help="model ID listed by oMLX", default="Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16")
@click.option("--omlx-api-key", help="oMLX API key (or set OMLX_API_KEY)", envvar="OMLX_API_KEY", default=None)
@click.option("--omlx-language", help="oMLX language, e.g. Chinese or English", default=None)
@click.option("--omlx-instruct", help="oMLX narration style instruction", default=None)
@click.option("--omlx-speed", help="oMLX speed multiplier", default=1.0, type=click.FloatRange(min=0, min_open=True))
@click.option("--omlx-timeout", help="oMLX request timeout in seconds", default=600.0, type=click.FloatRange(min=0, min_open=True))
@click.option("--volc-app-id", help="volcengine app id", default="9446257588")
@click.option("--volc-access-key", help="volcengine access key", default=None)
@click.option("--volc-resource-id", help="volcengine resource id", default="seed-tts-1.0")
@click.option(
    "--volc-speaker",
    help="volcengine speaker name",
    default="zh_female_shuangkuaisisi_moon_bigtts",
)
@click.option("--volc-model", help="volcengine model version", default=None)
@click.option("--volc-sample-rate", help="volcengine sample rate", default=24000, type=int)
@click.option("--volc-bit-rate", help="volcengine bit rate", default=None, type=int)
@click.option("--volc-config", "volc_config_path", help="volcengine config json path", default="key.json")
@click.option(
    "--mlx-model",
    help="mlx qwen3 model repo id",
    default="mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16",
)
@click.option(
    "--mlx-language",
    help="mlx qwen3 language name, e.g. English/Chinese/Japanese/Korean",
    default=None,
)
@click.option("--mlx-instruct", help="mlx qwen3 style or voice design instruction", default=None)
@click.option("--mlx-ref-audio", help="mlx qwen3 custom voice reference audio path", default=None)
@click.option("--mlx-ref-text", help="mlx qwen3 reference audio transcript", default=None)
@click.option("--mlx-speed", help="mlx qwen3 speed multiplier", default=1.0, type=float)
@click.option("--mlx-max-tokens", help="mlx qwen3 max generation tokens", default=16000, type=int)
@click.option("--no_upload", is_flag=True)
@click.option("--debug", is_flag=True)
def main(
    inputfile: str,
    outputpath: str,
    language: str,
    rate: int,
    tts_engine: str,
    voice: str,
    omlx_url: str,
    omlx_model: str,
    omlx_api_key: str,
    omlx_language: str,
    omlx_instruct: str,
    omlx_speed: float,
    omlx_timeout: float,
    volc_app_id: str,
    volc_access_key: str,
    volc_resource_id: str,
    volc_speaker: str,
    volc_model: str,
    volc_sample_rate: int,
    volc_bit_rate: int,
    volc_config_path: str,
    mlx_model: str,
    mlx_language: str,
    mlx_instruct: str,
    mlx_ref_audio: str,
    mlx_ref_text: str,
    mlx_speed: float,
    mlx_max_tokens: int,
    no_upload: bool,
    debug: bool,
):
    create_folder(outputpath)
    tts = build_tts_from_cli(
        engine_name=tts_engine,
        language=language,
        rate=rate,
        options=CliTTSOptions(
            voice=voice,
            omlx_url=omlx_url,
            omlx_model=omlx_model,
            omlx_api_key=omlx_api_key,
            omlx_language=omlx_language,
            omlx_instruct=omlx_instruct,
            omlx_speed=omlx_speed,
            omlx_timeout=omlx_timeout,
            volc_app_id=volc_app_id,
            volc_access_key=volc_access_key,
            volc_resource_id=volc_resource_id,
            volc_speaker=volc_speaker,
            volc_model=volc_model,
            volc_sample_rate=volc_sample_rate,
            volc_bit_rate=volc_bit_rate,
            volc_config_path=volc_config_path,
            mlx_model=mlx_model,
            mlx_language=mlx_language,
            mlx_instruct=mlx_instruct,
            mlx_ref_audio=mlx_ref_audio,
            mlx_ref_text=mlx_ref_text,
            mlx_speed=mlx_speed,
            mlx_max_tokens=mlx_max_tokens,
        ),
    )
    b = Book(inputfile, outputpath, language, tts)
    b.to_txt()
    b.split_book()
    if not b.output_tmp():
        return

    try:
        for i in range(b.file_count):
            b.combine_audio(i)

        if not debug:
            b.clean()
        if no_upload:
            return
        b.upload_s3()
    except Exception as e:
        print(e)
        with open(os.path.join(outputpath, "error.log"), "w") as f:
            f.write(str(e))


if __name__ == "__main__":
    main()
