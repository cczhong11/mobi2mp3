import click
import pyttsx3
from book import Book
from pathlib import Path

home = str(Path.home())
import os


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
@click.option("--no_upload", is_flag=True)
def main(inputfile: str, outputpath: str, language: str, rate: int, no_upload: bool):
    create_folder(outputpath)
    b = Book(inputfile, outputpath, language, rate)
    b.to_txt()
    b.split_book()
    b.output_tmp()
    for i in range(b.file_count):
        b.combine_aiff(i)
    b.clean()
    if no_upload:
        return
    b.upload_s3()


if __name__ == "__main__":
    main()
