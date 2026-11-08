# ADR 0011 — Webcam local, worker e janela passada

Status: aceito · 2026-11-08 · PV-0901–PV-0913

## Contexto

O Video Lab já utiliza a API offline. A webcam deve operar no navegador, com
consentimento explícito, timestamps verificáveis, descarte e abstenção. A execução
síncrona de Face Landmarker não deve bloquear a thread do preview. Não há material
humano autorizado ou validação fisiológica para testar uma estimativa positiva.

## Decisão

`/live` utiliza getUserMedia somente após Iniciar câmera, sem áudio. Detecta
recursos/contexto seguro antes da captura. Seleção de outro dispositivo encerra
a sessão e exige novo Start. Stop, unmount, pagehide, perda de foco/visibilidade,
track ended, erro do worker e watchdog liberam tracks, encerram worker e descartam
buffers. Resolução tardia de uma permissão já cancelada também libera seus tracks.
Não há reinício automático após retorno de foco ou refresh.

MediaPipe Tasks Vision JS 1.2.2, CPU, modo VIDEO, até duas faces para rejeitar
multiplicidade. Blendshapes e matrizes faciais permanecem desligados. Assets WASM
da dependência pinada e modelo float16/1 são preparados explicitamente por
`npm run live:assets`; não há CDN, download automático ou cópia de pesos no Git.
O script e o browser verificam SHA256 do modelo. A preparação copia apenas o
modelo local já verificado e o runtime npm para uma pasta public ignorada.
Não autoriza redistribuição/publicação desses assets.

A aquisição usa requestVideoFrameCallback/mediaTime; fallback usa currentTime
com deduplicação. Tempo é relativo ao primeiro frame analisado, não contador/FPS
nominal. Timestamps duplicados na resolução de milissegundos não são enviados
à inferência. Um único ImageBitmap fica em trânsito; callbacks sem análise são
contados separadamente. Backpressure descarta oportunidades sem fabricar amostras.
Preview mantém resolução/aspecto nativos; extração reduz a largura para até 320 px.
Espelhamento CSS atua conjuntamente sobre vídeo e overlay, sem espelhar a extração.

Worker clássico, isolado da UI, executa detector, rasterização, médias RGB, gates,
ring buffers e DSP. Contornos usam índices roi-v1 e shrink 0,85, com exclusões de
olhos/sobrancelhas/boca. Rasterização por centros de pixels difere do fillPoly do
OpenCV: não há alegação de equivalência de máscaras/pixels. Combined exige as três
regiões válidas e pondera RGB por pixels; é mais conservador que uma região parcial.
Ausência/múltiplas faces, geometria inválida, tracking, movimento, brilho/saturação
e pixels insuficientes preservam timestamp e RGB null/motivo.

## Perfil numérico live-v1

- Ring de 900 observações por ROI; exportação local dos últimos dados e até
  30 análises. Stop/unmount descartam tudo em memória; não gravar imagens.
- Janela passada de 20 s, atualização a cada 1 s de tempo de mídia, sem extrapolação.
- Reamostragem linear explícita para 30 Hz, com cadência mediana mínima de 12 Hz,
  gaps máximos 150 ms/2,5×mediana e gates de CV/cobertura temporal.
- GREEN, POS e CHROM seguem os kernels Python/classical-v1. Coeficientes SOS e zi
  Butterworth ordem 4, banda 0,7–3 Hz, a 30 Hz são exportados pelo Python.
- sosfiltfilt com extensão ímpar e Welch/Hann periódico sem zero-padding; margens
  de 1 s para GREEN e 1,6 s para POS/CHROM. Não é filtro incremental instantâneo:
  é análise não causal dentro de uma janela inteiramente passada.
- Parâmetros de qualidade provêm do config gerado; confirmação entre janelas,
  estabilidade e supressão de resultado com idade >3 s. Não suavizar/carregar BPM.
- Falha na captura atual bloqueia exibição até nova análise e não reescreve a
  proveniência de uma janela histórica. Freshness na UI tem deadline independente
  do recebimento de novos frames; watchdog encerra captura sem resposta.

A UI distingue cadência efetivamente analisada, processamento por frame e idade
na última captura. O tempo por frame inclui detector/RGB e DSP quando agendado;
não mede latência sensor→tela. Grade 30 Hz não equivale a 30 frames analisados/s.
Interpolação não recupera informação perdida ou elimina aliasing da aquisição.

## Verificação e consequências

`export_live_reference.py` gera constantes e três sinais RGB sintéticos a 30 Hz
(1,0/1,5/2,2 Hz), com referência Python de GREEN/POS/CHROM: nove comparações de BPM,
sinal, timestamps e PSD com tolerância absoluta 1e-9. Isso valida os kernels nesse
suporte; não prova equivalência do pipeline facial, de toda entrada irregular,
de condições reais ou de estimativas causais/instantâneas.

Testes de geometria usam landmarks originais artificiais. E2E Chromium usa câmera
Y4M original sem rosto, detector/WASM reais, sem câmera física. Exercita >20 s,
abstenção, exportação, Stop, permissão negada/tardia, mudança de seleção, eventos
de foco/visibilidade/track-ended, navegação e reload. Eventos de hardware/foco são
simulados quando não reproduzidos pelo modo headless. Inspeção humana autorizada,
robustez em dispositivos reais e outros navegadores permanecem pendentes.

Não há upload de frames ou dependência da API no Live Lab. Teste de rede recusa
métodos de envio, rotas /api e origens externas durante o fluxo. JSON derivado só
é baixado após ação explícita, com parâmetros, versão e hash do modelo. Download
já realizado não é retraído por Stop. Não há diagnóstico, SpO2, identidade facial
ou afirmação de precisão clínica.

Referências primárias: [guia Web](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js)
e [API detectForVideo](https://developers.google.com/edge/api/mediapipe/js/tasks-vision.facelandmarker).

## Correção de integração encontrada nesta onda

O E2E completo reproduziu o bloqueio intermitente do Video Lab já registrado na
Onda 8. Stack dump do subprocesso mostrou import de mediapipe → audio_record →
sounddevice → PortAudio Pa_Initialize, antes da inferência visual. Não era DSP
nem evidência de erro fisiológico. O bloqueio foi observado nesse caminho de áudio;
a condição exata dentro do driver/daemon de áudio não foi determinada.

O worker isolado de vídeo marca o módulo opcional sounddevice como indisponível
antes de importar o MediaPipe. AudioRecord da versão pinada trata ImportError;
a inferência visual continua real. Não se altera pacote instalado nem imports
no processo HTTP, no browser ou em consumidores genéricos do núcleo. Esse worker
não oferece áudio e não deve inicializar dispositivos de áudio por efeito colateral.
Teste de integração injeta um sounddevice que falha/gera marcador se importado;
o job precisa concluir com modelo real, sem disparar esse módulo.
