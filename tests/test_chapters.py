import tempfile
import unittest
import zipfile
from pathlib import Path

from book import Book
from epub_chapters import parse_epub


class DummyTTS:
    text_char_limit = 8
    output_format = "mp3"


class ChapterTests(unittest.TestCase):
    def test_parse_epub_uses_toc_titles_and_spine_order(self):
        with tempfile.TemporaryDirectory() as directory:
            epub = Path(directory) / "book.epub"
            with zipfile.ZipFile(epub, "w") as archive:
                archive.writestr(
                    "META-INF/container.xml",
                    '<container><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>',
                )
                archive.writestr(
                    "OPS/book.opf",
                    '<package><manifest><item id="toc" href="toc.ncx" media-type="application/x-dtbncx+xml"/>'
                    '<item id="c1" href="c1.xhtml" media-type="application/xhtml+xml"/>'
                    '<item id="c2" href="c2.xhtml" media-type="application/xhtml+xml"/></manifest>'
                    '<spine toc="toc"><itemref idref="c1"/><itemref idref="c2"/></spine></package>',
                )
                archive.writestr(
                    "OPS/toc.ncx",
                    '<ncx><navMap><navPoint><navLabel><text>第一章风起</text></navLabel>'
                    '<content src="c1.xhtml"/></navPoint><navPoint><navLabel><text>第二章云涌</text></navLabel>'
                    '<content src="c2.xhtml"/></navPoint></navMap></ncx>',
                )
                archive.writestr("OPS/c1.xhtml", "<html><body><h1>一</h1><p>甲乙丙</p></body></html>")
                archive.writestr("OPS/c2.xhtml", "<html><body><h1>二</h1><p>丁戊己</p></body></html>")

            chapters = parse_epub(epub)

        self.assertEqual([chapter.title for chapter in chapters], ["第一章风起", "第二章云涌"])
        self.assertIn("甲乙丙", chapters[0].content)

    def test_long_chapter_is_chunked_but_keeps_one_chapter_output(self):
        with tempfile.TemporaryDirectory() as directory:
            text = Path(directory) / "我的书.txt"
            text.write_text("第一章风起\n甲乙丙丁。戊己庚辛。\n第二章云涌\n壬癸。", encoding="utf-8")
            book = Book(str(text), directory, "zh_CN", DummyTTS())
            Path(book.book_path).parent.mkdir(parents=True, exist_ok=True)
            Path(book.book_path).write_text(text.read_text(encoding="utf-8"), encoding="utf-8")

            book.split_book()

            self.assertEqual(book.file_count, 2)
            self.assertGreater(len(book.chapter_chunks[0]), 1)
            self.assertEqual(book._safe_chapter_name(book.chapters[0].title), "第一章风起")
            self.assertEqual(
                Path(book.mp3_path) / f"{book.book}_{book._safe_chapter_name(book.chapters[0].title)}_0.mp3",
                Path(directory) / "mp3" / "我的书_第一章风起_0.mp3",
            )

    def test_combine_uses_book_short_chapter_and_index_filename(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "我的书.txt"
            source.write_text("第一章风起之后\n正文。", encoding="utf-8")
            book = Book(str(source), directory, "zh_CN", DummyTTS())
            Path(book.mp3_path).mkdir(parents=True)
            book.chapters = [type("Chapter", (), {"title": "第一章风起之后"})()]
            Path(book.tmp_path, "chapter-0.txt").write_text("", encoding="utf-8")
            Path(book.tmp_path, "chapter-0.mp3").write_bytes(b"audio")

            book.combine_audio(0)

            output = Path(book.mp3_path, "我的书_第一章风起_0.mp3")
            self.assertTrue(output.exists())
            self.assertEqual(book.final_files, [str(output)])


if __name__ == "__main__":
    unittest.main()
