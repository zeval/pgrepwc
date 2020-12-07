import sys
import getopt
import os
import re
import platform
import pickle
from math import ceil
from multiprocessing import Value, Process, Lock, Manager
import datetime
import signal
import time

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
if platform.system() == "Windows":
    os.system('color')

# Definição de variáveis globais

processTable = None
totalWC = None
totalLC = None
totalFilesProcessed = None
timeCounter = 0
statusReportInterval = None
startTimeStamp = None
manager = None
outputList = None
args = None
opts = None
halt = None
processedOutputList = None
allFiles = None
writeMutex = Lock()


def main(argv):
    global totalWC
    global totalLC
    global totalFilesProcessed
    global outputList
    global statusReportInterval
    global processTable
    global startTimeStamp
    global args
    global halt
    global processedOutputList
    global opts
    global allFiles

    processStats = None

    # Definição do tempo de início e datetime de início
    startTimeStamp = time.time()
    startDateStamp = datetime.datetime.now()


    try:
        # Obter argumentos, opções
        opts, args = getopt.getopt(argv, "clp:a:f:h")

    except getopt.GetoptError:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: pgrepwc [-c|-l] [-p n] [-a s] [-f file] [-h] palavra <ficheiros>")
        sys.exit(2)

    # Por omissão, todas as pesquisas/contagens são feitas no processo pai, pelo que não se dá paralelismo
    numberOfProcesses = 1
    parallelization = False

    if len(args) == 1:  # Caso apenas seja dada a palavra, e não os nomes dos ficheiros
        print("Introduza os nomes dos ficheiros a pesquisar, numa linha, separados por espaços:")
        allFiles = removeDuplicates(input().split())  # Evitar pesquisar nos mesmos ficheiros várias vezes
        print()  # Razões Estéticas
    else:
        allFiles = removeDuplicates(args[1:])  # Evitar pesquisar nos mesmos ficheiros várias vezes

    try:
        for opt in opts:
            if opt[0] == "-p":
                numberOfProcesses = int(opt[1])
                parallelization = True  # Ativar paralelismo caso a opção "-p n" seja utilizada
                if numberOfProcesses == 0:  # Evitar erros se for pedido "-p 0", desligando o paralelismo
                    parallelization = False
            if opt[0] == "-a":
                statusReportInterval = int(opt[1])
    except:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: pgrepwc [-c|-l] [-p n] [-a s] [-f file] [-h] palavra <ficheiros>")
        sys.exit(2)


    # Definição das variáveis de contagem em memória partilhada
    totalWC = Value("i", 0)
    totalLC = Value("i", 0)
    totalFilesProcessed = Value("i", 0)
    halt = Value("i", 0)


    # Caso o paralelismo esteja ativado:
    if parallelization:

        # Uso de multiprocessing.Manager para criação de estruturas de memória partilhada onde
        # os processos colocarão os seus dados.
        manager = Manager()
        outputList = manager.list()
        processStats = manager.dict()
        
        # Estrutura que irá conter a atribuição de carga a cada processo
        processTable = dict()

        # Cálculo do tamanho agregado de todos os ficheiros
        allFilesSize = 0
        for file in allFiles:
            allFilesSize += os.path.getsize(file)

        # Cálculo da quantidade média de bytes por processo
        bytesPerProcess = ceil(allFilesSize/numberOfProcesses)

        # Definição de uma mutual exclusion lock para evitar problemas de sincronização
        mutex = Lock()


        # Divisão do trabalho pelos vários processos:
        fileIndex = 0
        previousProcess = None
        nextProcess = False

        
        for process in range(numberOfProcesses):
            nextProcess = False
            while not nextProcess and fileIndex < len(allFiles):


                # Redefine-se o valor de nextProcess para False, pois só se deve avançar para a atribuição de carga ao próximo processo
                # quando a capacidade de carga total do processo atual tiver sido atingida.
                nextProcess = False

                # Caso este processo não seja o primeiro a correr, utilizar previousProcess para referenciar o processo anterior.
                if process > 0:
                    previousProcess = processTable[process - 1]

                # Caso este processo ainda não esteja registado na tabela de processos:
                # • Adiciona-se uma entrada cuja chave é o número do processo;
                # • bytesToHandle é a média de bytesPerProcess pois este processo ainda não tem carga atribuida.
                if process not in processTable:
                    processTable[process] = []
                    bytesToHandle = bytesPerProcess


                # Obter tamanho do ficheiro com que se está a lidar
                fileSize = os.path.getsize(allFiles[fileIndex])
                
                # Caso este seja o primeiro processo (ou seja: previousProcess == None):
                if not previousProcess:
                    
                    # Caso o tamanho do ficheiro seja menor ou igual à média de bytesPerProcess, atribui-se
                    # ao processo a carga de bytes fileSize, sendo o ficheiro tratado interiamente por um processo,
                    # e dá-se a instrução de que passamos a lidar com o próximo ficheiro (fileIndex += 1).
                    if fileSize <= bytesPerProcess:
                        processTable[process].append(Load(allFiles[fileIndex], 0, fileSize))
                        fileIndex += 1
                    
                    # Caso contrário (o tamanho do ficheiro é maior que a média bytesPerProcess), diz-se apenas que
                    # este processo terá que lidar com bytesToHandle bytes deste ficheiro (que neste caso será o valor
                    # inicial de bytesToHandle: a média bytesPerProcess.
                    else:
                        processTable[process].append(Load(allFiles[fileIndex], 0, bytesToHandle))
                    
                # Caso contrário (se este não for o primeiro processo):
                else:
                    
                    # Referencia-se a carga mais recente do último processo (o último objeto Load do processo anterior)
                    previousProcessLoad = previousProcess[-1]

                    # Caso a última carga do processo anterior tiver a ver com o ficheiro com que se lida atualmente, iremos
                    # então tratar apenas dos bytes após o byte em que o processo anterior terminou (previousProcessLoad.getEnd() + 1).
                    if previousProcessLoad.getFile() == allFiles[fileIndex]:
                        
                        # Caso os bytes que o processo anterior está encarregue + bytesToHandle for maior que fileSize,
                        # este processo lidará então com os bytes que faltarem do ficheiro atual, representados por:
                        # (fileSize - previousProcessLoad.getEnd() - 1). Dá-se a seguir a instrução de que passamos a lidar
                        # com o próximo ficheiro (fileIndex += 1).
                        if (previousProcessLoad.getEnd() + bytesToHandle) + 1 > fileSize:
                            processTable[process].append(Load(allFiles[fileIndex], previousProcessLoad.getEnd() + 1, fileSize - previousProcessLoad.getEnd() - 1))
                            fileIndex += 1
                        
                        # Caso contrário (se os bytes que o processo anterior está encarregue + bytesToHandle for menor que fileSize),
                        # o processo atual irá lidar com mais bytesToHandle bytes do ficheiro atual.
                        else:
                            processTable[process].append(Load(allFiles[fileIndex], previousProcessLoad.getEnd() + 1, bytesToHandle))

                    # Caso contrário (se a última carga do processo anterior não tiver a ver com o ficheiro atual, ou seja, se estivermos
                    # a tratar de um ficheiro novo), este processo ficará encarregue de lidar com mais fileSize bytes do ficheiro atual
                    # ou bytesToHandle bytes do ficheiro atual, dependendo se o tamanho do ficheiro é maior que a capacidade de carga
                    # que falta ao processo ou não.

                    else: 

                        if fileSize <= bytesToHandle:
                            processTable[process].append(Load(allFiles[fileIndex], 0, fileSize))
                            fileIndex += 1
                        else:
                            processTable[process].append(Load(allFiles[fileIndex], 0, bytesToHandle))

                # Cálculo da carga total atual do processo. Este passo cálcula bytesToHandle (ou seja, cálcula quantos bytes o processo 
                # ainda poderá tratar conforme a média de bytesPerProcess). Este passo assegura que qualquer processo n em 0 <= n < numberOfProcesses
                # irá apenas lidar com (no máximo) bytesPerProcess bytes, e nunca mais que isso, certificando-se assim da equitatividade na distribuição
                # de carga pelos vários processos.
                # ATENÇÃO: É importante reconhecer que a média bytesPerProcess é cálculada com base no tamanho total do agregado de ficheiros.

                processLoad = 0
                for loadUnit in processTable[process]:
                    processLoad += loadUnit.getBytesToHandle()

                # Caso a carga total do processo já seja igual ou maior que a média bytesPerProcess, passa-se então a atribuir carga ao próximo processo,
                # inibindo o ciclo while de correr com a instrução "nextProcess = True", causando uma próxima iteração do ciclo for que itera sobre o índice
                # de processos. Dá-se também a instrução "bytesToHandle = bytesPerProcess", reiniciando o valor de bytesToHandle para que o próximo processo
                # possa lidar com o valor correto de bytes por cada processo.
                if processLoad >= bytesPerProcess:
                    nextProcess = True
                    bytesToHandle = bytesPerProcess
                
                # Caso contrário (se o processo ainda não tiver atingido a sua capacidade de carga total), bytesToHandle, na próxima iteração, será o quanto
                # falta para a capacidade de carga do processo chegar ao seu total (valor cálculado pela instrução "bytesPerProcess - processLoad")
                else:
                    bytesToHandle = bytesPerProcess - processLoad




        ### Extra: descomentar esta secção e prestar atenção à variável processLoads para perceber a quantidade de bytes  #
        ###        atribuída a cada processo. Recomenda-se a colocação de um breakpoint no final da secção comentada em   #
        ###        caso de teste.                                                                                         #
        #                                                                                                                 #
        #     processLoads = []                                                                                           #
        #     for process in processTable.values():                                                                       #
        #         processLoad = 0                                                                                         #
        #         for loadUnit in process:                                                                                #
        #             processLoad += loadUnit.getBytesToHandle()                                                          #
        #         processLoads.append(processLoad)                                                                        #
        #                                                                                                                 #
        #     print(processLoads)                                                                                         #
        #                                                                                                                 #
        ###################################################################################################################


        # Criação de objetos Process e dada a carga atribuída
        processList = list()

        for process in processTable:
            processList.append(Process(target=matchFinder, args=(processTable[process], outputList, processStats, mutex)))

        # Caso o utilizador tenha incluido a opção "-a", atribuir função realtimeFeedback ao sinal SIGALRM
        # e iniciar um temporizador que itera a cada segundo
        if statusReportInterval:
            
            signal.signal(signal.SIGALRM, realtimeFeedback)
            signal.setitimer(signal.ITIMER_REAL, 1, 1)

        # Atribuição da função haltHandler ao sinal SIGINT
        signal.signal(signal.SIGINT, haltHandler)

        # Execução e espera pela conclusão dos processos filhos e início da medição do tempo de processamento
        before = time.time()

        for process in processList:
            process.start()

        # Uso de sleep() para “obrigar” o CPU a passar a execução para os filhos.

        time.sleep(1)

        for process in processList:
            process.join()

        after = time.time()

        
    # Caso o paralelismo esteja desligado, todo o trabalho é feito pelo processo pai
    else: 

        # Redefinição de estruturas necessários ao funcionamento do processo:
        # • fullLoad: lista que incluirá os objetos Load referentes à carga (1 por ficheiro, neste caso)
        # • Outros: estruturas onde o processo guardará os seus resultados
        fullLoad = list()
        outputList = list()
        processStats = dict()


        # Colocação dos objetos Load referentes aos ficheiros a analisar. 1 objeto Load por ficheiro,
        # na sua integridade, pois apenas haverá um processo a lidar com todos os ficheiros.
        for file in allFiles:
            fileSize = os.path.getsize(file)
            fullLoad.append(Load(file, 0, fileSize))

        # Caso o utilizador tenha incluido a opção "-a", atribuir função realtimeFeedback ao sinal SIGALRM
        # e iniciar um temporizador que itera a cada segundo
        if statusReportInterval:
            
            signal.signal(signal.SIGALRM, realtimeFeedback)
            signal.setitimer(signal.ITIMER_REAL, 1, 1)
        
        # Atribuição da função haltHandler ao sinal SIGINT
        signal.signal(signal.SIGINT, haltHandler)

        # Execução e espera pela conclusão da função matchFinder e início da medição do tempo de processamento
        before = time.time()
        
        matchFinder(fullLoad, outputList = outputList, processStats = processStats)

        after = time.time()


    # Organização de output: passagem e um dicionário partilhado de estrutura
    # orientada a processos, para um dicionário local de estrutura orientada
    # a ficheiros.
    processedOutputList = dict()

    for match in outputList:
        if match.getFile() not in processedOutputList:
            processedOutputList[match.getFile()] = []
        processedOutputList[match.getFile()].append(match)

    # Ordenação ascendente dos objetos Match por número de linha, para que o output
    # seja imprimido de forma ordenada  
    for file in processedOutputList:
        processedOutputList[file].sort(key=lambda match: (match.getLineNumber()))


    # Guardar ficheiro de histórico
    for opt in opts:
        if opt[0] == "-f":
            file = opt[1].strip()
            with open(file, "wb") as f:
                pickle.dump((dict(processStats), after - before, startDateStamp, opts, args[0], int(halt.value)), f)


    
    # Esconder output se -h for incluido nas opções
    os.system("clear")
    if not any("-h" in opt for opt in opts):
        for file in processedOutputList:
            for match in processedOutputList[file]:
                print(match.getLineContent())
            
            
    # Desativa o feedback em tempo real
    signal.alarm(0)


    print() # Razões estéticas


    # Imprimir output consoante a presença de opções nos argumentos do utilizador:
    # • Caso o paralelismo esteja ativado: imprimir PID do processo pai;
    # • Caso a opção "-c" esteja incluida, imprimir o total de ocorrências;
    # • Caso a opção "-l" esteja incluida, imprimir o total de linhas com ocorrências. 
    if parallelization:
        print(f"PID Pai: {colorWrite(os.getpid(), 'green')}")

    if any("-c" in opt for opt in opts):
        print(f"Total de ocorrências: {colorWrite(totalWC.value, 'green')}")

    if any("-l" in opt for opt in opts):
        print(f"Total de linhas: {colorWrite(totalLC.value, 'green')}")


    # Cálculo do tempo total passado desde o início do processamento.
    timeTaken = round((after - before) * 1000000) 

    print("Tempo total:", colorWrite(timeTaken, 'green'), "microsegundos")
        
    # Imprimir a flag "[PARAGEM FORÇADA]" caso o utilizador tenha forçado a paragem via sinal SIGINT.
    if halt.value == 2:
        print(colorWrite("[PARAGEM FORÇADA]", "red"))
    




