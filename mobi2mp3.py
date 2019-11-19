from gtts import gTTS
import os
import pyttsx3
import time
import ffmpeg
import argparse

class Mobi(object):
    def __init__(self, name, language, outputpath,outputformat,rate=400):
        self.filename = name
        self.language = language
        self.outputpath = outputpath
        self.outputformat = outputformat
        self.rate = rate


    '''
    Change file to txt
    '''
    def to_txt(self):
        bookname = self.filename.rfind("/")
        self.bookname = self.filename[bookname + 1:]
        os.system(
            "ebook-convert {0} {2}/{1}.txt".format(self.filename, self.bookname,self.outputpath))

    '''
    use gTTS to read all txt for each 10 lines.
    Save all files name to a txt file for future usage. 
    '''
    def to_gMp3(self):
        if "_" in self.language:
            self.language = self.language.replace("_","-")
        with open(self.outputpath+"/"+self.bookname + ".txt") as f:
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
                    tts = gTTS(string, lang=self.language)
                    tts.save(
                        'result-{0}.mp3'.format(str(total_count).zfill(4)))
                    filelist.append(
                        'result-{0}.mp3'.format(str(total_count).zfill(4)))
                    count = 0
                    total_count += 1
                    string = ""
        with open(self.outputpath+"/result.txt", "w") as ff:
            for i in filelist:
                ff.write("file " + i + "\n")

    '''
    Use ffmpeg to concat all files
    '''
    def concat_mp3(self):
        os.system(
            "ffmpeg -f concat -i result.txt -c copy {0}.mp3".format(self.bookname))


    '''
    Use ffmpeg to concat all aiff files and change to mp3
    '''
    def concat_aiff(self, count):
        os.system(
            f"ffmpeg -f concat -i result-{count}.txt -c copy {count}-{self.bookname}.aiff")
        os.system(
            f"ffmpeg -i {count}-{self.bookname}.aiff -f mp3 -acodec libmp3lame -ab 192000 -ar 44100 {count}-{self.bookname}.mp3")
        os.system(f"rm result-{count}.txt")

    '''
    Choose language for sepcific language and read via OSX tts
    '''
    def to_aiff(self):
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        res = []
        for i in voices:
            if (i.languages[0] == self.language and i.name=="Ting-Ting") or (i.languages[0] == self.language and i.name=="Alice"):
                engine.setProperty('voice', i.id)
        if self.language=="zh_CN":
            engine.setProperty('rate', 400)
        else:
            engine.setProperty('rate', 200)
        with open(self.outputpath+"/"+self.bookname + ".txt") as f:
            string = ""
            count = 0
            total_count = 0
            for line in f.readlines():
                line = line.replace("\n", "")
                if len(line) > 0:
                    string += line
                    count += 1
                if count > 100 and self.language=="zh_CN" or count>0 and self.language=="en_US":
                    engine.save_to_file(
                        string, 'result-{0}.aiff'.format(total_count))
                    res.append('result-{0}.aiff'.format(total_count))
                    count = 0
                    total_count += 1
                    string = ""
            engine.save_to_file(
                        string, 'result-{0}.aiff'.format(total_count))
            res.append('result-{0}.aiff'.format(total_count))
            
        k = 0
        for i in res:
            with open(self.outputpath+f"/result-{k//10}.txt", "a") as ff:
                ff.write("file " + i + "\n")
            k += 1
        engine.runAndWait()
        return k//10
    def run(self):
        if self.outputformat == 'osx':
            self.to_txt()
            rs = self.to_aiff()
            for i in range(rs+1):
                self.concat_aiff(i)
            os.system("rm *.aiff")
        if self.outputformat == 'gtts':
            self.to_txt()
            self.to_gMp3()
            self.concat_mp3()
'''
test function with test.mobi, if it did not find save_to_file on MacOS, please install the latest pyttsx3 from github repo
pip install git+git://github.com/nateshmbhat/pyttsx3
'''
def test_aiff():
    book = Mobi(
    "test.mobi", "en_US",".",'osx',200)
    book.run()
    

def test_mp3():
    book = Mobi(
    "test.mobi", "en_US",".",'osx')
    book.run()

'''
parse inputs
'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--inputfile',help='input file path')
    parser.add_argument('-o','--outputpath', help='output file path')
    parser.add_argument('-l','--language', help='language setting like zh_CN/en_US',default='zh_CN')
    parser.add_argument('-f','--format', help='format setting like gtts/osx',default='osx')
    parser.add_argument('-r','--rate', help='rate setting 100-400',default='400')
    args = parser.parse_args()
    inputfile = vars(args)["inputfile"]
    outputpath = vars(args)["outputpath"]
    language = vars(args)["language"]
    outputformat = vars(args)["format"]
    rate = vars(args)["rate"]
    book = Mobi(inputfile, language,outputpath,outputformat,rate)
    book.run()

if __name__ == '__main__':
    main()
    

'''
engine = pyttsx3.init()
voices = engine.getProperty('voices')
for i in voices:
    if i.languages[0] == 'zh_CN':
        engine.setProperty('voice', i.id)
engine.say('在疲劳之后，遵从自己的生理系统的召唤，小睡一下，可能是个很好的方法。', 'result.aiff')
engine.runAndWait()
'''
#tts = gTTS("alexa, what's the weather today", lang='en-US')
#tts.save('alexa.mp3')
