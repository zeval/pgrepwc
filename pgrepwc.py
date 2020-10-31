import sys, getopt, os, re
from math import ceil
from multiprocessing import Value, Process

# Constante/Definição de cor
RED_START = '\033[91m'
GREEN_START = '\033[92m'
COLOR_END = '\033[0m'
os.system('color')


#TODO: Encontrar maneira de dar uma mensagem mais bonita caso o ficheiro não seja encontrado em vez de simplesmente crashar
#TODO: Quando um ficheiro é pesquisado/contado, espera-se até que este processo termine para começar outro. Apesar das várias
#pesquisas se darem em vários processos, estas não acontecem ao mesmo tempo com um for. Será ainda paralelização?
#TODO: O que quererá dizer "apresentar resultados de forma não intercalada"?

def main(argv):

    try:
        # Obter argumentos, opções
        opts, args = getopt.getopt(argv,"clp:")

    except getopt.GetoptError:
        # Mensagem de ajuda caso o comando seja malformado
        print("Utilização: pgrepwc [-c|-l] [-p n] palavra {ficheiros}")
        sys.exit(2)

    # Por omissão, todas as pesquisas/contagens são feitas no processo pai, pelo que não se dá paralelização
    parallelization = False

    if len(args) == 1: # Caso apenas seja dada a palavra, e não os nomes dos ficheiros
        print("Introduza os nomes dos ficheiros a pesquisar, numa linha, separados por espaços:")
        allFiles = removeDuplicates(input().split()) # Evitar pesquisar nos mesmos ficheiros várias vezes
        print() # Razões Estéticas
    else:
        allFiles = removeDuplicates(args[1:]) # Evitar pesquisar nos mesmos ficheiros várias vezes


    for opt in opts:
        if opt[0] == "-p":
            numberOfProcesses = int(opt[1])
            parallelization = True # Ativar paralelização caso a opção "-p n" seja utilizada
            if numberOfProcesses == 0: # Evitar erros se for pedido "-p 0", desligado a paralelização
                parallelization = False


    if numberOfProcesses > len(allFiles): # Evitar ciclos do for desnecessários, utilizar no máximo tantos
        numberOfProcesses = len(allFiles) # processos como ficheiros referidos

    # Definição das variáveis de contagem em memória partilhada
    totalWC = Value("i", 0)
    totalLC = Value("i", 0)


    if parallelization:

        # Definição do número estimado de ficheiros a lidar por cada processo
        numberOfFilesPerProcess = ceil(len(allFiles)/numberOfProcesses)

        # Divisão do trabalho pelos vários processos
        for process in range(numberOfProcesses):
            while len(allFiles)>0:

                filesToHandle = []

                for i in range(numberOfFilesPerProcess):

                    if len(allFiles) >= 1:
                        filesToHandle.append(allFiles.pop(0))


                p = Process(target = matchFinder, args=(filesToHandle, args, args[0], totalWC, totalLC))

                p.start()
                p.join()
        
    else: # Caso a paralelização esteja desligada, todo o trabalho é feito pelo processo pai
        
        matchFinder(allFiles, args, args[0], totalWC, totalLC)



    print() #estético
    if parallelization:
        print(f"PID PAI: {os.getpid()}")

    if any("-c" in opt for opt in opts):
        print(f"Total de ocorrências: {totalWC.value}")

    if any("-l" in opt for opt in opts):
        print(f"Total de linhas: {totalLC.value}")


def matchFinder(files, args, word, totalWC, totalLC):
    
    wc = 0
    lc = 0

    # Expressão regular responsável por identificar instâncias da palavra isolada
    regex = fr"\b{word}\b"
    
    for file in files:
        
        with open(file, "r") as f:

            print(f"PID: {os.getpid()}\nFicheiro: {file}\n")

            lines = f.readlines()
            
            for lineIndex in range(len(lines)):
                line = lines[lineIndex]
                matches = re.findall(regex, line)
                if matches:
                    lc += 1
                    wc += len(matches)

                    # Uso do método re.sub() para substituir todas as instâncias da palavra isolada 
                    # por instâncias da mesma em versão colorida
                    processedLine = re.sub(regex, RED_START + word + COLOR_END, line)
                    print(f"{GREEN_START}{lineIndex+1}{COLOR_END}: {processedLine}")


    # Incrementação nas variáveis de contagem em memória partilhada
    totalWC.value += wc
    totalLC.value += lc

def removeDuplicates(inputList):
    """
    Função responsável por retirar elementos duplicados de uma lista.
    Requires: inputList diferente de None.
    Ensures: uma lista semelhante a inputList, sem elementos duplicados.
    """
    return list(dict.fromkeys(inputList))                

if __name__ == "__main__":
   main(sys.argv[1:])