# Verificação da Onda 10 — 2026-11-08

História: benchmark offline congelado → revisão portátil → importação local →
filtros/gráficos → exportação voluntária → descarte da aba.

- Runner Python real em RGB/referência originais artificiais, três participantes,
  três métodos e janelas de 10/20/30 s. Não houve rosto/dataset humano.
- Estudo bloqueia alteração do plano e de entradas após congelamento; não sobrescreve
  saída existente. Comparação PNG e relatório Markdown foram gerados e inspecionados.
- Resumo recomputado da revisão corresponde ao resumo original de cada execução.
  Sem pares aceitos: erro null, sem referência inventada; abstenções continuam na cobertura.
- Pydantic/JSON Schema/TS gerados; testes de elegibilidade sem referência, janela
  duplicada, formato desconhecido e mistura artificial/real recusam os arquivos.
- Chromium abre bundle gerado pelo próprio runner, filtra janela/método/participante,
  mostra gráficos/tabela e exporta CSV. Descartar retorna ao estado sem dados.
- JSON importado não é enviado: nenhuma chamada /api ou método de envio durante
  o fluxo de revisão. Sem exceções de página e sem overflow horizontal do documento.
- Screenshots desktop/mobile revisados; gráficos/tabela possuem rolagem interna
  para manter rótulos legíveis em viewport estreito. Arquivos locais em artifacts/.
- Não houve coleta de dados, download de dataset, experimento em pessoa ou comparação
  anatômica real. Protocolos A–E são draft; resultados sintéticos não são avaliação clínica.

Validação: 230 testes Python, 30 Vitest, 9 Playwright no conjunto completo; Ruff,
mypy (67 fontes), ESLint, TypeScript e build passaram. Após ajuste visual de
rolagem dos gráficos, os dois E2E de benchmark e build foram verificados novamente.
Schemas/tipos regenerados e formatação/diff verificados. CI configurada, sem
execução remota. Servidores de testes foram encerrados.

PV-1004–PV-1008 e a conclusão científica final de PV-1010 permanecem pendentes dos
dados autorizados e congelamento definitivo. CLI/relatório não validam a veracidade
de declarações de acesso/alinhamento ou de transformações criadas externamente.
