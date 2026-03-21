# mobi2mp3

This tool converts mobi/epub/pdf books into spoken audio files. It supports macOS `say`, Volcengine streaming TTS, and MLX Qwen3 TTS on Apple Silicon.

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

Change all mobi, epub, pdf to txt file, use tts service read them. Save them to local file and concat together using ffmpeg.

## Usage

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
