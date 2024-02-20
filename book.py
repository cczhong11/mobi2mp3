from dataclasses import dataclass
import os
from typing import Text


CHINESE_COUNT_LIMIT = 5000
ENGLISH_COUNT_LIMIT = 8000


class Book(object):
    def __init__(self, input_path: str, output: str, language: str, rate: str):
        self.input_path = input_path
        self.language = language
        self.output = output
        self.rate = rate
        filename = self.input_path.split("/")[-1]
        self.book = filename.split(".")[:-1][0]
        self.book_path = os.path.join(self.output, "txt", self.book + ".txt")
        self.tmp_path = os.path.join(self.output, "tmp")
        self.mp3_path = os.path.join(self.output, "mp3")
        self.book_list = []

        self.file_count = 0

    def to_txt(self):
        if os.path.exists(f"{self.output}/txt/{self.book}.txt"):
            return
        if "/txt/" in self.input_path:
            os.system(f"cp {self.input_path} {self.book_path}")
            return
        os.system(f"/opt/homebrew/bin/ebook-convert {self.input_path} {self.book_path}")

    def split_book(self):
        file_txt = ""
        count = 0
        with open(self.book_path) as f:
            for l in f:
                l = l.strip()
                if "ISBN" in l or "本书由「ePUBw.COM」整理" in l:
                    continue
                if len(l) > 0:
                    file_txt += l
                    count += len(l)
                if (count > CHINESE_COUNT_LIMIT and self.language == "zh_CN") or (
                    count > ENGLISH_COUNT_LIMIT and self.language == "en_US"
                ):
                    self.book_list.append(file_txt)
                    file_txt = ""
                    count = 0
        self.book_list.append(file_txt)
        self.save_book_list_to_tmp()

    def save_book_list_to_tmp(self):
        for i, text in enumerate(self.book_list):
            file_path = os.path.join(self.tmp_path, f"text-{i}.txt")
            if os.path.exists(file_path):
                continue
            with open(file_path, "w") as f:
                f.write(text)

    def output_tmp(self):
        for i, text in enumerate(self.book_list):
            aiff_path = os.path.join(self.tmp_path, f"result-{i}.aiff")
            if os.path.exists(aiff_path):
                continue
            os.system("say -o '" + aiff_path + "' '" + text.replace("'", '"') + "'")
            # self.engine.save_to_file(text, aiff_path)
        total = len(self.book_list)
        self.file_count = total // 10 + 1

        print(f"total {total} file count {self.file_count}")
        for i in range(self.file_count):
            if i * 10 >= total:
                break
            with open(os.path.join(self.tmp_path, f"result-{i}.txt"), "w") as f:
                for j in range(10):
                    if i * 10 + j >= total:
                        break
                    f.write(f"file result-{i*10+j}.aiff\n")
        # self.engine.runAndWait()

    def combine_aiff(self, count):
        if not os.path.join(self.tmp_path, f"result-{count}.txt"):
            return
        new_file = os.path.join(self.tmp_path, f"{self.book}-{count}.aiff")
        result = os.path.join(self.tmp_path, f"result-{count}.txt")
        final = os.path.join(self.mp3_path, f"{self.book}-{count}.mp3")
        print(new_file, result, final)
        if not os.path.exists(new_file):
            cmd = f"/opt/homebrew/bin/ffmpeg -f concat -i {result} -c copy {new_file}"
            print(cmd)
            os.system(cmd)
        if not os.path.exists(final):
            os.system(
                f"/opt/homebrew/bin/ffmpeg -i {new_file} -f mp3 -acodec libmp3lame -ab 16000 -ar 44100 {final}"
            )
            print(f"convert {new_file} to {final}")

    def clean(self):

        os.system(f"rm {self.tmp_path}/*")

    def upload_s3(self):
        try:
            from DataWriter.AWSS3DataWriter import AWSS3DataWriter
        except ImportError:
            print("import error")
            return
        s3 = AWSS3DataWriter("rss-ztc")
        for i in range(self.file_count):
            s3.write_data("book", os.path.join(self.mp3_path, f"{self.book}-{i}.mp3"))
