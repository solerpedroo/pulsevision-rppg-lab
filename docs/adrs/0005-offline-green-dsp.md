# ADR 0005 — DSP offline e GREEN

Status: aceito · 2026-11-07 · PV-0301–PV-0308

## Contexto

A extração RGB da Onda 2 produz timestamps reais e linhas sem RGB quando há falha.
Precisamos de um baseline mensurável em sinais artificiais antes de CHROM/POS.

## Decisão

SciPy 1.18.1 pinado. Núcleo fora de HTTP/React, operando arrays float64.
Janelas padrão de 20 s e passo de 1 s, limites [início, fim). A origem é o primeiro
timestamp. Para agendamento apenas, o fim da captura é aproximado pelo último
timestamp mais o intervalo mediano; não cria amostra ou PTS. Borda da janela
tolera até 1,5 intervalo entre limite e amostra. Cauda incompleta é omitida;
se o trace inteiro é curto, retornar uma janela com abstenção.

## Tempo e validade

Timestamps não finitos, negativos, duplicados/regressivos ou shapes inválidos
geram SignalInputError: não existe janela temporal confiável para atribuir resultado.
Uma janela conhecida sem dados suficientes retorna BPM null e motivo.
RGB inválido/NaN/Inf, ROI rejeitada ou descontinuidade não são removidos silenciosamente.
No CSV, preservar linhas rejeitadas. Tracking reset após a primeira linha e mudança
de composição de combined (partial_roi) invalidam a janela.

Cadência é a mediana dos intervalos. Só reamostrar quando intervalos não forem
uniformes (rtol 1e-5, atol 1e-9). Interpolação linear na cadência mediana, sem
extrapolação. Nenhum target FPS arbitrário ou downsampling nesta versão.
Recusar intervalo maior que min(0,15 s, 2,5 × intervalo mediano).
Isso permite preencher pequenas irregularidades/omissões; não é evidência nova.
Recusar fs/2 <= limite superior da banda antes do filtro. Isso não garante
ausência de aliasing na aquisição original.

## GREEN e filtro

G/mean(G)-1, depois detrend linear por janela. Não dividir por desvio padrão:
isso amplificaria sinais constantes/numericamente insignificantes.
Desvio após detrend <1e-6 causa abstenção.
Butterworth de ordem 4, 0,7–3 Hz, SOS e sosfiltfilt com padding ímpar.
O filtro é não causal: só para análise offline de uma janela completa.
Forward/backward duplica a ordem efetiva da resposta. Não comparar com variante
live sem documentar diferenças de causalidade e latência.
Descartar 1 s em cada borda antes da PSD. É margem heurística, não garantia
matemática de extinção dos transientes.

## Espectro e abstenção inicial

Welch: Hann periódico, segmento até 20 s limitado à duração útil, overlap 50%,
nfft=nperseg (sem zero-padding), detrend=False porque já houve detrending.
Uma janela de 20 s após corte de bordas fornece um único segmento de ~18 s;
não alegar redução de variância por múltiplos segmentos nesse caso.
Pico é o maior bin na banda. BPM=60*f; sem interpolação parabólica/suavização.
Registrar largura do bin em Hz/BPM: não confundir com acurácia ou intervalo de confiança.

Recusar pico nos extremos dos bins da banda, concentração do pico e vizinhos
imediatos <0,45 da energia na banda, ou outro pico fora de ±2 bins com potência

> 0,5 da potência dominante. São heurísticas provisórias.
> Harmônicos de amplitudes semelhantes causam ambiguidade; harmônico dominante
> com fundamental fraca pode passar. Iluminação periódica também pode passar.
> Não chamar detecção de periodicidade de confirmação de pulso.
> Qualidade completa e validação com referência continuam nas Ondas 5 e 6.

## Contratos e rastreabilidade

EstimateResult recebe metadata opcional, compatível com fixtures anteriores.
Gerar schema e TS juntos. Registrar modo offline, filtro, resampling e resolução.
produced_at_s é marcador na base da sessão (fim da janela), não relógio de execução.
WindowAnalysis inclui sinal, tempos e PSD para diagnóstico; falhas não recebem BPM anterior.
CLI registra config, versões, hash de entrada, contagens/cobertura e input_kind.
Marcador synthetic_reference é informação declarada no trace, não autenticação da origem.

Referências consultadas:

- https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.butter.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.sosfiltfilt.html
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html
