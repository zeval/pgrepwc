import sys
import getopt
import os
import re
import platform

import pickle
from math import ceil
from multiprocessing import Value, Process, Lock, Manager
import datetime
from Load import Load
from Match import Match
import signal
import asyncio
import time

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
if platform.system() == "Windows":
    os.system('color')


processTable = None
totalWC = None
totalLC = None
totalFilesProcessed = None
timeCounter = 0
statusReportInterval = None
startTimeStamp = None
manager = None
outputTable = None
args = None




def main(argv):
    global totalWC
    global totalLC
    global totalFilesProcessed
    global outputTable
    global statusReportInterval
    global processTable
    global startTimeStamp
    global args

    startTimeStamp = time.time()
    startDateStamp = datetime.datetime.now()
    processStats = None

    try:
        # Obter argumentos, opções
        opts, args = getopt.getopt(argv, "clp:a:f:")

    except getopt.GetoptError:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: pgrepwc [-c|-l] [-p n] [-a s] [-f file] palavra <ficheiros>")
        sys.exit(2)

    # Por omissão, todas as pesquisas/contagens são feitas no processo pai, pelo que não se dá paralelização
    numberOfProcesses = 1
    parallelization = False

    if len(args) == 1:  # Caso apenas seja dada a palavra, e não os nomes dos ficheiros
        print("Introduza os nomes dos ficheiros a pesquisar, numa linha, separados por espaços:")
        allFiles = removeDuplicates(input().split())  # Evitar pesquisar nos mesmos ficheiros várias vezes
        print()  # Razões Estéticas
    else:
        allFiles = removeDuplicates(args[1:])  # Evitar pesquisar nos mesmos ficheiros várias vezes

    for opt in opts:
        if opt[0] == "-p":
            numberOfProcesses = int(opt[1])
            parallelization = True  # Ativar paralelização caso a opção "-p n" seja utilizada
            if numberOfProcesses == 0:  # Evitar erros se for pedido "-p 0", desligando a paralelização
                parallelization = False
        if opt[0] == "-a":
            statusReportInterval = int(opt[1])

    # Definição das variáveis de contagem em memória partilhada
    totalWC = Value("i", 0)
    totalLC = Value("i", 0)
    totalFilesProcessed = Value("i", 0)

    if parallelization:

        manager = Manager()
        outputTable = manager.list()
        processTable = dict()
        processStats = manager.dict()
        

        # # Definição do número estimado de ficheiros a lidar por cada processo
        # numberOfFilesPerProcess = ceil(len(allFiles) / numberOfProcesses)

        #####

        allFilesSize = 0
        for file in allFiles:
            allFilesSize += os.path.getsize(file)
        #####

        bytesPerProcess = ceil(allFilesSize/numberOfProcesses)

        # Definição de um mutex para evitar problemas de sincronização / outputs intercalados
        mutex = Lock()

        # TODO:fix comment -> Definição de uma Queue onde os processos-filho irão submeter os seus resultados


        # Divisão do trabalho pelos vários processos

        fileIndex = 0
        previousProcess = None
        nextProcess = False

        
        ## Weird bug when using 1 big file, 1 medium file, 2 small files for 2 processes... seems fixable, maybe it's working properly idk too sleepy :////
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



        assert 1==1



    # Tip: variable watch processLoads

    #     processLoads = []
    #     for process in processTable.values():
    #         processLoad = 0
    #         for loadUnit in process:
    #             processLoad += loadUnit.getBytesToHandle()
    #         processLoads.append(processLoad)

    #     print(processLoads)

    #     assert 1==1 # Optimal place for breakpoint :)


    # #######


        processList = list()

        for process in processTable:
            processList.append(Process(target=matchFinder, args=(processTable[process], opts, args[0], totalWC, totalLC, totalFilesProcessed, mutex, outputTable, processStats)))


        if statusReportInterval:
            
            signal.signal(signal.SIGALRM, realtimeFeedback)
            signal.setitimer(signal.ITIMER_REAL, 1, 1)

        # Execução e espera pela conclusão dos processos filhos 

        before = time.time()

        for process in processList:
            process.start()

        time.sleep(1)

        for process in processList:
            process.join()

        after = time.time()


        assert 1==1
        

    else:  # Caso a paralelização esteja desligada, todo o trabalho é feito pelo processo pai



        fullLoad = list()
        outputTable = list()
        processStats = dict()


        for file in allFiles:
            fileSize = os.path.getsize(file)
            fullLoad.append(Load(file, 0, fileSize))


        if statusReportInterval:
            
            signal.signal(signal.SIGALRM, realtimeFeedback)
            signal.setitimer(signal.ITIMER_REAL, 1, 1)


        

        before = time.time()
        matchFinder(fullLoad, opts, args[0], totalWC, totalLC, totalFilesProcessed, outputTable = outputTable, processStats = processStats)

        after = time.time()

    

    # MOSTRAR OUTPUT

    
    processedOutputTable = dict()

    # Organização de output: passagem e um dicionário partilhado de estrutura
    # orientada a processos, para um dicionário local de estrutura orientada
    # a ficheiros.

    for match in outputTable:
        if match.getFile() not in processedOutputTable:
            processedOutputTable[match.getFile()] = []
        processedOutputTable[match.getFile()].append(match)

    for file in processedOutputTable:
        processedOutputTable[file].sort(key=lambda match: (match.getLineNumber()))

    # Guardar ficheiro de histórico

    for opt in opts:
        if opt[0] == "-f":
            file = opt[1]
            with open(file, "wb") as f:
                pickle.dump((processStats, after - before, startDateStamp), f)

    
    # Uncomment to show output
    # for file in processedOutputTable:
    #     for match in processedOutputTable[file]:
    #         print(match.getLineContent())
            
    # print("processing time:", after1 - before1)
    
    

    
    # Desativa o feedback em tempo real
    signal.alarm(0)

    print() # Razões estéticas

    if parallelization:
        print(f"PID PAI: {colorWrite(os.getpid(), 'green')}")

    if any("-c" in opt for opt in opts):
        print(f"Total de ocorrências: {colorWrite(totalWC.value, 'green')}")

    if any("-l" in opt for opt in opts):
        print(f"Total de linhas: {colorWrite(totalLC.value, 'green')}")
    
    print("Tempo total:", colorWrite(round(after - before), 'green'), "segundos")



