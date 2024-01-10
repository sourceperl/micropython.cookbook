"""
See app.py for details.

Here we just import some app objects to populate REPL for autocomplete.
"""

from app import analyze, dump, save, serial, version


# override default help()
def help():
    print('')
    print(open('help.txt', 'r').read())


# remove unused symbols to clean REPL namespace
del machine, rp2
