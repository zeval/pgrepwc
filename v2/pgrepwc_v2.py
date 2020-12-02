import sys
import getopt
import os
import re
import platform
from math import ceil
from multiprocessing import Value, Process, Lock
from Load import Load

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
if platform.system() == "Windows":
    os.system('color')


processTable = dict()


def main(argv):
    try:
        # Obter argumentos, opções
        opts, args = getopt.getopt(argv, "clp:a:")

    except getopt.GetoptError:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: pgrepwc [-c|-l] [-p n] [-a s] palavra <ficheiros>")
        sys.exit(2)

    # Por omissão, todas as pesquisas/contagens são feitas no processo pai, pelo que não se dá paralelização
    numberOfProcesses = 1
    parallelization = False

    statusReportInterval = None

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

    if parallelization:

        # # Definição do número estimado de ficheiros a lidar por cada processo
        # numberOfFilesPerProcess = ceil(len(allFiles) / numberOfProcesses)

        #####

        allFilesSize = 0
        for file in allFiles:
            allFilesSize += os.path.getsize(file)
        #####

        bytesPerProcess = ceil(allFilesSize/numberOfProcesses)

        # Definição de lista de processos a executar
        p = []

        # Definição de um mutex para evitar problemas de sincronização / outputs intercalados
        mutex = Lock()
        
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
                    if previousProcess[-1].getFile() == allFiles[fileIndex]:
                        
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
                



    ####### Estas linhas mostram a carga em cada processo :) Tip: variable watch processLoads

        processLoads = []
        for process in processTable.values():
            processLoad = 0
            for loadUnit in process:
                processLoad += loadUnit.getBytesToHandle()
            processLoads.append(processLoad)

        print(processLoads)

        assert 1==1 # Optimal place for breakpoint :)


    #######

    # Falta iterar sobre a processTable e dar as Loads aos respetivos processos

        # Execução e espera pela conclusão dos processos filhos 

        for fileProcesses in processTable.values():
            for processTuple in fileProcesses:
                processTuple[0].start()

        for fileProcesses in processTable.values():
            for processTuple in fileProcesses:
                processTuple[0].join()

    else:  # Caso a paralelização esteja desligada, todo o trabalho é feito pelo processo pai

        # TODO: Fix this (case same process handles all files)
        matchFinder(allFiles, opts, args[0], totalWC, totalLC)

    if parallelization:
        print(f"PID PAI: {os.getpid()}")

    if any("-c" in opt for opt in opts):
        print(f"Total de ocorrências: {totalWC.value}")

    if any("-l" in opt for opt in opts):
        print(f"Total de linhas: {totalLC.value}")


def matchFinder(files, args, word, totalWC, totalLC, mutex=None):

    # Expressão regular responsável por identificar instâncias da palavra isolada
    regex = fr"\b{word}\b"

    for file in files:

        output = []
        wc = 0
        lc = 0
        try:
            with open(file, "r", encoding="utf-8") as f:
                output.append("==================================================")
                output.append(f"PID: {os.getpid()}\nFicheiro: {file}\n")

                lineNumber = 0

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

                # Output do resultado de cada processo
                # O mutex ajuda a impedir outputs intercalados e que o acesso às variáveis globais seja mediado

                if mutex:
                    mutex.acquire()

                for line in output:
                    print(line)

                print()
                for opt in args:
                    if opt[0] == "-c":
                        print(f"Total de ocorrências da palavra: {wc}\n"
                              f"A enviar para o processo pai ({os.getppid()})...")
                    if opt[0] == "-l":
                        print(f"Total de linhas em que a palavra apareceu: {lc}\n"
                              f"A enviar para o processo pai ({os.getppid()})...")
                print(f"==================================================\n")

            # Incrementação nas variáveis de contagem em memória partilhada
            totalWC.value += wc
            totalLC.value += lc

            # Libertação do mutex para que os outros processos possam imprimir o seu resultado
            if mutex:
                mutex.release()

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