def matchFinder(loadList, args, word, totalWC, totalLC, totalFilesProcessed, mutex=None, outputTable=None, processStats=None):
    # Expressão regular responsável por identificar instâncias da palavra isolada
    regex = fr"\b{word}\b"
    before = time.time()
    processInfo = []

    for load in loadList:

        loadMatches = []

        beforeLoad = time.time()

        file = load.getFile()
        offset = load.getOffset()
        loadSize = load.getBytesToHandle()
        end = load.getEnd()
        wc = 0
        lc = 0
        pid = os.getpid()
        fileSize = os.path.getsize(file)


        # if file not in outputTable:
        #     outputTable[file] = []
        
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

                        # output += f"{GREEN_START}{lineNumber}{COLOR_END}: {processedLine}"

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

                # if mutex:
                #     mutex.acquire()
                #     outputTable[pid] = output
                #     mutex.release()
                # else:
                #     outputTable[pid] = output

                for match in output:
                    outputTable.append(match)
                    loadMatches.append(match)
            
  
        except FileNotFoundError:
            print(f"Ficheiro '{file}' não encontrado. Verifique o seu input.")

        except UnicodeDecodeError as e:
            print(e, f"\nFicheiro '{file}' contém caracteres ilegíveis.")

        afterLoad = time.time()

        processInfo.append((load, fileSize, afterLoad-beforeLoad, loadMatches))


    after = time.time()
    # print("HERE: ", after-before)
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

    global manager
    global totalLC
    global totalWC
    global totalFilesProcessed
    global timeCounter
    global statusReportInterval
    global startTimeStamp
    global args

    timeCounter += 1



    if timeCounter % statusReportInterval == 0:
        currentTime = round((time.time() - startTimeStamp) * 1000000)
        os.system("clear")
        print(f"Passaram {colorWrite(currentTime, 'green')} microsegundos")
        print(f"Encontradas {colorWrite(totalWC.value, 'green')} instâncias de '{colorWrite(args[0], 'red')}' em {colorWrite(totalLC.value, 'green')} linhas.")
        print(f"{colorWrite(totalFilesProcessed.value, 'green')} ficheiros foram completamente processados.")
        print()

# async def realtimeFeedbackAlt():
#     """
#     A versão da package "signal" para Windows não suporta signal.SIGALRM.
#     Esta é uma alternativa utilizando a package "asyncio"
#     """

#     global manager
#     global totalLC
#     global totalWC
#     global statusReportInterval

#     timeCounter = 5

#     while True:
#         asyncio.sleep(5)
#         print(f"Passaram {timeCounter} segundos")
#         timeCounter += 5

    
#     return

def colorWrite(text, color):
    if color == "green":
        return GREEN_START + str(text) + COLOR_END
    
    if color == "red":
        return RED_START + str(text) + COLOR_END

if __name__ == "__main__":
    main(sys.argv[1:])

