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
  --no_upload
  --help                 Show this message and exit.
```