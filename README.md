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
usage: mobi2mp3.py [-h] [-i INPUTFILE] [-o OUTPUTPATH] [-l LANGUAGE]
                   [-f FORMAT] [-r RATE]

optional arguments:
  -h, --help            show this help message and exit
  -i INPUTFILE, --inputfile INPUTFILE
                        input file path
  -o OUTPUTPATH, --outputpath OUTPUTPATH
                        output file path
  -l LANGUAGE, --language LANGUAGE
                        language setting like zh_CN/en_US
  -f FORMAT, --format FORMAT
                        format setting like gtts/osx
  -r RATE, --rate RATE  rate setting 100-400
```