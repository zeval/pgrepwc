Grupo 22 - Dezembro/2020

55373 - José Almeida
55371 - Augusto Gouveia
54975 - Miguel Lages

Funcionalidades:

[pgrepwc.py]: 

• Utilização: pgrepwc [-c|-l] [-p n] [-a s] [-f file] [-h] palavra <ficheiros>

• Opção "-h" que permite esconder o output.

• Uso de mecanismos de memória partilhada para comunicar resultados de pesquisas/contagens ao
processo pai por parte dos processos-filho.

• Suporta paralelismo: multiprocessing.

• Realçamento dos números das linhas a verde e das correspondências a vermelho.

• Uso de mecanismos de exclusão mútua (mutex lock) para assegurar que não se dão problemas de
sincronização (ex. escrita simultânea na mesma variável por parte de processos/threads diferentes)
e que a exposição dos resultados por parte dos processos/threads se dá de maneira intercalada.

• Uso de expressões regulares para encontrar correspondências exatas da palavra especificada em
situações que esta se encontre isolada.

• Estrutura robusta que permite aceder aos ficheiros-alvo sem ter que os carregar diretamente para
a memória (especialmente útil para ficheiros de maiores dimensões).

• Programação defensiva que permite que o programa não falhe quando um dos ficheiros referidos não
é encontrado. Inclui também prevenção de repetição de procura em ficheiros, descartando ficheiros
repetidos que possam ter sido introduzidos pelo utilizador.

• Leitura de nomes dos ficheiros-alvo através de stdin ou como argumento.

• Processamento seguro do sinal SIGINT: ao ser recebido o sinal SIGINT, é necessária confirmação
para que o programa termine o processamento, de modo a evitar acidentes. Ao ser recebida
confirmação, a paragem de processamento é efectuada de maneira segura e não abrupta, assegurando-se
que todos os dados recolhidos até ao momento são corretamente apresentados e possivelmente
guardados (opção "-f").

• Código detalhadamente documentado.

[hpgrepwc.py]: 

• Utilização: hpgrepwc <ficheiro>

• Realçamento de dados considerados mais importantes a verde, há excepção de quando o total de
bytes processado não corresponde a 100% (neste caso a percentagem do total de bytes processado
apresenta-se realçada a vermelho).

• Código detalhadamente documentado.