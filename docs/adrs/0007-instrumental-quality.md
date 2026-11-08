# ADR 0007 — Qualidade instrumental, abstenção e validade temporal

Status: aceito · 2026-11-07 · PV-0501–PV-0508

## Decisão

SignalQualityService avalia evidências instrumentais por janela, sem score de
confiança clínica. QualityConfig quality-v1 é imutável, versionada em JSON e
exportada com parâmetros de DSP/métodos. Os thresholds de pico herdados
(min_peak_fraction e max_competing_peak_ratio) permanecem em SignalConfig para
compatibilidade numérica; o serviço central coordena sua avaliação.

QualityAssessment opcional foi adicionado a EstimateResult: passed, metrics,
evaluated_checks e warnings. Passed deve concordar com disponibilidade de BPM.
Fixtures antigas continuam válidas sem quality. Não confundir checks disponíveis
com comprovação de pulso: dados desconhecidos não viram confiança positiva.
ReasonCode enumera motivos estáveis; flags de origem desconhecidas causam
unknown_quality_flag e deixam o nome original em warnings.

## Evidência facial e fotométrica

O loader CSV preserva landmark_status, flags e estatísticas opcionais de pixel,
movimento e brilho. Status/flags são declarações da extração, não verificação
independente de identidade ou presença de uma pessoa. Nunca inferir identidade.
Qualquer amostra rejeitada invalida a janela; não removê-la antes do DSP.
Limites iniciais: fração válida >=0,5, >=30 pixels, movimento <=0,08,
fração escura <=0,4 e saturada <=0,1.
Face ausente, múltiplas faces, geometria inválida, tracking interrompido e mudança
da composição da ROI têm causas separadas. Pode haver mais de uma causa na janela.
Uma janela inteiramente sem face usa no_face; mistura de frames usa unreliable.

Tracking reset da primeira linha de uma sessão CSV é inicialização; o loader
remove somente esse marcador inicial da evidência para o gate. Reset posterior
bloqueia todas as janelas que o contêm. API com evidência montada manualmente deve
distinguir inicialização de perda de tracking, preservando interrupções reais.

## Iluminação e amostragem

Usar brilho original da ROI quando fornecido em todas as linhas; caso contrário,
média RGB é proxy, explicitamente sinalizado. Limites: CV de brilho <=0,1 e
mudança relativa por amostra <=0,2. Amostras RGB médias escuras (<25) ou com canal

> =245 também têm gates de fração (0,4 e 0,1). Eles não substituem distribuição de
> pixels e segmentação; são verificações complementares.
> CV dos intervalos <=0,2; cobertura temporal >=0,9, estimada como
> min(1, N*mediana_intervalo/duração_da_janela). Não é porcentagem de câmera capturada
> com ground truth. Os limites de gap, bordas e Nyquist da Onda 3 continuam ativos.

## Energia e pico

Pico, concentração e competidores usam o espectro do método; suas medidas são
preservadas inclusive em rejeições quando calculáveis. Medir também energia em
banda no G normalizado/detrended ainda não filtrado: fração >=0,25 do total
positivo. É uma evidência comum de interferência, não SNR fisiológico.
Pode rejeitar CHROM/POS úteis quando G contém ruído que esses métodos removem;
o custo em cobertura precisa ser medido na validação. Nenhum ajuste por resultado
do teste final. Flicker periódico de baixa amplitude ainda pode passar.

## Continuidade e resultados vencidos

EstimateContinuity é isolado por sessão/método/ROI e exige fim de janela crescente.
Primeira janela completa válida pode ser aceita. Mudança >15 BPM exige duas
janelas candidatas consecutivas dentro de 6 BPM: enquanto pendente, degraded,
BPM null e unstable_between_windows. Não suavizar nem carregar o BPM anterior.
Após falha ou gap de histórico >3 s, exigir duas candidatas válidas; a primeira
fica warming_up/recovering_signal. Esse atraso é instrumental e pode suprimir
mudanças fisiológicas reais. Janelas sobrepostas não são provas independentes.
Configurar max_history_gap_s >= stride_s; a análise recusa configuração incompatível.

display_estimate retorna cópia; idade = now_s − produced_at_s na mesma base da
sessão. Idade >3 s suprime BPM com stale_estimate/degraded e marca stale=true.
Limite é inclusivo. Não altera histórico nem repõe valor antigo após falha.
Histórico offline continua datado; aplicar freshness somente ao exibir como atual.
analyze_window é stateless; analyze_trace aplica continuidade entre seus resultados.

## Cobertura e limites de escopo

summarize_quality conta todas as janelas fornecidas, aceitas e abstenções;
coverage=aceitas/elegíveis, ou null para conjunto vazio. Motivos são contados uma
vez por motivo/janela; somas por motivo podem exceder abstenções.
Exportadores usam o helper por método, preservando aquecimento/rejeições.
Elegibilidade aqui é o agendamento de análise (inclui o resultado diagnóstico de
trace curto); protocolo específico de exclusão de dataset será aplicado antes
dos gates na Onda 6 e deverá ser reportado separadamente.
Não existe benchmark fisiológico nesta onda.

Os limites são heurísticos iniciais; teste sintético demonstra comportamento,
não calibração, sensibilidade clínica ou segurança em monitoramento.
