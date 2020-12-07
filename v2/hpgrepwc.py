import sys
import os
import pickle
from datetime import timedelta, datetime as dt 
import time
import platform

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
if platform.system() == "Windows":
    os.system('color')




def main(argv):

    try:
        # Obter nome do ficheiro
        file = argv[0]

    except:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: hpgrepwc <ficheiro>")
        sys.exit(2)


    try:
        with open(file, "rb") as f:
            data = pickle.load(f)
        
    except FileNotFoundError as e:
        print(f"Ficheiro '{file}' não encontrado. Verifique o seu input.")
        sys.exit(2)

    ### Leitura dos dados e envio para stdout 
    
    output = []

    startDateStamp = data[2]
    duration = data[1]
    processData = data[0]
    opts = data[3]
    word = data[4]
    haltValue = data[5]

    output.append(f"\nPalavra a pesquisar: {colorWrite(word, 'red')}")
    output.append(f"Início da execução: {colorWrite(dt.strftime(data[2], '%d/%m/%Y, %H:%M:%S.%f'), 'green')}")
    output.append(f"Duração da execução: {colorWrite(timedelta(seconds = data[1]), 'green')}")

    sortedProcessData = dict()

    for process in processData:
        for loadData in processData[process]:
            if process not in sortedProcessData:
                sortedProcessData[process] = dict()
            if loadData[0].getFile() not in sortedProcessData[process]:
                sortedProcessData[process][loadData[0].getFile()] = []
            sortedProcessData[process][loadData[0].getFile()].append(loadData)

    files = set([processedFile for processedFile in getNested(sortedProcessData, process) for process in sortedProcessData])
    files = [colorWrite(argFile, 'green') for argFile in files]

    output.append(f"Ficheiros em argumento: " + ",\n                        ".join(files))

    fileSizes = {}
    totalProcessed = 0
    totalLC = 0
    totalWC = 0

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

            if file not in fileSizes:
                fileSizes[file] = fileSize
            totalProcessed += searchSum

            allLines = []
            fileWC = 0
            for loadData in fileData:
                for match in loadData[3]:
                    allLines.append(match.getLineNumber())
                    fileWC += match.getAmount()
                    

            fileLC = len(set(allLines))

            totalWC += fileWC
            totalLC += fileLC
            


            # print(getNested(sortedProcessData, process, file))
            output.append(f"        Tempo de pesquisa: {colorWrite(timedelta(seconds= timeSum), 'green')}")
            output.append(f"        Dimensão do ficheiro: {colorWrite(fileSize, 'green')} bytes")
            output.append(f"        Dimensão processada: {colorWrite(searchSum, 'green')} bytes ({colorWrite(searchPercentage, 'green')})")

            if any("-c" in opt for opt in opts):
                output.append(f"        Total de ocorrências: {colorWrite(fileWC, 'green')}")

            if any("-l" in opt for opt in opts):
                output.append(f"        Total de linhas com ocorrências: {colorWrite(fileLC, 'green')}")

    output.append("")

    totalSize = sum([fileSizes[file] for file in fileSizes])
    totalPercentage = round((totalProcessed/totalSize)*100)
    totalPercentageString = colorWrite(str(totalPercentage) + "%", 'green') if totalPercentage == 100 else colorWrite(str(totalPercentage) +"%", 'red')

    if any("-c" in opt for opt in opts):
        output.append(f"Total de ocorrências: {colorWrite(totalWC, 'green')}")

    if any("-l" in opt for opt in opts):
        output.append(f"Total de linhas com ocorrências: {colorWrite(totalLC, 'green')}")
    
    output.append(f"Total de bytes: {colorWrite(totalSize, 'green')}")
    output.append(f"Total de bytes processado: {colorWrite(totalProcessed, 'green')} ({totalPercentageString})")

    if haltValue == 2:
        output.append(colorWrite("[PARAGEM FORÇADA]", "red"))

    output.append("")

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


### CLASSES (O enunciado explicitamente limita a existência de ficheiros ".py"
#   a um máximo de 2. Desta forma, incluímos as classes necessárias ao funcionamento
#   do programa no ficheiro pgrepwc e no ficheiro hpgrepwc separadamente para que estes
#   possam funcionar indepentendemente um do outro.)


class Load:
    """
    TODO: Comentar
    """
    def __init__(self, file, offset, bytesToHandle):
        self._file = file
        self._offset = offset
        self._bytesToHandle = bytesToHandle
        self._end = offset + bytesToHandle - 1

    def getFile(self):
        return self._file

    def getOffset(self):
        return self._offset
    
    def getBytesToHandle(self):
        return self._bytesToHandle

    def getEnd(self):
        return self._end

class Match:
    """
    TODO: Comentar
    """
    def __init__(self, file, lineNumber, lineContent, amount):
        self._lineNumber = lineNumber
        self._lineContent = lineContent
        self._file = file
        self._amount = amount

    def getLineNumber(self):
        return self._lineNumber

    def getLineContent(self):
        return self._lineContent
    
    def getFile(self):
        return self._file

    def getAmount(self):
        return self._amount


if __name__ == "__main__":
    main(sys.argv[1:])

