class TTSEngine:
    output_format = "aiff"
    text_char_limit = None
    combine_group_size = 10

    def synthesize(self, text: str, output_path: str) -> None:
        raise NotImplementedError
