# Aquisição de vídeo — Onda 1

A implementação é local, sequencial e independente de HTTP.
A saída não contém sinal rPPG, ROI ou BPM.

## Inspeção

Na raiz, após uv sync --locked:

```bash
uv run python -m rppg_core.acquisition.inspect_video /caminho/video.mp4
```

Saída JSON: metadata (codec, resolução, duração declarada, FPS informado,
base temporal, origem e orientação), decoder (versões PyAV/FFmpeg), timing
(contagem, span observado, FPS efetivo, intervalos e gaps) e timeline por frame.
Não inclui pixels, caminho pessoal ou referência fisiológica.
O span observado vai do primeiro ao último PTS; não inclui a duração de
apresentação do último frame e pode diferir da duração declarada no container.
FPS efetivo = (n−1)/span; com um único frame fica null. interval_cv mede
irregularidade observada; não classifica automaticamente o vídeo como defeituoso.
nominal_fps é o average_rate informado pelo PyAV/container, apenas informativo.

## Uso Python

```python
from contextlib import closing
from rppg_core.acquisition import VideoReader

reader = VideoReader("/caminho/video.mov")
metadata = reader.metadata()
with closing(reader.frames()) as frames:
    for sample in frames:
        print(sample.timestamp_s, sample.pts, sample.rgb.shape)
```

FrameSample usa array uint8 (altura, largura, 3), RGB24. PTS e time_base
permitem reconstituir o tempo original. timestamp_s inicia em zero e cresce
estritamente. A rotação não altera o array; leia rotation_degrees antes de
mapear coordenadas na Onda 2. Nenhum fallback de índice de frame é utilizado.

## Falhas

video_open_error: arquivo ausente/ilegível ou container inválido.
unsupported_video: nenhum stream de vídeo ou decoder disponível.
video_decode_error: stream vazio, frame corrompido, falha de decode ou contagem
divergente. invalid_timestamps: base inválida, PTS ausente, repetido/regressivo.
Cabeçalho truncado pode parecer container sem vídeo: o erro descreve a evidência
disponível, sem tentar adivinhar a causa física. Ao falhar, invalidar saída parcial.
O backend futuro mapeará esses códigos para status de jobs e mensagens ao usuário.

## Reprodução

uv run pytest tests/test_acquisition.py gera os vídeos em tmp_path e remove-os
pelo ciclo de vida do pytest. MP4/MOV MPEG-4 e WebM VP9 estão cobertos; codecs
diferentes dependem da build FFmpeg. Não é necessário ffmpeg CLI para esses testes.
Detalhes e limites de integridade: docs/adrs/0003-video-ingestion.md.
