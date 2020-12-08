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

# Constantes data

START_DATE_STAMP = 2
DURATION = 1
PROCESS_DATA = 0
OPTS = 3
WORD = 4
HALT_VALUE = 5

# Constantes loadData

LOAD = 0
TIME_TAKEN = 2
LOAD_MATCHES = 3

# Constantes fileData

SIZE = 1


def main(argv):

    try:
        # Obter nome do ficheiro.
        file = argv[0]

    except:
        # Mensagem de ajuda caso o comando seja mal formado.
        print("Utilização: hpgrepwc <ficheiro>")
        sys.exit(2)


    try:
        with open(file, "rb") as f:
            data = pickle.load(f)
        
    except:
        print(f"Ficheiro '{file}' não encontrado ou inválido. Verifique o seu input.")
        sys.exit(2)

    ### Leitura dos dados e envio para stdout.
    
    output = []

    # Obtenção de dados a partir do tuplo de dados no ficheiro binário.
    startDateStamp = data[START_DATE_STAMP]
    duration = data[DURATION]
    processData = data[PROCESS_DATA]
    opts = data[OPTS]
    word = data[WORD]
    haltValue = data[HALT_VALUE]


    # Adicionar campos ao output.
    output.append(f"\nPalavra a pesquisar: {colorWrite(word, 'red')}")
    output.append(f"Início da execução: {colorWrite(dt.strftime(startDateStamp, '%d/%m/%Y, %H:%M:%S.%f'), 'green')}")
    output.append(f"Duração da execução: {colorWrite(timedelta(seconds = duration), 'green')}")


    
    # Organização de dados: passagem e um dicionário partilhado de estrutura
    # orientada a processos, para um dicionário bi-dimensional local de estrutura 
    # organizada por PROCESSOS -> FICHEIROS, em que a chave de primeira dimensão
    # é referente ao processo e de segunda dimensão é referente ao ficheiro. 
    # Esta estrutura mais organizada permite-nos saber com quanto de cada ficheiro 
    # é que cada processo lidou.

    sortedProcessData = dict()

    for process in processData:
        for loadData in processData[process]:
            if process not in sortedProcessData:
                sortedProcessData[process] = dict()
            if loadData[LOAD].getFile() not in sortedProcessData[process]:
                sortedProcessData[process][loadData[LOAD].getFile()] = []
            sortedProcessData[process][loadData[LOAD].getFile()].append(loadData)

    # Obtenção dos vários nomes de ficheiros numa lista de valores únicos.
    files = set([processedFile for processedFile in getNested(sortedProcessData, process) for process in sortedProcessData])

    # Transformação de todos esses nomes na sua respetiva versão colorida.
    files = [colorWrite(argFile, 'green') for argFile in files]

    # Adicionar campos ao output.
    output.append(f"Ficheiros em argumento: " + ",\n                        ".join(files))

    # Inicialização de variáveis importantes ao resto do processo.
    fileSizes = {}
    totalProcessed = 0
    totalLC = 0
    totalWC = 0


    for process in sortedProcessData:
        
        output.append(f"\nProcesso: {colorWrite(process, 'green')}")

        # Uso da função getNested para aceder à primeira dimensão do dicionário sortedProcessData
        # e obter os nomes dos vários ficheiros com os quais o processo lidou.
        files = getNested(sortedProcessData, process)
        

        for file in files:
            # Uso da função getNested para aceder à segunda dimensão do dicionário sortedProcessData
            # e obter informação sobre o processamento do atual ficheiro por parte do atual processo.
            fileData = getNested(sortedProcessData, process, file)

            output.append(f"    Ficheiro: {colorWrite(file, 'green')}")

            # Cálculo do tempo total demorado para o processo lidar com o ficheiro atual.
            timeSum = sum([loadData[TIME_TAKEN] for loadData in fileData])

            fileSize = fileData[0][SIZE]

            # Cálculo do total de bytes do ficheiro com o qual o processo atual lidou
            # e cálculo da respetiva percentagem relativamente ao tamanho total do ficheiro
            # em questão.
            searchSum = sum([loadData[LOAD].getBytesToHandle() for loadData in fileData])
            searchPercentage = (str(round((searchSum/fileSize)*100, 1)) + "%").replace(".0", "")


            # Incrementação do total de bytes analisado.
            totalProcessed += searchSum

            # Organização de dados: dicionário utilizado para registar o tamanho de cada
            # ficheiro referenciado.
            if file not in fileSizes:
                fileSizes[file] = fileSize


            allLines = []
            fileWC = 0
            

            # Criação de lista que inclui os números de todas as linhas com ocorrências
            # (útil para saber o total de linhas com ocorrências encontradas neste ficheiro).
            for loadData in fileData:
                for match in loadData[LOAD_MATCHES]:
                    allLines.append(match.getLineNumber())
                    fileWC += match.getAmount()
            fileLC = len(set(allLines))


            # Incrementação do total de bytes analisado.
            totalWC += fileWC
            totalLC += fileLC

            # Adicionar campos ao output.
            output.append(f"        Tempo de pesquisa: {colorWrite(timedelta(seconds= timeSum), 'green')}")
            output.append(f"        Dimensão do ficheiro: {colorWrite(fileSize, 'green')} bytes")
            output.append(f"        Dimensão processada: {colorWrite(searchSum, 'green')} bytes ({colorWrite(searchPercentage, 'green')})")

            # Imprimir output consoante a presença de opções nos argumentos do utilizador.
            if any("-c" in opt for opt in opts):
                output.append(f"        Total de ocorrências: {colorWrite(fileWC, 'green')}")

            if any("-l" in opt for opt in opts):
                output.append(f"        Total de linhas com ocorrências: {colorWrite(fileLC, 'green')}")

    output.append("")


    # Cálculo da soma do tamanho do agregado de ficheiros e respetiva percentagem
    # relativamente ao total de bytes analisado.
    totalSize = sum([fileSizes[file] for file in fileSizes])
    totalPercentage = str(round((totalProcessed/totalSize)*100, 1)).replace(".0", "")
    totalPercentageString = colorWrite(str(totalPercentage) + "%", 'green') if totalPercentage == "100" else colorWrite(str(totalPercentage) +"%", 'red')


    # Imprimir output consoante a presença de opções nos argumentos do utilizador.
    if any("-c" in opt for opt in opts):
        output.append(f"Total de ocorrências: {colorWrite(totalWC, 'green')}")

    if any("-l" in opt for opt in opts):
        output.append(f"Total de linhas com ocorrências: {colorWrite(totalLC, 'green')}")
    

    # Adicionar campos ao output.
    output.append(f"Total de bytes: {colorWrite(totalSize, 'green')}")
    output.append(f"Total de bytes processado: {colorWrite(totalProcessed, 'green')} ({totalPercentageString})")

    # Imprimir a flag "[PARAGEM FORÇADA]" caso o utilizador tenha forçado a paragem via sinal SIGINT.
    if haltValue == 2:
        output.append(colorWrite("[PARAGEM FORÇADA]", "red"))

    output.append("")

    for line in output:
        print(line)


