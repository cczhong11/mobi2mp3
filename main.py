import click
import json
import os
from pathlib import Path

from book import Book
from tts import TTSConfig, create_tts

home = str(Path.home())


def create_folder(path):
    def create_folder_single(folder_name):
        if not os.path.exists(os.path.join(path, folder_name)):
            os.mkdir(os.path.join(path, folder_name))

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
    type=click.Choice(["mac_say", "volc_stream"]),
)
@click.option("--voice", help="macOS voice name", default=None)
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
@click.option("--no_upload", is_flag=True)
@click.option("--debug", is_flag=True)
def main(
    inputfile: str,
    outputpath: str,
    language: str,
    rate: int,
    tts_engine: str,
    voice: str,
    volc_app_id: str,
    volc_access_key: str,
    volc_resource_id: str,
    volc_speaker: str,
    volc_model: str,
    volc_sample_rate: int,
    volc_bit_rate: int,
    volc_config_path: str,
    no_upload: bool,
    debug: bool,
):
    create_folder(outputpath)
    tts_config = TTSConfig(language=language, rate=rate, voice=voice)
    volc_config = None
    if tts_engine == "volc_stream":
        from tts import VolcTTSConfig

        file_config = {}
        if volc_config_path and os.path.exists(volc_config_path):
            try:
                with open(volc_config_path, "r") as f:
                    file_config = json.load(f).get("volc", {})
            except (json.JSONDecodeError, OSError):
                file_config = {}

        app_id = volc_app_id or file_config.get("app_id")
        access_key = (
            volc_access_key
            or file_config.get("access_key")
            or os.getenv("VOLC_ACCESS_KEY")
            or os.getenv("VOLCENGINE_ACCESS_KEY")
        )
        resource_id = volc_resource_id or file_config.get("resource_id")
        speaker = volc_speaker or file_config.get("speaker")
        model = volc_model or file_config.get("model")
        sample_rate = (
            volc_sample_rate if volc_sample_rate is not None else file_config.get("sample_rate")
        )
        bit_rate = volc_bit_rate if volc_bit_rate is not None else file_config.get("bit_rate")
        if not access_key:
            raise click.ClickException(
                "volc_stream requires --volc-access-key or VOLC_ACCESS_KEY"
            )
        volc_config = VolcTTSConfig(
            app_id=app_id,
            access_key=access_key,
            resource_id=resource_id,
            speaker=speaker,
            model=model,
            sample_rate=sample_rate,
            bit_rate=bit_rate,
        )
    tts = create_tts(tts_engine, tts_config, volc_config)
    b = Book(inputfile, outputpath, language, tts)
    b.to_txt()
    b.split_book()
    b.output_tmp()

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
