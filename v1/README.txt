Grupo 22 - Novembro/2020

55373 - José Almeida
55371 - Augusto Gouveia
54975 - Miguel Lages

Funcionalidades:

• Suporta duas versões de paralelismo: multiprocessing (pgrepwc.py) e multithreading (pgrepwc_threads.py).

		- O uso do pacote multiprocessing neste projeto permite-nos certificar que este funciona de maneira igualmente eficiente em Linux e Windows (algo impossibilitado pelo uso de os.fork(), visto que este não funciona em Windows).

• Realçamento dos números das linhas a verde e das correspondências a vermelho, em ambas versões do programa (disponível em ambos Linux e Windows).

• Uso de mecanismos de exclusão mútua (mutex lock) para assegurar que não se dão problemas de sincronização (e.g. escrita simultânea na mesma variável por parte de processos/threads diferentes) e que a exposição dos resultados por parte dos processos/threads se dá de maneira intercalada.

• Uso de expressões regulares para encontrar correspondências exatas da palavra especi-
ficada em situações que esta esteja isolada.

• Estrutura robusta que permite aceder aos ficheiros-alvo sem ter que os carregar diretamente para a memória (especialmente útil para ficheiros de maiores dimensões).

• Programação defensiva que permite que o programa não falhe quando um dos ficheiros referidos não é encontrado. Inclui também prevenção de repetição de procura em ficheiros, descartando ficheiros repetidos que possam ter sido introduzidos pelo utilizador.

• [pgrepwc.py] -> Uso de mecanismos de memória partilhada para comunicar resultados de pesquisas/contagens ao processo pai por parte dos processos-filho.

• Leitura de nomes dos ficheiros-alvo através de stdin ou como argumento.

• Código detalhadamente documentado.