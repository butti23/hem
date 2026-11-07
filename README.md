# GRASP para máximo subgrafo induzido k-colorível ponderado

O objetivo é maximizar a soma dos pesos dos vértices coloridos. A cor 0 representa descarte. A cor do vértice DIMACS de identificador 1 ocupa a primeira posição do vetor `colors`.

## Reproduzir no ambiente do projeto

Na máquina Intel de 2,50 GHz com 32 GB e Ubuntu 26.04, extraia o pacote e execute a partir da pasta deste arquivo:

```sh
bash run_ubuntu.sh
```

O script verifica a distribuição, registra CPU, memória, versão do compilador, comando e hashes. Compila com `g++ -std=c++20 -O0` e executa um único processo de busca por vez. São 480 execuções independentes: 6 grafos × 2 regimes × 10 sementes × 4 prazos. Os orçamentos somam duas horas, além do tempo de leitura, escrita e validação. O controlador requer Python 3 sem pacotes adicionais. O relatório de ambiente é gravado ao lado da pasta de resultados. Para repetir, informe um novo nome de pasta.

Para resolver apenas uma instância:

```sh
g++ -std=c++20 -O0 grasp.cpp -o grasp
./grasp instances/queen6_6.col - 6 1 5
./grasp instances/DSJC125.9.col instances/DSJC125.9.weights 4 1 30
```

Os argumentos após os pesos são número de cores, semente e prazo em segundos. A entrada `-` atribui peso unitário. A saída JSON inclui a coloração. Com vários prazos crescentes, o programa observa a mesma trajetória em cada prazo.

## Correspondência com os algoritmos 1 a 3

1. **Construção.** Cada par vértice–cor é um vértice do produto cartesiano. A implementação C++ mantém o grau residual de cada candidato e o decrementa após remover um vizinho ativo. A RCL usa o limiar máximo menos 0,2 vezes a amplitude das prioridades. O sorteio é uniforme, inclusive em caso de empate.
2. **Busca local.** A reinserção percorre os descartados por peso/(1 + grau original) decrescente e identificador crescente, usando a menor cor admissível. Cada teste remove um único vértice da solução corrente e tenta reinserir todos os descartados, inclusive o removido. Comparam-se todos os vizinhos alcançados antes do prazo. A primeira solução de maior peso prevalece em empate, e somente melhorias estritas são aceitas.
3. **Reinícios e prazo.** Cada reinício começa vazio. O incumbente monitora soluções viáveis durante a construção e a vizinhança, permitindo recuperar a melhor solução já disponível em uma interrupção. Isso não altera as escolhas do GRASP enquanto há tempo. O relógio monotônico começa antes da preparação da adjacência e da inicialização do gerador. No Ubuntu, o controlador externo mede do sinal de partida ao sinal de conclusão e rejeita excedentes. O trabalhador reserva até 25 ms do último prazo para devolver o controle. Leitura da instância, serialização da solução e validação externa ficam fora dessa janela.

## Instâncias e validação

`instances/manifest.json` traz origem, identificadores, dimensões, k, referência unitária e hashes SHA-256 dos arquivos de entrada. Os seis arquivos DIMACS já contêm os grafos completos. As arestas estão em ordem canônica, com identificadores começando em 1. No grafo das rainhas os registros simétricos foram fundidos. DSJC125.9 foi convertido de listas de vizinhos. Cada vértice conserva o identificador da fonte utilizada.

Os seis arquivos `.weights` guardam os inteiros de 1 a 100 por identificador. Para reproduzi-los, execute `python3 prepare.py`. A semente 42 é reiniciada para cada grafo. A construção usa sementes separadas de 1 a 10. C++ usa `std::mt19937` e a versão Python usa `random.Random`. As bibliotecas mapeiam os sorteios de maneiras distintas, portanto as trajetórias podem diferir.

`experiment.py` verifica os hashes antes da bateria. Após cada execução, verifica o número de cores, conflitos em todas as arestas, número de vértices e soma dos pesos mantidos. Em `runs.jsonl` ficam os vetores de cores e as métricas individuais. Em `summary.csv` ficam média, melhor valor, desvio-padrão amostral, descarte, quantidade mantida, tempo, construções iniciadas (inclui a primeira), movimentos de busca local aceitos, observações válidas e falhas. As falhas não recebem peso.

## Medições disponíveis

A pasta `resultados_ubuntu` contém execuções independentes da versão C++20 compilada com g++ 15.2.0 no Ubuntu 26.04 LTS via WSL2. O processador é um Intel Core i9-11900H de 2,50 GHz. O host tem cerca de 32 GB físicos. O sistema convidado registrou 15 GiB de RAM disponíveis ao ambiente Linux. O arquivo `resultados_ubuntu.environment.txt` registra o ambiente real e os hashes do fonte e do executável.

A referência portátil em Python pode ser executada separadamente com o comando abaixo. O modo pareado observa quatro prazos na mesma trajetória e não deve ser confundido com os quatro processos independentes da bateria Ubuntu.

```sh
python3 experiment.py --paired --out nova_bateria_local
python3 exact_dense.py
```

Para a qualidade unitária, a referência é a coluna αk de Januschowski e Pfetsch na Tabela 4 de Kuryatnikova, Sotirov e Vera. Para DSJC125.9, `exact_dense.py` fornece também um ótimo ponderado independente. O verificador enumera todos os conjuntos independentes e maximiza a soma de até quatro conjuntos disjuntos. A poda usa o peso da classe corrente como teto para cada classe restante, pois as classes estão em ordem decrescente. Nos demais casos ponderados, o melhor obtido é uma referência empírica. A comparação entre os quatro algoritmos de controle é um experimento separado no documento.

Fonte dos valores de referência: [Kuryatnikova, Sotirov e Vera, Tabela 4](https://arxiv.org/pdf/2001.09644).