def matchFinder(loadList, outputList, processStats, mutex=None):
    """
    Função responsável por encontrar as palavras idênticas à especificada pelo utilizador
    Requires: loadList != None, outputList != None, processStats != None

    """

    global halt 
    global totalWC
    global totalLC
    global totalFilesProcessed
    global processTable
    global args

    word = args[0]

    if mutex:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    # Expressão regular responsável por identificar instâncias da palavra isolada
    regex = fr"\b{word}\b"

    processInfo = []

    for load in loadList:

        if halt.value == 2:
            break

        loadMatches = []

        beforeLoad = time.time()

        file = load.getFile()
        offset = load.getOffset()
        loadSize = load.getBytesToHandle()
        end = load.getEnd()
        pid = os.getpid()
        fileSize = os.path.getsize(file)
        
        firstLine = lineCounter(file, offset)

        try:
            with open(file, "rb") as f: #encoding="ISO-8859-1"
                lineNumber = firstLine
                f.seek(offset)

                line = str(f.readline(), "utf-8")
                
                output = []

                while line and f.tell() <= load.getEnd():

                    matches = re.findall(regex, line)

                    if matches:

                        # Uso do método re.sub() para substituir todas as instâncias da palavra isolada
                        # por instâncias da mesma em versão colorida
                        processedLine = re.sub(regex, colorWrite(word, "red"), line)
                        output.append(Match(file, lineNumber, f"{colorWrite(lineNumber, 'green')}: {processedLine}", len(matches)))

                        if mutex:
                            mutex.acquire()
                            totalWC.value += len(matches)
                            totalLC.value += 1
                            mutex.release()
                        else:
                            totalWC.value += len(matches)
                            totalLC.value += 1

                    line = str(f.readline(), "utf-8")
                    lineNumber += 1


                if fileSize == load.getEnd():
                    if mutex:
                        mutex.acquire()
                        totalFilesProcessed.value += 1
                        mutex.release()
                    else:
                        totalFilesProcessed.value += 1

                for match in output:
                    outputList.append(match)
                    loadMatches.append(match)
            
  
        except FileNotFoundError:
            print(f"Ficheiro '{file}' não encontrado. Verifique o seu input.")

        except UnicodeDecodeError as e:
            print(e, f"\nFicheiro '{file}' contém caracteres ilegíveis.")

        afterLoad = time.time()

        processInfo.append((load, fileSize, afterLoad-beforeLoad, loadMatches))


    processStats[os.getpid()] = processInfo



