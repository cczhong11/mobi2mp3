import click
import pyttsx3
from book import Book

@click.command()
@click.option("-i","--inputfile",help='input file path',type=str)
@click.option('-o','--outputpath', help='output file path', default="/Users/tczhong/Documents/mobi2mp3/")
@click.option('-l','--language', help='language setting like zh_CN/en_US',default='zh_CN')
@click.option('-r','--rate', help='rate setting 100-400',default=400, type=int)
def main(inputfile:str, outputpath:str, language:str, rate:int):
    b = Book(inputfile, outputpath, language, rate)
    b.to_txt()
    b.split_book()
    b.output_tmp()
    for i in range(b.file_count):
        b.combine_aiff(i)
    book.clean()

if __name__ == '__main__':
    main()