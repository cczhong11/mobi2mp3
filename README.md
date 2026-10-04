# mobi2mp3

This tool converts mobi/epub/pdf books into spoken audio files. It supports macOS `say`, Volcengine streaming TTS, and MLX Qwen3 TTS on Apple Silicon.

## Standalone Gemini Batch text TTS

`mobi2mp3-gemini-text` is deliberately separate from the book conversion
providers. Give it a user-supplied UTF-8 `.txt` file; the first run submits a
Gemini Batch job and a later identical run downloads WAV chunks and merges one
MP3. It reads the credential only from `google.key` in the supplied JSON
config; it does not upload to S3.

```bash
uv run mobi2mp3-gemini-text \
  --input /path/to/text.txt \
  --output /path/to/result.mp3 \
  --config /path/to/key.json
```

## Requirements

1. install calibre

```
# MAC
brew cask install calibre
# Debian
sudo apt-get install calibre
```

2. install ffmpeg

```
# MAC
brew cask install ffmpeg
# Debian
sudo apt-get install ffmpeg
```

3. install dependencies with uv

```bash
uv sync
```

4. for `mlx_qwen3`, use Apple Silicon. The first run will also download the selected Hugging Face model.

## Main idea

EPUB files are read using their spine and table of contents so each final MP3 is one
chapter. Other formats are converted to text and split on common Chinese/English
chapter headings. A long chapter may use several temporary TTS chunks, which are
joined into a single chapter file by ffmpeg.

Final files use `book_zero-padded-index_chapter-title-first-5-chars.mp3`, for example:
`奇风岁月_000_第一章风.mp3`.

## Usage

### Check Volcengine billing balance

`mobi2mp3-volc-balance` queries the official Volcengine Billing API
(`QueryBalanceAcct`) and prints the account's available cash/credit balance.
It is **not** a per-TTS-token or per-resource-package counter: the streaming
TTS application token cannot access billing, and the public TTS documentation
does not expose a dedicated remaining-quota API.

Create/use a least-privilege Volcengine IAM key permitted to call
`billing:QueryBalanceAcct`, then provide it through a secret manager as
`VOLC_BILLING_ACCESS_KEY_ID` and `VOLC_BILLING_SECRET_ACCESS_KEY`:

```bash
uv run mobi2mp3-volc-balance
```

For automation, add `--json-output`. Never place keys in this repository.

```
uv run mobi2mp3 [OPTIONS]

Options:
  -i, --inputfile TEXT   input file path
  -o, --outputpath TEXT  output file path
  -l, --language TEXT    language setting like zh_CN/en_US
  -r, --rate INTEGER     rate setting 100-400
  --tts [mac_say|volc_stream|mlx_qwen3]
                          tts engine name
  --voice TEXT           voice name for macOS say or mlx qwen3
  --volc-app-id TEXT     volcengine app id
  --volc-access-key TEXT
                          volcengine access key
  --volc-resource-id TEXT
                          volcengine resource id
  --volc-speaker TEXT    volcengine speaker name
  --volc-model TEXT      volcengine model version
  --volc-sample-rate INTEGER
                          volcengine sample rate
  --volc-bit-rate INTEGER
                          volcengine bit rate
  --volc-config TEXT      volcengine config json path
  --mlx-model TEXT        mlx qwen3 model repo id
  --mlx-language TEXT     mlx qwen3 language name, e.g. English/Chinese/Japanese/Korean
  --mlx-instruct TEXT     mlx qwen3 style or voice design instruction
  --mlx-ref-audio TEXT    mlx qwen3 custom voice reference audio path
  --mlx-ref-text TEXT     mlx qwen3 reference audio transcript
  --mlx-speed FLOAT       mlx qwen3 speed multiplier
  --mlx-max-tokens INTEGER
                          mlx qwen3 max generation tokens
  --no_upload
  --debug
  --help                  Show this message and exit.
```

Notes:
  - `volc_stream` requires an access key via `--volc-access-key` or `VOLC_ACCESS_KEY`.
  - `--volc-config` can point to a JSON file like `key.json` with a `volc` object.
  - `mlx_qwen3` uses [`mlx-audio`](https://github.com/Blaizzy/mlx-audio) and now defaults to `mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-bf16`.
  - For stable voice across long books, provide `--mlx-ref-audio` and preferably `--mlx-ref-text` so all chunks reuse the same reference voice.
  - With the default `CustomVoice` model, the built-in speaker defaults to `serena`.
  - `mlx_qwen3` maps `zh_CN` to `Chinese`, `en_US` to `English`, `ja_JP` to `Japanese`, and `ko_KR` to `Korean`.

Example CLI:
```bash
# macOS say
uv run mobi2mp3 -i /path/to/book.epub --voice "Tingting"

# volc stream with config file
uv run mobi2mp3 -i /path/to/book.epub --tts volc_stream --volc-config key.json


# mlx qwen3 custom voice on Apple Silicon
uv run mobi2mp3 -i /path/to/book.epub --tts mlx_qwen3 --mlx-language Chinese \
  --mlx-ref-audio /path/to/reference.wav \
  --mlx-ref-text "这是一段参考音频对应的文字"

# mlx qwen3 voice design model
uv run mobi2mp3 -i /path/to/book.epub \
  --tts mlx_qwen3 \
  --mlx-model mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16 \
  --mlx-language Chinese \
  --mlx-instruct "Warm audiobook narrator with calm pacing"
```

Useful UV commands:

```bash
uv sync
uv run mobi2mp3 --help
uv add requests
uv add --upgrade mlx-audio
```
