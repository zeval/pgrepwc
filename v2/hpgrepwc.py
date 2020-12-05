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
        os.system("pwd")
        with open(file, "rb") as f:
            data = pickle.load(f)
        
    except FileNotFoundError as e:
        print(f"Ficheiro '{file}' não encontrado. Verifique o seu input.")
        import traceback;traceback.print_exc()
        print(os.system("ls"))
        sys.exit(2)

    ### Leitura dos dados e envio para stdout 
    
    output = []

    startDateStamp = data[2]
    duration = data[1]
    processData = data[0]
    opts = data[3]
    word = data[4]

    output.append(f"\nPalavra a pesquisar: {colorWrite(word, 'red')}")
    output.append(f"Início da execução: {colorWrite(data[2], 'green')}")
    output.append(f"Duração da execução: {colorWrite(data[1], 'green')}")

    sortedProcessData = dict()

    for process in processData:
        for loadData in processData[process]:
            if process not in sortedProcessData:
                sortedProcessData[process] = dict()
            if loadData[0].getFile() not in sortedProcessData[process]:
                sortedProcessData[process][loadData[0].getFile()] = []
            sortedProcessData[process][loadData[0].getFile()].append(loadData)

    # for process in sortedProcessData:
    #     print(sortedProcessData[process].keys())


    # print(getNested(sortedProcessData, 2307))

    for process in sortedProcessData:
        output.append(f"\nProcesso: {colorWrite(process, 'green')}")
        files = getNested(sortedProcessData, process)
        
        for file in files:
            fileData = getNested(sortedProcessData, process, file)
            # print(fileData)

            assert 1==1

            output.append(f"    Ficheiro: {colorWrite(file, 'green')}")
            timeSum = sum([loadData[2] for loadData in fileData])
            fileSize = fileData[0][1]
            searchSum = sum([loadData[0].getBytesToHandle() for loadData in fileData])
            searchPercentage = str(round((searchSum/fileSize)*100)) + "%"

            allLines = []
            totalWC = 0
            for loadData in fileData:
                for match in loadData[3]:
                    allLines.append(match.getLineNumber())
                    totalWC += match.getAmount()
                    

            totalLC = len(set(allLines))
            


            # print(getNested(sortedProcessData, process, file))
            output.append(f"        Tempo de pesquisa: {colorWrite(timeSum, 'green')}")
            output.append(f"        Dimensão do ficheiro: {colorWrite(fileSize, 'green')} bytes")
            output.append(f"        Dimensão processada: {colorWrite(searchSum, 'green')} bytes ({colorWrite(searchPercentage, 'green')})")

            if any("-c" in opt for opt in opts):
                output.append(f"        Total de ocorrências: {colorWrite(totalWC, 'green')}")

            if any("-l" in opt for opt in opts):
                output.append(f"        Total de linhas com ocorrências: {colorWrite(totalLC, 'green')}")


    for line in output:
        print(line)




def colorWrite(text, color):
    if color == "green":
        return GREEN_START + str(text) + COLOR_END
    
    if color == "red":
        return RED_START + str(text) + COLOR_END


def getNested(data, *args):
    if args and data:
        element  = args[0]
        if element:
            value = data.get(element)
            return value if len(args) == 1 else getNested(value, *args[1:])

if __name__ == "__main__":
    main(sys.argv[1:])

