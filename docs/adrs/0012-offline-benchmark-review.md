# ADR 0012 — Benchmark Lab, revisão portátil e estudos congelados

Status: aceito · 2026-11-08 · PV-1001–PV-1003/PV-1009.
Experimentos reais PV-1004–PV-1008 e conclusão científica de PV-1010 pendentes.

## Contexto

O usuário não dispõe de UBFC/PURE autorizado. O runner da Onda 6 já calcula
pares, exclusões, cobertura, métricas por participante e relatórios com hashes.
A Onda 10 pode tornar esses resultados inspecionáveis e preparar execução em lote,
sem fabricar avaliação em pessoas nem tratar proxies RGB como vídeos degradados.

## Decisão

Criar contrato `benchmark-review-v1` em Pydantic, exportar JSON Schema e gerar TS.
Uma revisão contém até 64 execuções e 100 mil janelas, com metadados de sessão,
ROI/janela, natureza artificial/real, parâmetros, seed, versões/hashes, falhas,
suporte de referência e abstenções. A fonte científica continua sendo o runner;
o conversor não estima BPM ou inventa referência a partir de métricas agregadas.

`benchmarks.analysis.review` converte relatórios benchmark-v1 e escreve JSON,
summary JSON, Markdown e comparação PNG. Suporte de referência inexistente em
janela previamente excluída é representado como null, não intervalo invertido
aparentemente utilizável. Originais permanecem nos relatórios de cada execução.

`benchmarks.study` declara variantes por manifesto/lock/split e experimento A–E.
Congela o hash do plano, locks de entradas e estado do código antes de executar.
Cada variante reutiliza verify_lock/run_benchmark; alteração de configuração,
entrada ou plano invalida a execução. IDs não permitem caminhos arbitrários de
saída. Diretórios existentes não são sobrescritos; falha remove somente a nova
saída do estudo. Não há otimização automática de parâmetros/offsets ou downloads.

A demonstração executa o mesmo RGB artificial de três participantes sintéticos
em janelas de 10/20/30 s e GREEN/CHROM/POS. Rótulos de cenário indicam geração
artificial. Não simular uma comparação anatômica renomeando combined como testa.
Protocolos A–E permanecem em `benchmarks/protocols/experiments-v1.json` como draft,
com pré-condições para acesso, transformação de pixels, PTS e referência real.
Não são experimentos concluídos ou pré-registro independente.

## Interface

`/benchmark` importa apenas JSON normalizado, localmente, até 20 MiB. Usa schema
AJV e validações relacionais equivalentes às do contrato: natureza/dataset,
referência/elegibilidade, duplicatas e sessões declaradas. Nada é enviado à API.
A página começa vazia, sem métricas de demonstração carregadas automaticamente.
Descartar revisão limpa a aba; não remove o arquivo original ou downloads.

Filtros por execução/método/ROI/cenário/participante/janela; agrupamentos por
método, participante, ROI, cenário e janela. Cada grupo mantém a execução separada:
não agregar execuções/datasets distintos em uma média enganosa. Erros usam média
com peso igual por participante com pares, conforme runner. Janelas elegíveis
rejeitadas permanecem no denominador da cobertura; sessões sem contagem conhecida
continuam como falhas separadas. Nenhum par → erro null; zero cobertura ≠ precisão zero.

Gráficos e tabela mostram erros condicionais e cobertura juntos; motivos/falhas
ficam disponíveis. CSV exporta o recorte completo, mesmo quando gráficos/tabela
estão paginados em 18 grupos. JSON exporta a revisão integral importada. Valores
numéricos não são recalculados a partir do que foi arredondado na tabela. CSV
neutraliza fórmulas em rótulos de texto; números negativos continuam numéricos.

A UI não recalcula bootstrap/intervalos de confiança nem escolhe vencedor. O
summary JSON offline retém o bootstrap por participante do agregador. Comparações
com janelas diferentes também mudam resolução espectral/suporte de referência.
Custo computacional da execução não é latência sensor→tela.

## Rastreabilidade e limites

Hashes são registrados pelo conversor/runner e exibidos; o navegador não tem os
arquivos originais para verificá-los. Schema não autentica declaração de acesso,
licença, sincronização ou integridade científica de um arquivo externo. A interface
sempre explicita isso e mantém identificação artificial/real visível.

Relatório Markdown contém hipótese, método, resultados descritivos, origem,
pendências, limitações e trabalhos futuros. É relatório de infraestrutura quando
executado com dados artificiais; não substitui o relatório científico final.
Blur/compressão/movimento reais e avaliação com ground truth permanecem pendentes.
Não há implementação de release/deploy da Onda 11 nesta alteração.
