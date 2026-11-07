# Protocolo metodológico v1

Status: regras metodológicas fixadas; parâmetros e manifesto de dataset pendentes.
Não houve aquisição de dataset, execução de benchmark nem resultados científicos.

## Particionamento e congelamento

Separar desenvolvimento, validação e teste por participante; sessões do mesmo
participante pertencem ao mesmo conjunto. Ordenar identificadores e registrar
manifesto explícito com seed 42. Tamanhos serão definidos conforme dataset autorizado,
antes de qualquer avaliação final. Ajustar filtros, ROIs e gates apenas na validação.
Antes do teste, congelar manifesto, configuração, versão de código e ambiente.
Mudanças posteriores exigem nova versão de protocolo e justificativa.

## Tempo e referência

Usar PTS e timestamps de referência na mesma base temporal; registrar origem,
unidades e offset fornecido pelo dataset. Sem sincronização verificável, não calcular
erros. Não otimizar offset pelo erro no teste. Estimar referência no mesmo intervalo
da janela, documentando método de extração de HR. Recusar lacunas sem interpolação
arbitrária. CFR/VFR e políticas de exclusão serão testados nas ondas de aquisição.

## Estimativas e abstenção

Ponto de partida: janelas de 20 s, stride 1 s e busca 0,7–3 Hz, sujeitos à validação.
Esses valores não são limites clínicos. Registrar toda janela elegível, inclusive
abstenções com motivo. Nunca carregar BPM anterior como atual.
Registrar duração, ROI, método, filtros, bordas válidas e causalidade.

## Métricas e agregação

MAE, RMSE, MedAE e bias (estimado menos referência) em pares temporalmente válidos.
Pearson apenas quando amostra e variância permitirem; caso contrário, indisponível.
Cobertura = janelas aceitas / elegíveis; se denominador zero, indisponível.
Reportar contagens de exclusão antes da elegibilidade e motivos de abstenção.
Agregar primeiro por participante; publicar distribuição e síntese por método.
Bland–Altman deve explicitar medidas repetidas. IC via bootstrap de participantes
quando a amostra permitir; registrar seed e número de reamostragens.
Reportar latência/FPS com hardware, distinguindo aquisição de processamento.

## Rastreabilidade

Cada execução registra protocolo, dataset/versão/licença, participantes, seed, commit,
ambiente, parâmetros, referência, alinhamento e exclusões. Nunca inventar medidas.
Teste final só inicia após revisão do protocolo e manifesto congelados.
