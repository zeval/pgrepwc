import sys, getopt






def main(argv):

    # se -p omitido ou 0
    with open(argv[1], "r") as f:

        lines = f.readlines()

        for lineIndex in range(len(lines)):
            if argv[0] in lines[lineIndex]:
                print(lineIndex+1, lines[lineIndex])


if __name__ == "__main__":
   main(sys.argv[1:])

