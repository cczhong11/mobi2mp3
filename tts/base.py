class TTSEngine:
    output_format = "aiff"
    text_char_limit = None

    def synthesize(self, text: str, output_path: str) -> None:
        raise NotImplementedError
