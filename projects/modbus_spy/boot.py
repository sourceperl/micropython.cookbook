from app import serial, dump, analyze, on, off, save
from app import _dump_rt, _analyze_rt


# override default help()
def help():
    print('')
    print(open('help.txt', 'r').read())


# remove unused symbols to clean REPL namespace
del machine, rp2
