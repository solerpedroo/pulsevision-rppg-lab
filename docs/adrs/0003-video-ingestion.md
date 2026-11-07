# ADR 0003 — Ingestão temporal com PyAV

Status: aceito · 2026-11-07 · PV-0101–PV-0107

## Contexto

A primeira etapa do núcleo científico precisa preservar apresentação temporal
em vídeos CFR e VFR. O Fedora desta sessão não possui executável ffmpeg.

## Decisão

Usar PyAV 19.0.2 e NumPy 2.5.4 pinados, com bibliotecas FFmpeg do wheel.
Não instalar pacotes do sistema nem reconstruir timestamps a partir do FPS.
Selecionar o primeiro stream de vídeo. A API entrega RGB24 na orientação
codificada, junto à rotação DISPLAYMATRIX (graus anti-horários). Não girar
pixels implicitamente: a etapa ROI terá de consumir essa orientação.

FrameSample mantém índice, PTS, base racional, timestamp original e segundos
relativos ao primeiro frame. PTS pode começar negativo ou fora de zero;
a normalização conserva intervalos e mantém a origem original auditável.
Comparar tempos como frações antes da conversão para segundos.

PTS ausente, repetido ou regressivo interrompe a leitura com erro tipado.
Imagens iguais com PTS distintos são mantidas. Gap é diagnóstico: intervalo
maior que gap_factor / FPS informado (padrão 2,5). Não é prova de frame perdido:
um VFR legítimo também pode ser sinalizado. Sem FPS informado não há esse gate.
Amostras não são interpoladas, removidas ou reordenadas.

## Integridade e recursos

Leitura sequencial com memória de pixels limitada ao consumo do gerador.
Cada iteração abre um container; término ou close() fecha-o. Ao interromper
cedo, usar contextlib.closing(reader.frames()). Metadados decodificam o primeiro
frame para obter rotação, mas não validam o vídeo inteiro.
Falha de abertura, ausência de vídeo/decoder, falha de decode/corrupção e erro
temporal têm códigos próprios. Contagem final divergente da declaração do
stream também invalida a leitura. Consumidores devem descartar resultados
parciais se o gerador terminar com erro.

O decoder não detecta toda corrupção possível. Contêiner sem contagem confiável
pode terminar limpo após truncamento. Não prometer validação forense de integridade.
Sem seek nesta onda. Nenhum endpoint HTTP ou upload é introduzido.

## Evidências e suporte

Testes geram imagens constantes 64×48, CFR 25 FPS, VFR e origem deslocada:
MP4/MOV com MPEG-4 Part 2 e WebM com VP9, usando codecs presentes no wheel.
Isso não implica suporte a todos os codecs possíveis nessas extensões.
Fixtures são temporárias e sem rostos; nenhum arquivo de vídeo é versionado.
A CLI emite JSON com metadados, timeline, FPS efetivo, intervalos e versões;
erro produz código de saída 2. O relatório acumula apenas metadados da timeline,
portanto seu uso de memória cresce com o número de frames.

Documentação de referência consultada:
https://pyav.basswood.io/docs/stable/api/time.html
e https://pyav.basswood.io/docs/stable/api/video.html.
