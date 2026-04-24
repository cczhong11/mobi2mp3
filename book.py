import os
import re
import shutil
from typing import List

from aws_util import S3Uploader
from tools import resolve_executable


CHINESE_COUNT_LIMIT = 5000
ENGLISH_COUNT_LIMIT = 8000
SENTENCE_SPLIT_PATTERN = re.compile(r"[^。！？；：.!?;:]+[。！？；：.!?;:”\"]*")
BODY_START_MARKERS = (
    "悉达多，俊美的婆罗门",
    "第一部婆罗门之子悉达多",
    "婆罗门之子悉达多",
)


class Book(object):
    def __init__(self, input_path: str, output: str, language: str, tts_engine):
        self.input_path = input_path
        self.language = language
        self.output = output
        self.tts_engine = tts_engine
        filename = self.input_path.split("/")[-1]
        self.book = filename.split(".")[:-1][0]
        self.book_path = os.path.join(self.output, "txt", self.book + ".txt")
        self.tmp_root = os.path.join(self.output, "tmp")
        self.tmp_path = os.path.join(self.tmp_root, self.book)
        self.mp3_path = os.path.join(self.output, "mp3")
        self.book_list: List[str] = []

        self.file_count = 0
        os.makedirs(self.tmp_path, exist_ok=True)

    def to_txt(self):
        if os.path.exists(f"{self.output}/txt/{self.book}.txt"):
            return
        if "/txt/" in self.input_path:
            os.system(f"cp {self.input_path} {self.book_path}")
            return
        ebook_convert = resolve_executable(
            "ebook-convert",
            "/Applications/Calibre.app/Contents/MacOS/ebook-convert",
            "/Applications/calibre.app/Contents/MacOS/ebook-convert",
            "/opt/homebrew/bin/ebook-convert",
        )
        os.system(f"{ebook_convert} {self.input_path} {self.book_path}")

    def split_book(self):
        self.book_list = []
        limit = self._chunk_limit()
        sentence_buffer: List[str] = []
        with open(self.book_path) as f:
            raw_text = "".join(l.strip() for l in f if l.strip())
        content = self._strip_front_matter(raw_text)
        if content:
            sentence_buffer.extend(self._split_sentences(content))
        self._append_sentence_chunks(sentence_buffer, limit)
        self.save_book_list_to_tmp()

    def save_book_list_to_tmp(self):
        #self._reset_tmp_files()
        for i, text in enumerate(self.book_list):
            file_path = os.path.join(self.tmp_path, f"text-{i}.txt")
            with open(file_path, "w") as f:
                f.write(text)

    def output_tmp(self):
        ext = getattr(self.tts_engine, "output_format", "aiff")
        combine_group_size = getattr(self.tts_engine, "combine_group_size", 10)
        for i, text in enumerate(self.book_list):
            audio_path = os.path.join(self.tmp_path, f"result-{i}.{ext}")
            if os.path.exists(audio_path):
                continue
            self.tts_engine.synthesize(text, audio_path)
        total = len(self.book_list)
        self.file_count = total // combine_group_size + 1

        print(f"total {total} file count {self.file_count}")
        for i in range(self.file_count):
            if i * combine_group_size >= total:
                break
            with open(os.path.join(self.tmp_path, f"result-{i}.txt"), "w") as f:
                for j in range(combine_group_size):
                    if i * combine_group_size + j >= total:
                        break
                    f.write(f"file result-{i*combine_group_size+j}.{ext}\n")
    def combine_audio(self, count):
        ext = getattr(self.tts_engine, "output_format", "aiff")
        if not os.path.exists(os.path.join(self.tmp_path, f"result-{count}.txt")):
            return
        ffmpeg = resolve_executable("ffmpeg", "/opt/homebrew/bin/ffmpeg")
        new_file = os.path.join(self.tmp_path, f"{self.book}-{count}.{ext}")
        result = os.path.join(self.tmp_path, f"result-{count}.txt")
        final = os.path.join(self.mp3_path, f"{self.book}-{count}.mp3")
        print(new_file, result, final)
        if not os.path.exists(new_file):
            cmd = f"{ffmpeg} -f concat -safe 0 -i {result} -c copy {new_file}"
            print(cmd)
            os.system(cmd)
        if ext == "mp3":
            if not os.path.exists(final):
                shutil.copyfile(new_file, final)
        else:
            if not os.path.exists(final):
                os.system(
                    f"{ffmpeg} -i {new_file} -f mp3 -acodec libmp3lame -ab 16000 -ar 44100 {final}"
                )
                print(f"convert {new_file} to {final}")
        if not os.path.exists(final):
            raise Exception(f"file {final} not exists")

    def clean(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def _chunk_limit(self) -> int:
        engine_limit = getattr(self.tts_engine, "text_char_limit", None)
        if engine_limit is not None:
            return engine_limit
        if self.language == "zh_CN":
            return CHINESE_COUNT_LIMIT
        return ENGLISH_COUNT_LIMIT

    def _append_sentence_chunks(self, sentences: List[str], limit: int):
        current = ""
        for sentence in sentences:
            if len(sentence) > limit:
                if current:
                    self.book_list.append(current)
                    current = ""
                self.book_list.extend(self._force_split_text(sentence, limit))
                continue
            if not current:
                current = sentence
                continue
            if len(current) + len(sentence) <= limit:
                current += sentence
            else:
                self.book_list.append(current)
                current = sentence
        if current:
            self.book_list.append(current)

    def _split_sentences(self, text: str) -> List[str]:
        sentences = [item.strip() for item in SENTENCE_SPLIT_PATTERN.findall(text) if item.strip()]
        if sentences:
            return sentences
        return [text]

    def _force_split_text(self, text: str, limit: int) -> List[str]:
        return [text[i : i + limit] for i in range(0, len(text), limit)]

    def _strip_front_matter(self, text: str) -> str:
        normalized = text.replace(" ", "")
        for marker in BODY_START_MARKERS:
            idx = normalized.find(marker.replace(" ", ""))
            if idx != -1:
                return normalized[idx:]
        return normalized

    def _reset_tmp_files(self):
        for filename in os.listdir(self.tmp_path):
            if (
                filename.startswith("text-")
                or filename.startswith("result-")
                or filename.startswith(f"{self.book}-")
            ):
                os.remove(os.path.join(self.tmp_path, filename))

    def upload_s3(self):
        uploader = S3Uploader("rss-ztc")
        for i in range(self.file_count):
            uploader.upload_file("book", os.path.join(self.mp3_path, f"{self.book}-{i}.mp3"))
