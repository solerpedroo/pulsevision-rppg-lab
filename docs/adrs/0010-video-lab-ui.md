# ADR 0010 — Video Lab, preview local e inspeção temporal

Status: aceito · 2026-11-08 · PV-0801–PV-0810

## Contexto

A Onda 7 oferece jobs isolados e resultados históricos. A Onda 8 precisa tornar
esse fluxo utilizável no navegador, incluindo abstenções e geometria verdadeira,
sem implementar captura ou DSP de webcam. Não há dataset ou rosto autorizado
para validação fisiológica/visual positiva.

## Decisão

Next.js mantém layout e rotas server; `/` redireciona para `/video`. A feature
`apps/web/features/video` separa cliente HTTP/paginação, orquestração da sessão,
preview por frame e gráficos SVG. O navegador abre o arquivo por object URL;
selecionar um arquivo não o envia. Upload binário ocorre após autorização marcada
e clique explícito, com destino e retenção visíveis. Somente origens loopback são
configuráveis; chave opcional permanece em memória da aba.

O backend segue como autoridade para formato, cadência e limites. A UI verifica
extensão, bytes, duração/resolução reportadas pelo decoder do navegador. Aceitação
pelo navegador não garante suporte pelo decoder Python, nem o contrário.
Não há upload de URL remota, autoanálise ou reprodução de BPM anterior.

Cada alteração de método/ROI exige novo job. A UI exclui o job anterior antes de
enviar novamente o mesmo arquivo escolhido, evitando misturar configurações.
Polling tem um único timer com cleanup/abort. Resultados e geometria são paginados;
RGB, rPPG e PSD são lidos completos, sem truncar janelas de maior FPS.
BPM null interrompe linhas, mantém motivo e janela e aparece como traço ausente.
Cobertura é fração de janelas aceitas, nunca precisão ou confiança clínica.

O núcleo oferece um observer opcional das máscaras reais, com timestamps do
VideoReader e orientação aplicada. Só o subprocesso converte essas máscaras em
contornos externos normalizados e grava `roi.json`, servido pela série `roi`.
Sem face, múltiplas faces ou geometria inválida, registra regiões vazias naquele
instante. Não se guardam frames, landmarks de identificação ou vídeo de preview.
São contornos dominantes simplificados em 1,5 pixel, não uma representação exata
dos pixels fotometricamente aceitos nem de todos os furos/exclusões da máscara.
Contorno pode existir mesmo quando qualidade temporal/fotométrica rejeita RGB.

O overlay usa `requestVideoFrameCallback`/mediaTime quando disponível, com estado
isolado dos gráficos. Há fallback por timeupdate/seeked; em lacunas >250 ms não se
reutiliza uma geometria antiga. Browser time e timestamps científicos são relativos
ao início do vídeo; containers com edições/timelines incomuns exigem inspeção
manual antes de alegar alinhamento exato. Gráficos permanecem históricos offline.
A janela inspecionada acompanha a reprodução enquanto contém o instante atual;
ao sair dela, a UI escolhe uma janela que contenha o novo instante. Seletores e
scrubber permitem inspeção explícita. Atualização por frame não recalcula DSP.

Gráficos mostram eixos/unidades e lacunas, sem bandas clínicas ou dados de exemplo
apresentados como resultados. Controles nativos, skip link, foco visível, labels,
status/progresso e texto dos motivos atendem o fluxo de teclado. Live Lab e
Benchmark permanecem desabilitados, sem implementar ondas seguintes.

## Consequências e limites

Backend e UI devem rodar localmente; não há publicação nesta onda. Não há retomada
automática da sessão ao recarregar a aba: chave, arquivo e estado não são gravados
em localStorage. Jobs já aceitos continuam sujeitos ao TTL do servidor.
Fechar a aba revoga seus object URLs, mas não equivale a cancelar um job aceito.
Derivados geométricos são dados faciais e recebem os mesmos limites/TTL/exclusão.
Excluir sessão também descarta arquivo/preview locais e autorização da UI;
404/410 permitem limpar o estado de um job já removido/expirado.
Downloads explícitos pertencem ao usuário e não podem ser retraídos por DELETE.

Playwright testa o fluxo real com vídeo original sintético sem rosto e modelo
local, incluindo recálculo e revogação do job antigo; respostas simuladas testam
estados determinísticos de cancelamento/falha e indisponibilidade da conexão.
Geometria positiva usa detector/landmarks sintéticos em testes do núcleo.
Isso não comprova robustez de ROIs reais, precisão de BPM ou validação clínica.
