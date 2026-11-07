# Comparação única a 30 segundos

Execute no Ubuntu 26.04, nesta pasta:

```bash
bash run_comparison.sh
```

A execução compila C++20 com -O0, registra o ambiente e inicia uma bateria sequencial. A pasta padrão é comparacao_30s. Uma pasta existente bloqueia uma nova execução com o mesmo nome. O compilador precisa recompilar grasp.cpp, pois o executável antigo grasp contém somente a implementação anterior.

São 168 execuções sobre os mesmos doze cenários. Cada controle determinístico roda uma vez por cenário. O GRASP roda com sementes 1 a 10. Cada execução tem teto de 30 segundos, com preparação e inicialização incluídas. As três construtivas terminam ao concluir o algoritmo. Tabu termina no prazo ou após 100.000 iterações. O GRASP sozinho consome aproximadamente uma hora nesta bateria.

Os controles estão em controls.hpp. Briggs usa grau residual menor que k e escolha otimista por peso/grau. MIS usa grau residual mínimo no produto cartesiano, maior suporte como primeiro desempate e ordem vértice–cor como segundo. ADG remove grupos simultaneamente, com epsilon 0,1, e colore em ordem inversa dos grupos. Tabu inicializa por classes, protege inserções durante sete iterações seguintes, recoloca o removido por último e conserva a melhor solução por peso.

compare.py reaproveita a validação de colorações e o controlador externo de experiment.py. A escolha do algoritmo é transmitida por HEM_METHOD. A interface original continua disponível com o método grasp por padrão.

Os arquivos runs.jsonl, summary.csv, comparison.csv e RELATORIO.md preservam soluções individuais, métricas, ganhos por cenário e o resultado do critério operacional do documento. A comparação usa a média das dez sementes do GRASP e o melhor peso dos quatro controles. Falhas tornam o critério inconclusivo.

Estado da implementação nesta sessão: scripts Python verificados quanto à sintaxe e relatório de bateria incompleta exercitado. A compilação C++ e a bateria estão pendentes porque o WSL retorna Wsl/E_ACCESSDENIED e o MinGW local falha ao iniciar com erro de realocação de DLL.
