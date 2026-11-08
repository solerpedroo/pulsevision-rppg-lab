# Métricas e população avaliada

Para pares aceitos: e_i = estimado_i − referência_i.
MAE = média(|e|); RMSE = raiz(média(e²)); MedAE = mediana(|e|); bias = média(e).
Pearson exige pelo menos dois pares e variância em ambas séries; não mede concordância.

Calcular cada métrica por participante antes da média de participantes, com peso
igual para cada pessoa com pares. Média de RMSEs não é RMSE pooled; média de
MedAEs não é mediana pooled. Nomes e aggregation registram essa escolha.
Reportar participantes sem pares e coverage junto aos erros condicionais à aceitação.

Bootstrap percentil usa participantes como unidade, com reposição, seed e número
de reamostragens fixados. Default: 1000; CI somente com >=3 participantes avaliáveis.
Esse mínimo é um critério operacional, não garantia de poder ou precisão.
Não fornece IC para LoA nem transforma janelas repetidas em observações independentes.

LoA descritivos = bias ±1,96*desvio padrão amostral dos erros.
Os gráficos com múltiplas janelas por indivíduo explicitam medidas repetidas;
a implementação não estima componentes de variância de um modelo hierárquico.
Concordância entre médias dos participantes é reportada separadamente.
Referência primária sobre o problema de medidas repetidas:
https://pubmed.ncbi.nlm.nih.gov/17613642/
Bland e Altman (2007), DOI 10.1080/10543400701329422.

Código recusa pares não finitos; não faz nanmean nem exclui silenciosamente
valores para reduzir erro. Gaps/alinhamento inválido são tratados antes dos pares.
Timing de DSP é medido em CPU no ambiente real da execução. Tempo de aquisição/IO
é compartilhado por sessão; não somá-lo três vezes ao comparar métodos.