def removeDuplicates(inputList):
    """
    Função responsável por retirar elementos duplicados de uma lista.
    Requires: inputList diferente de None.
    Ensures: uma lista semelhante a inputList, sem elementos duplicados.
    """
    return list(dict.fromkeys(inputList))

def lineCounter(file, pos):
    """
    TODO: Comentar
    """
    # Abrindo o ficheiro como binário é várias vezes mais rápido e eficiente
    # do que abrir como ficheiro de texto.
    with open(file, "rb+") as f:
        count = 0
        line = f.readline()
        
        while line:
            a = f.tell()
            count += 1
            if f.tell()>pos:
                return count
            line = f.readline()

def realtimeFeedback(sig, NULL):
    """
    Função responsável por apresentar o estado do programa.
    TODO: Comentar
    """
    global manager
    global totalLC
    global totalWC
    global totalFilesProcessed
    global timeCounter
    global statusReportInterval
    global startTimeStamp
    global halt
    global args
    global opts
    global allFiles
    global writeMutex

    timeCounter += 1

    output = ""


    if timeCounter % statusReportInterval == 0 and halt.value == 0:
        currentTime = round((time.time() - startTimeStamp) * 1000000)


        output += (f"Passaram {colorWrite(currentTime, 'green')} microsegundos")

        if any("-l" in opt for opt in opts):
            output += (f"\nEncontradas instâncias de '{colorWrite(args[0], 'red')}' em {colorWrite(totalLC.value, 'green')} linhas")

        elif any("-c" in opt for opt in opts):
            output += (f"\nEncontradas {colorWrite(totalWC.value, 'green')} instâncias de '{colorWrite(args[0], 'red')}'")
            
        fileProgress = colorWrite(str(totalFilesProcessed.value) + "/" + str(len(allFiles)), 'green')

        output += (f"\n{fileProgress} ficheiros foram completamente processados")
        output += ("")

        os.system("clear")
        writeMutex.acquire()
        print(output)
        writeMutex.release()

        
