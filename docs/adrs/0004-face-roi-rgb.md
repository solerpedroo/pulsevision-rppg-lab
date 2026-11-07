# ADR 0004 — Face Landmarker, ROIs e RGB

Status: aceito · 2026-11-07 · PV-0201–PV-0209

## Decisão

MediaPipe 1.2.2, Face Landmarker VIDEO em CPU, bundle float16 versão 1.
OpenCV contrib 5.0.0.93 é a dependência do MediaPipe e fornece rasterização.
Não instalar simultaneamente pacotes OpenCV headless e contrib: ambos fornecem cv2.
A implementação usa apenas operações de array, sem janelas ou câmera.

single_face_only=True é obrigatório. num_faces=2 permite rejeitar múltiplas
detecções; configurar num_faces=1 ocultaria a segunda face. Isso desabilita o
smoothing automático restrito a num_faces=1. Não há identificação nem rastreamento
de identidade. Não habilitar blendshapes ou matrizes de expressão.

Rotacionar RGB conforme DISPLAYMATRIX antes do detector e das máscaras, sem
espelhamento. Somente múltiplos de 90 graus são aceitos; rejeitar outros valores.
Usar milissegundos floor(timestamp_s*1000) no detector, preservando segundos
originais no CSV. Colisões na precisão em ms geram erro, sem fabricar timestamps.

## Geometria roi-v1

Polígonos conservadores de testa e bochechas usam índices fixos MediaPipe 478.
Left/right são lados anatômicos para imagem não espelhada. Reduzir polígonos a
85% em torno do centro; excluir olhos, boca e sobrancelhas por landmarks.
Coordenadas inválidas, polígonos fora dos limites ou degenerados invalidam o frame.
A região combined é a união das ROIs válidas: média ponderada por pixels, sem
contar sobreposição duas vezes. Regiões parciais geram flag partial_roi.

Não existe segmentação semântica de cabelo/oclusores. Geometria e máscaras
fotométricas mitigam parte desses casos; não garantem pele em todos os pixels.
Nenhuma seleção de cor por etnia, tom de pele inferido ou atributo demográfico.

## Qualidade inicial

Descartar pixels com brilho médio menor que 25 ou algum canal >=245. Exigir
30 pixels válidos e fração >=0,5. Registrar frações escura/saturada, área e brilho.
Movimento é RMS de deslocamento dos landmarks normalizado pela diagonal do
bounding box anterior. Limites iniciais: movimento 0,08, escala relativa 0,2,
mudança de brilho 0,2 e gap de tracking 0,25 s.
Esses parâmetros são heurísticos, não calibrados; mudar somente em validação.
A política completa de qualidade/janelas permanece na Onda 5.

Sem face, múltiplas faces ou geometria inválida limpam a referência de tracking.
Não carregar RGB anterior. Retorno após interrupção recebe tracking_reset.
CSV mantém quatro linhas por timestamp, inclusive rejeições com RGB vazio.
Consumidores futuros devem respeitar flags/gaps e não interpolar arbitrariamente.

## Artefatos e privacidade

CLI requer --model e --output explícitos. Sem auto-download durante inferência.
Script separado baixa URL versionada e verifica SHA256. Pesos em models/ fora do Git.
CSV só é publicado após consumo completo do vídeo, sem substituir saída existente.
Metadados registram hash do modelo, parâmetros e contagens. Nenhum frame/preview
é salvo nesta onda. Visualização com rostos exigirá ação explícita.

## Evidências e limites

Testes sintéticos validam geometrias, máscaras, transformação, tracking e pipeline
VideoReader→RGB. Teste local usa o modelo real em vídeo/imagem sem rosto.
Isso não valida precisão geométrica em pessoas: inspeção em material autorizado,
incluindo iluminação variada, segue pendente antes de alegações de robustez.
As heurísticas não garantem detectar toda oclusão ou troca de pessoa.
