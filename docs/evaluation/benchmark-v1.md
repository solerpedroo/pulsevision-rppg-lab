# Runner de benchmark v1

A infraestrutura funciona com dados locais declarados. Atualmente não há
benchmark fisiológico executado: o usuário não possui UBFC-rPPG/PURE.

## Demonstração artificial reproduzível

Na raiz, usando novos diretórios:

```bash
uv sync --locked
uv run python -m benchmarks.runners.synthetic --output artifacts/benchmark-demo/inputs
uv run python -m benchmarks.runners.run freeze artifacts/benchmark-demo/inputs/manifest.json \
  --output artifacts/benchmark-demo/lock.json
uv run python -m benchmarks.runners.run run artifacts/benchmark-demo/inputs/manifest.json \
  --lock artifacts/benchmark-demo/lock.json --split development \
  --output artifacts/benchmark-demo/results
```

São quatro identidades sintéticas, RGB artificial e referência de frequência conhecida.
Não são sujeitos humanos nem ground truth fisiológico. Um evento artificial de
movimento testa abstenções/recuperação; a referência possui relógio independente a 60 Hz.
Nenhum dataset é baixado automaticamente.

Saídas: benchmark-v1.json, windows.csv, participants.csv, benchmark-v1.md e figures/green.png,
chrom.png e pos.png. Relatório inclui erro, coverage, motivos, exclusões, métricas
por participante e versões. Timestamps não se tornam independentes por haver
janelas sobrepostas. Gráficos/LoA por janela são apenas descritivos.

Reexecuções com o mesmo lock produzem métricas e linhas de avaliação idênticas.
Tempos de execução variam. Se o código, ambiente ou dados mudarem, gerar novo lock
apenas em desenvolvimento e registrar motivo; não contornar avaliação final congelada.

## Preparação para dados reais

1. Obter dados pelos responsáveis e registrar termos/permissões/versão em data/,
   junto à autorização de pesquisa aplicável. Não versionar esse registro pessoal.
2. Inspecionar organização/codec e arquivos de referência. O adapter UBFC espera
   subject*/vid.avi + ground_truth.txt; não assume que toda distribuição é idêntica.
3. Documentar origem/unidades do tempo e offset numa evidência local. A declaração
   verified=true significa que isso foi verificado externamente, não pelo erro obtido.
4. Preencher manifesto a partir de benchmarks/configs/ubfc-manifest.example.json.
   Exemplo é incompleto e deve falhar até acesso/caminhos/verificação reais serem preenchidos.
5. Fixar participantes por development/validation/test, sem sessões da mesma
   pessoa em splits distintos. Definir critérios de elegibilidade antes de testar.
6. Em validação, confirmar ROIs em material autorizado e revisar qualidade de referência.
   Só então congelar manifesto/código/config e executar test sem retunar.

RGB pode vir da extração anterior (com trace_provenance), ou diretamente de vídeo
com model_path local. O runner remove o CSV intermediário após sessão.
PURE: somente parser de referência preparado; imagem→timestamp→RGB ainda deve
ser validado contra o pacote autorizado antes de alegar suporte end-to-end.

## Denominadores e interpretação

eligible_windows: janelas completas com referência utilizável no mesmo intervalo útil espectral.
excluded_windows: janelas agendadas sem referência confiável ou incompletas.
abstained_windows: elegíveis com BPM null. Não remover abstenções para reportar só erro.
Sessões sem comparação completa aparecem em session_failures, com contagem de
janelas não atribuída; não inseri-las artificialmente no denominador.
Participants sem pares continuam visíveis com erro null.

Resumo principal: média igualmente ponderada das métricas individuais. Coverage
por janela e macro por participante são diferentes; ambos são reportados.
IC é bootstrap de participantes com pares e não inclui magicamente dados ausentes.
Nenhuma correlação quando a série é constante. Associação não é concordância.
Leia ADR 0008 para fórmulas, limites temporais, defaults e interpretação de LoA.

## Erros intencionais

- Mudança de arquivo/config/code após freeze: execução recusada.
- Sobreposição de participantes: manifesto recusado.
- Acesso real sem confirmação/registro: manifesto recusado.
- Alinhamento não verificado: sessão excluída, sem métricas.
- Referência inválida: exclusão explícita, sem referência fabricada ou offset otimizado.
- Tentativa de rotular sintéticos como test fisiológico: execução recusada.

O intervalo de referência é o interior espectral comum após corte de bordas,
derivado somente dos timestamps e da configuração, independentemente da aceitação
do método. reference_start_s/reference_end_s são exportados separadamente da
janela nominal de análise. Isso evita comparar média do sensor em 20 s contra
um espectro calculado em um interior menor. Em falha de temporização, usar o
interior nominal pré-declarado e preservar a abstenção; não otimizar o intervalo
para obter erro menor. Regra idêntica para os três métodos.

O manifesto permite condition por sessão (rótulo declarado pelo pesquisador,
sem inferir características da pessoa). summary_by_condition mantém agregação por
participante dentro de cada condição, além do resumo global. O report registra
offset/origem, verificação e hash da evidência de alinhamento por sessão.
O runner requer checkout local do monorepo para fingerprint do código/lockfiles;
não é anunciada execução de benchmark a partir de wheel isolado sem fontes.
