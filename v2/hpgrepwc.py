import sys
import os
import pickle
import datetime
from Load import Load
from Match import Match
import time
import platform

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
if platform.system() == "Windows":
    os.system('color')


def main(argv):
    global args

    try:
        # Obter nome do ficheiro
        file = argv[0]

    except:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: hpgrepwc <ficheiro>")
        sys.exit(2)


    try:
        with open("test", "rb") as f:
            print(f.read())
            data = pickle.load(f)

    except FileNotFoundError as e:
        print(e)
    





def colorWrite(text, color):
    if color == "green":
        return GREEN_START + str(text) + COLOR_END
    
    if color == "red":
        return RED_START + str(text) + COLOR_END

if __name__ == "__main__":
    main(sys.argv[1:])

