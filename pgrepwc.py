import sys, getopt






def main(argv):

    wc = 0

    for fileIndex in argv[1:]:

        # se -p omitido ou 0
        with open(fileIndex, "r") as f:

            lines = f.readlines()


            for lineIndex in range(len(lines)):
                if argv[0] in lines[lineIndex].split(): #para que não apareçam palavras pegadas a outras
                    wc += 1
                    print(lineIndex+1, lines[lineIndex])

    print(f"Total de ocorrências: {wc}")

if __name__ == "__main__":
   main(sys.argv[1:])

