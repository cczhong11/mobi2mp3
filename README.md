# mobi2mp3

This file could help you change mobi file to mp3 or `aiff`. This file work on Mac, it could be used in Linux easily.

## requirement

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

3. install all requirement `pip install -r requirements.txt`

## Main idea

Change all mobi, epub, pdf to txt file, use tts service read them. Save them to local file and concat together using ffmpeg.

## Usage 

```
usage: main.py [OPTIONS]

Options:
  -i, --inputfile TEXT   input file path
  -o, --outputpath TEXT  output file path
  -l, --language TEXT    language setting like zh_CN/en_US
  -r, --rate INTEGER     rate setting 100-400
  --tts [mac_say|volc_stream]
                          tts engine name
  --voice TEXT           macOS voice name
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
  --no_upload
  --debug
  --help                 Show this message and exit.
```

Notes:
  - `volc_stream` requires an access key via `--volc-access-key` or `VOLC_ACCESS_KEY`.
  - `--volc-config` can point to a JSON file like `key.json` with a `volc` object.

Example CLI:
```
# macOS say
python main.py -i /path/to/book.epub --voice "Tingting"

# volc stream with config file
python main.py -i /path/to/book.epub --tts volc_stream --volc-config key.json
```
