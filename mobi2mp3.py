from gtts import gTTS
import os
import pyttsx3
import time
import ffmpeg


class Mobi(object):
    def __init__(self, name, language):
        self.filename = name
        self.language = language

    def to_txt(self):
        bookname = self.filename.rfind("/")
        self.bookname = self.filename[bookname + 1:]
        # TODO: set output path
        os.system(
            "ebook-convert {0} {1}.txt".format(self.filename, self.bookname))

    def to_gMp3(self):
        with open(self.bookname + ".txt") as f:
            string = ""
            count = 0
            total_count = 0
            filelist = []
            for line in f.readlines():
                line = line.replace("\n", "")
                if len(line) > 0:
                    string += line
                    count += 1
                    print(line)
                if count > 10:
                    tts = gTTS(string, lang='zh-CN')
                    tts.save(
                        'result-{0}.mp3'.format(str(total_count).zfill(4)))
                    filelist.append(
                        'result-{0}.mp3'.format(str(total_count).zfill(4)))
                    count = 0
                    total_count += 1
                    string = ""
        with open("result.txt", "w") as ff:
            for i in filelist:
                ff.write("file " + i + "\n")

    def concat_mp3(self):
        os.system(
            "ffmpeg -f concat -i result.txt -c copy {0}.mp3".format(self.bookname))

    def concat_aiff(self):
        os.system(
            "ffmpeg -f concat -i result.txt -c copy {0}.aiff".format(self.bookname))
        os.system(
            "ffmpeg -i {0}.aiff -f mp3 -acodec libmp3lame -ab 192000 -ar 44100 {0}.mp3".format(self.bookname))
        os.system("rm *.aiff")
        os.system("rm result.txt")

    def to_aiff(self):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        res = []
        for i in voices:
            if i.languages[0] == 'zh_CN':
                engine.setProperty('voice', i.id)
        engine.setProperty('rate', 400)
        with open(self.bookname + ".txt") as f:
            string = ""
            count = 0
            total_count = 0
            for line in f.readlines():
                line = line.replace("\n", "")
                if len(line) > 0:
                    string += line
                    count += 1
                    print(line)
                if count > 20:
                    engine.save_to_file(
                        string, 'result-{0}.aiff'.format(total_count))
                    res.append('result-{0}.aiff'.format(total_count))
                    count = 0
                    total_count += 1
                    string = ""
        with open("result.txt", "w") as ff:
            for i in res:
                ff.write("file " + i + "\n")
        engine.runAndWait()


book = Mobi(
    "/Users/tczhong/Dropbox/待读/有效学习_-_乌尔里希伯泽尔.mobi", "zh_CN")
book.to_txt()
book.to_aiff()
# book.concat_mp3()
book.concat_aiff()
'''
engine = pyttsx3.init()
voices = engine.getProperty('voices')
for i in voices:
    if i.languages[0] == 'zh_CN':
        engine.setProperty('voice', i.id)
engine.say('在疲劳之后，遵从自己的生理系统的召唤，小睡一下，可能是个很好的方法。', 'result.aiff')
engine.runAndWait()
'''
# tts = gTTS('在疲劳之后，遵从自己的生理系统的召唤，小睡一下，可能是个很好的方法。', lang='zh-CN')
# tts.save('hello.mp3')
