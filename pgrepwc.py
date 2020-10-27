import sys, getopt, os


# Cor
CRED = '\033[91m'
CEND = '\033[0m'
os.system('color')


def main(argv):

    try:
        opts, args = getopt.getopt(argv,"clp:")

        # print(opts)

        # print(args)

    except getopt.GetoptError:
        print("Utilização: pgrepwc [-c|-l] [-p n] palavra {ficheiros}")
        sys.exit(2)

    wc, lc = matchFinder(args, args[0])

    if any("-c" in opt for opt in opts):
        print(f"Total de ocorrências: {wc}")

    if any("-l" in opt for opt in opts):
        print(f"Total de linhas: {lc}")

    


def matchFinder(args, word):

    wc = 0
    lc = 0

    for file in args[1:]:
        # se -p omitido ou 0
        with open(file, "r") as f:

            lines = f.readlines()

            for lineIndex in range(len(lines)):
                splitLine = lines[lineIndex].strip("\n").split()
                if word in splitLine: #para que não apareçam palavras pegadas a outras
                    lc += 1
                    wc += splitLine.count(word)
                    print(lineIndex+1, lines[lineIndex].replace(word, f"{CRED}{word}{CEND}"))
    
    return wc, lc

                    

if __name__ == "__main__":
   main(sys.argv[1:])