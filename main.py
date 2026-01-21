import click
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
    type=click.Choice(["mac_say"]),
)
@click.option("--voice", help="macOS voice name", default=None)
@click.option("--no_upload", is_flag=True)
@click.option("--debug", is_flag=True)
def main(
    inputfile: str,
    outputpath: str,
    language: str,
    rate: int,
    tts_engine: str,
    voice: str,
    no_upload: bool,
    debug: bool,
):
    create_folder(outputpath)
    tts_config = TTSConfig(language=language, rate=rate, voice=voice)
    tts = create_tts(tts_engine, tts_config)
    b = Book(inputfile, outputpath, language, tts)
    b.to_txt()
    b.split_book()
    b.output_tmp()

    try:
        for i in range(b.file_count):
            b.combine_aiff(i)

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