def colorWrite(text, color):
    """
    Devolve o texto recebido na cor especificada.
    Requires: text é um string e color é 'green' ou 'red'.
    Ensures: text rodeado pelos códigos de cor referentes à 
    cor especificada.
    """
    if color == "green":
        return GREEN_START + str(text) + COLOR_END
    
    if color == "red":
        return RED_START + str(text) + COLOR_END


def getNested(data, *args):
    """
    Permite aceder a dicionários ninhados (várias dimensões).
    Requires: data é um dicionário e args são chaves dos dicionários internos.
    """
    if args and data:
        element  = args[0]
        if element:
            value = data.get(element)
            return value if len(args) == 1 else getNested(value, *args[1:])


### CLASSES (O enunciado explicitamente limita a existência de ficheiros ".py"
#   a um máximo de 2. Desta forma, incluímos as classes necessárias ao funcionamento
#   do programa no ficheiro pgrepwc e no ficheiro hpgrepwc separadamente para que estes
#   possam funcionar indepentendemente um do outro).

class Load:
    """
    Alberga dados sobre carga referente a um processo.
    """
    def __init__(self, file, offset, bytesToHandle):
        self._file = file
        self._offset = offset
        self._bytesToHandle = bytesToHandle
        self._end = offset + bytesToHandle - 1

    def getFile(self):
        """
        Obtém o ficheiro onde vai correr a pesquisa.
        """
        return self._file

    def getOffset(self):
        """
        Obtém a posição inicial onde vai começar a ser corrida a pesquisa.
        """
        return self._offset
    
    def getBytesToHandle(self):
        """
        Obtém o número de bytes a pesquisar.
        """
        return self._bytesToHandle

    def getEnd(self):
        """
        Obtém a posição de fim da execução.
        """
        return self._end

class Match:
    """
    Alberga dados sobre uma linha que contenha ocorrências de uma palavra.
    """
    def __init__(self, file, lineNumber, lineContent, amount):
        self._lineNumber = lineNumber
        self._lineContent = lineContent
        self._file = file
        self._amount = amount

    def getLineNumber(self):
        """
        Obtém o número da linha onde a(s) ocorrência(s) foi/foram encontrada(s).
        """
        return self._lineNumber

    def getLineContent(self):
        """
        Obtém o conteúdo correspondente à linha onde a(s) ocorrência(s) foi/foram encontrada(s).
        """
        return self._lineContent
    
    def getFile(self):
        """
        Obtém o ficheiro onde a(s) ocorrência(s) foi/foram encontrada(s).
        """
        return self._file

    def getAmount(self):
        """
        Obtém o número de ocorrência(s) que se repete(m) ao longo da linha.
        """
        return self._amount

# Invocação de main
if __name__ == "__main__":
    main(sys.argv[1:])