def haltHandler(sig,NULL):
    """
    Função responsável por lidar com a interrupção do programa.
    """
    global halt
    global args
    global writeMutex

    word = args[0]

    if halt.value == 0:
        halt.value = 1
        os.system("clear")
        ctrlC = colorWrite("CTRL+C", 'red')
        writeMutex.acquire()
        answer = input(f"Carregou em {ctrlC} se parar agora poderão haver instâncias de '{colorWrite(word, 'red')}' não encontradas, deseja mesmo sair? ({colorWrite('Y', 'green')}/{colorWrite('N', 'red')})\n")
        writeMutex.release()

        if answer.lower() == "y":
            print("A terminar em segurança...")
            halt.value = 2
        else:
            halt.value = 0


def colorWrite(text, color):
    if color == "green":
        return GREEN_START + str(text) + COLOR_END
    
    if color == "red":
        return RED_START + str(text) + COLOR_END


### CLASSES (O enunciado explicitamente limita a existência de ficheiros ".py"
#   a um máximo de 2. Desta forma, incluímos as classes necessárias ao funcionamento
#   do programa no ficheiro pgrepwc e no ficheiro hpgrepwc separadamente para que estes
#   possam funcionar indepentendemente um do outro.)

class Load:
    """
    A classe Load TODO
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
    A classe Match TODO
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