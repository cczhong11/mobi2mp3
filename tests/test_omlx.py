import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import json

from tts import CliTTSOptions, build_tts_from_cli


class OmlxTests(unittest.TestCase):
    def test_server_receives_model_auth_and_language_and_returns_audio(self):
        received = {}

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                received["path"] = self.path
                received["auth"] = self.headers.get("Authorization")
                received["payload"] = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                self.send_response(200)
                self.send_header("Content-Type", "audio/mpeg")
                self.end_headers()
                self.wfile.write(b"test-audio")

            def log_message(self, *args):
                pass

        with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                with patch.dict("os.environ", {"OMLX_API_KEY": "test-key"}):
                    engine = build_tts_from_cli("omlx", "zh_CN", 400, CliTTSOptions(
                        omlx_url=f"http://127.0.0.1:{server.server_port}/v1/",
                        omlx_model="installed-model",
                        omlx_instruct="Calm narration",
                    ))
                with tempfile.TemporaryDirectory() as directory:
                    output = Path(directory) / "nested" / "speech.mp3"
                    engine.synthesize("你好。", str(output))
                    self.assertEqual(output.read_bytes(), b"test-audio")
            finally:
                server.shutdown()
                thread.join()

        self.assertEqual(received["path"], "/v1/audio/speech")
        self.assertEqual(received["auth"], "Bearer test-key")
        self.assertEqual(received["payload"]["model"], "installed-model")
        self.assertEqual(received["payload"]["language"], "Chinese")
        self.assertEqual(received["payload"]["voice"], "serena")
        self.assertEqual(received["payload"]["response_format"], "mp3")
        self.assertEqual(received["payload"]["instructions"], "Calm narration")

    def test_errors_do_not_create_audio_files(self):
        engine = build_tts_from_cli("omlx", "en_US", 400, CliTTSOptions())
        for status, content_type, audio in [(401, "application/json", b"error"),
                                            (200, "application/json", b"{}"),
                                            (200, "audio/mpeg", b"")]:
            with self.subTest(status=status, content_type=content_type, audio=audio):
                with patch("tts.omlx.requests.post") as post:
                    response = post.return_value.__enter__.return_value
                    response.status_code = status
                    response.headers = {"Content-Type": content_type}
                    response.content = audio
                    with tempfile.TemporaryDirectory() as directory:
                        output = Path(directory) / "speech.mp3"
                        with self.assertRaises(RuntimeError):
                            engine.synthesize("Hello.", str(output))
                        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
