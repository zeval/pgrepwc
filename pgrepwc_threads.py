import sys
import os
import re
import getopt
import platform
from threading import Thread, current_thread
from math import ceil

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
if platform.system() == "Windows":
    os.system('color')

# Definição de variáveis globais
totalWC = 0
totalLC = 0


# TODO: Mutex lock


def main(argv):

    try:
        # Obter argumentos, opções
        opts, args = getopt.getopt(argv, "clp:")

    except getopt.GetoptError:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: pgrepwc [-c|-l] [-p n] palavra {ficheiros}")
        sys.exit(2)

    # Por omissão, todas as pesquisas/contagens são feitas no processo pai, pelo que não se dá paralelização
    numberOfThreads = 1
    parallelization = False

    if len(args) == 1:  # Caso apenas seja dada a palavra, e não os nomes dos ficheiros
        print("Introduza os nomes dos ficheiros a pesquisar, numa linha, separados por espaços:")
        allFiles = removeDuplicates(input().split())  # Evitar pesquisar nos mesmos ficheiros várias vezes
        print()  # Razões Estéticas
    else:
        allFiles = removeDuplicates(args[1:])  # Evitar pesquisar nos mesmos ficheiros várias vezes

    for opt in opts:
        if opt[0] == "-p":
            numberOfThreads = int(opt[1])
            parallelization = True  # Ativar paralelização caso a opção "-p n" seja utilizada
            if numberOfThreads == 0:  # Evitar erros se for pedido "-p 0", desligando a paralelização
                parallelization = False

    if numberOfThreads > len(allFiles):  # Evitar ciclos do for desnecessários, utilizar no máximo tantas
        numberOfThreads = len(allFiles)  # threads como ficheiros referidos

    if parallelization:

        # Definição do número estimado de ficheiros a lidar por cada thread
        numberOfFilesPerThread = ceil(len(allFiles)/numberOfThreads)
        t = []

        # Divisão do trabalho pelas várias threads
        for process in range(numberOfThreads):
            while len(allFiles) > 0:

                filesToHandle = []

                for i in range(numberOfFilesPerThread):

                    if len(allFiles) >= 1:
                        filesToHandle.append(allFiles.pop(0))

                t.append(Thread(target=matchFinder, args=(filesToHandle, opts, args[0], parallelization)))

        for thread in t:
            thread.start()
        for thread in t:
            thread.join()

    else:  # Caso a paralelização esteja desligada, todo o trabalho é feito sem threading
        matchFinder(allFiles, args, args[0], parallelization)

    print()  # estético
    print(f"Thread PAI: {current_thread().ident}\n")

    if any("-c" in opt for opt in opts):
        print(f"Total de ocorrências: {totalWC}")

    if any("-l" in opt for opt in opts):
        print(f"Total de linhas: {totalLC}")


def matchFinder(files, args, word, parallelization):

    global totalLC
    global totalWC

    # Expressão regular responsável por identificar instâncias da palavra isolada
    regex = fr"\b{word}\b"

    for file in files:
        output = []
        wc = 0
        lc = 0
        try:
            with open(file, "r", encoding="utf-8") as f:
                print(f"=========================")
                if parallelization:
                    output.append(f"Thread ID: {current_thread().ident}")
                output.append(f"Ficheiro: {file}\n")

                lineNumber = 0

                # lines = f.readlines()

                # for lineIndex in range(len(lines)):
                for line in f:
                    lineNumber += 1
                    matches = re.findall(regex, line)
                    if matches:
                        lc += 1
                        wc += len(matches)

                        # Uso do método re.sub() para substituir todas as instâncias da palavra isolada
                        # por instâncias da mesma em versão colorida
                        processedLine = re.sub(regex, RED_START + word + COLOR_END, line)
                        output.append(f"{GREEN_START}{lineNumber}{COLOR_END}: {processedLine}")

                for line in output:
                    print(line)

                print()
                for opt in args:
                    if opt[0] == "-c":
                        print(f"Total de ocorrências da palavra: {wc}.\nA enviar para o processo pai...\n")
                    if opt[0] == "-l":
                        print(f"Total de linhas em que a palavra apareceu: {lc}.\nA enviar para o processo pai...\n")
                print(f"=========================\n")

                totalWC += wc
                totalLC += lc
        except FileNotFoundError:
            print(f"Ficheiro '{file}' não encontrado. Verifique o seu input.")


def removeDuplicates(inputList):
    """
    Função responsável por retirar elementos duplicados de uma lista.
    Requires: inputList diferente de None.
    Ensures: uma lista semelhante a inputList, sem elementos duplicados.
    """
    return list(dict.fromkeys(inputList))          


if __name__ == "__main__":
    main(sys.argv[1:])
