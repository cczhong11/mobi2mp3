import os
import re
import shutil
import subprocess
from typing import List

from aws_util import S3Uploader
from epub_chapters import Chapter, parse_epub
from tools import resolve_executable


CHINESE_COUNT_LIMIT = 5000
ENGLISH_COUNT_LIMIT = 8000
SENTENCE_SPLIT_PATTERN = re.compile(r"[^。！？；：.!?;:]+[。！？；：.!?;:”\"]*")
BODY_START_MARKERS = (
    "悉达多，俊美的婆罗门",
    "第一部婆罗门之子悉达多",
    "婆罗门之子悉达多",
)
CHAPTER_HEADING_PATTERN = re.compile(
    r"^\s*(?:第[0-9零一二三四五六七八九十百千万两〇○]+[章节回卷部篇]|chapter\s+\d+).*$",
    re.IGNORECASE,
)
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


class Book(object):
    def __init__(self, input_path: str, output: str, language: str, tts_engine):
        self.input_path = input_path
        self.language = language
        self.output = output
        self.tts_engine = tts_engine
        filename = os.path.basename(self.input_path)
        self.book = os.path.splitext(filename)[0]
        self.book_path = os.path.join(self.output, "txt", self.book + ".txt")
        self.tmp_root = os.path.join(self.output, "tmp")
        self.tmp_path = os.path.join(self.tmp_root, self.book)
        self.mp3_path = os.path.join(self.output, "mp3")
        self.book_list: List[str] = []
        self.chapters: List[Chapter] = []
        self.chapter_chunks: List[List[str]] = []
        self.final_files: List[str] = []

        self.file_count = 0
        os.makedirs(self.tmp_path, exist_ok=True)

    def to_txt(self):
        if os.path.splitext(self.input_path)[1].lower() == ".epub":
            return
        if os.path.exists(f"{self.output}/txt/{self.book}.txt"):
            return
        if os.path.splitext(self.input_path)[1].lower() == ".txt":
            shutil.copyfile(self.input_path, self.book_path)
            return
        ebook_convert = resolve_executable(
            "ebook-convert",
            "/Applications/Calibre.app/Contents/MacOS/ebook-convert",
            "/Applications/calibre.app/Contents/MacOS/ebook-convert",
            "/opt/homebrew/bin/ebook-convert",
        )
        subprocess.run([ebook_convert, self.input_path, self.book_path], check=True)

    def split_book(self):
        self.book_list = []
        self.chapter_chunks = []
        limit = self._chunk_limit()
        if os.path.splitext(self.input_path)[1].lower() == ".epub":
            self.chapters = parse_epub(self.input_path)
        else:
            with open(self.book_path, encoding="utf-8", errors="replace") as file_obj:
                self.chapters = self._parse_text_chapters(file_obj.read())

        for chapter in self.chapters:
            chunks: List[str] = []
            self._append_sentence_chunks(
                self._split_sentences(chapter.content), limit, target=chunks
            )
            if chunks:
                self.chapter_chunks.append(chunks)
                self.book_list.extend(chunks)
        self.file_count = len(self.chapter_chunks)
        self.save_book_list_to_tmp()

    def save_book_list_to_tmp(self):
        #self._reset_tmp_files()
        for chapter_index, chunks in enumerate(self.chapter_chunks):
            for chunk_index, text in enumerate(chunks):
                file_path = os.path.join(
                    self.tmp_path, f"text-{chapter_index}-{chunk_index}.txt"
                )
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(text)

    def output_tmp(self):
        ext = getattr(self.tts_engine, "output_format", "aiff")
        total = sum(len(chunks) for chunks in self.chapter_chunks)
        pending = []
        for chapter_index, chunks in enumerate(self.chapter_chunks):
            for chunk_index, text in enumerate(chunks):
                audio_path = os.path.join(
                    self.tmp_path, f"audio-{chapter_index}-{chunk_index}.{ext}"
                )
                if not os.path.exists(audio_path):
                    pending.append((text, audio_path))

        for text, audio_path in pending:
            self.tts_engine.synthesize(text, audio_path)

        for chapter_index, chunks in enumerate(self.chapter_chunks):
            with open(
                os.path.join(self.tmp_path, f"chapter-{chapter_index}.txt"),
                "w",
                encoding="utf-8",
            ) as manifest:
                for chunk_index in range(len(chunks)):
                    manifest.write(f"file audio-{chapter_index}-{chunk_index}.{ext}\n")
        print(f"total {total} chunks, {self.file_count} chapters")
        return True

    def combine_audio(self, count):
        ext = getattr(self.tts_engine, "output_format", "aiff")
        manifest = os.path.join(self.tmp_path, f"chapter-{count}.txt")
        if not os.path.exists(manifest):
            return
        ffmpeg = resolve_executable("ffmpeg", "/opt/homebrew/bin/ffmpeg")
        new_file = os.path.join(self.tmp_path, f"chapter-{count}.{ext}")
        chapter_name = self._safe_chapter_name(self.chapters[count].title)
        book_name = self._safe_filename(self.book)
        final = os.path.join(self.mp3_path, f"{book_name}_{count:03d}_{chapter_name}.mp3")
        print(new_file, manifest, final)
        if not os.path.exists(new_file):
            cmd = [ffmpeg, "-f", "concat", "-safe", "0", "-i", manifest, "-c", "copy", new_file]
            print(" ".join(cmd))
            subprocess.run(cmd, check=True)
        if ext == "mp3":
            if not os.path.exists(final):
                shutil.copyfile(new_file, final)
        else:
            if not os.path.exists(final):
                subprocess.run(
                    [
                        ffmpeg,
                        "-i",
                        new_file,
                        "-f",
                        "mp3",
                        "-acodec",
                        "libmp3lame",
                        "-ab",
                        "16000",
                        "-ar",
                        "44100",
                        final,
                    ],
                    check=True,
                )
                print(f"convert {new_file} to {final}")
        if not os.path.exists(final):
            raise Exception(f"file {final} not exists")
        while len(self.final_files) <= count:
            self.final_files.append("")
        self.final_files[count] = final

    def clean(self):
        shutil.rmtree(self.tmp_path, ignore_errors=True)

    def _chunk_limit(self) -> int:
        engine_limit = getattr(self.tts_engine, "text_char_limit", None)
        if engine_limit is not None:
            return engine_limit
        if self.language == "zh_CN":
            return CHINESE_COUNT_LIMIT
        return ENGLISH_COUNT_LIMIT

    def _append_sentence_chunks(
        self, sentences: List[str], limit: int, target: List[str] | None = None
    ):
        target = self.book_list if target is None else target
        current = ""
        for sentence in sentences:
            if len(sentence) > limit:
                if current:
                    target.append(current)
                    current = ""
                target.extend(self._force_split_text(sentence, limit))
                continue
            if not current:
                current = sentence
                continue
            if len(current) + len(sentence) <= limit:
                current += sentence
            else:
                target.append(current)
                current = sentence
        if current:
            target.append(current)

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

    def _parse_text_chapters(self, text: str) -> List[Chapter]:
        lines = [line.strip() for line in text.splitlines()]
        chapters: List[Chapter] = []
        title = "正文"
        content: List[str] = []
        found_heading = False
        for line in lines:
            if not line:
                continue
            if CHAPTER_HEADING_PATTERN.match(line) and len(line) <= 80:
                if content:
                    chapter_text = self._strip_front_matter("".join(content))
                    if chapter_text:
                        chapters.append(Chapter(title, chapter_text))
                title = line
                content = [line]
                found_heading = True
            else:
                content.append(line)
        if content:
            chapter_text = self._strip_front_matter("".join(content))
            if chapter_text:
                chapters.append(Chapter(title, chapter_text))
        if found_heading and chapters and chapters[0].title == "正文":
            chapters = chapters[1:]
        return chapters or [Chapter("正文", self._strip_front_matter(text))]

    def _safe_filename(self, value: str) -> str:
        cleaned = INVALID_FILENAME_CHARS.sub("_", value)
        return re.sub(r"\s+", " ", cleaned).strip(" ._") or "未命名"

    def _safe_chapter_name(self, title: str) -> str:
        return self._safe_filename(title)[:5]

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
        for path in self.final_files:
            if path:
                uploader.upload_file("book", path)
