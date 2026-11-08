# Benchmark local

Infraestrutura disponível; avaliação UBFC/PURE real pendente de dados e acesso.
Use python -m benchmarks.runners.synthetic e python -m benchmarks.runners.run.
Guia completo: ../docs/evaluation/benchmark-v1.md.
Formatos: adapters/; manifestação/congelamento: manifest.py; execução: runners/;
métricas de erro: packages/rppg_core/metrics/; agregação/figuras: analysis/.
Resultados em artifacts/, fora do Git. Não colocar relatórios de dados restritos aqui.

Onda 10: `python -m benchmarks.study demo/freeze/run` orquestra variantes congeladas;
`python -m benchmarks.analysis.review` converte relatórios existentes para a UI.
Veja `../docs/architecture/benchmark-lab.md` e `protocols/experiments-v1.json`.
Protocolos reais A–E e relatório científico final permanecem pendentes; rótulo de
variante não valida nem implementa uma transformação externa de vídeo.
