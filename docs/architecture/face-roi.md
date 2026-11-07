# Extração RGB — Onda 2

Este módulo transforma vídeo em médias RGB de regiões faciais e motivos de
rejeição. Não calcula sinal rPPG, frequência cardíaca ou qualidade clínica.

## Execução

Na raiz:

```bash
uv sync --locked
uv run python scripts/fetch_face_model.py
uv run python -m rppg_core.roi.extract_rgb /caminho/video.mp4 \
  --model models/face_landmarker.task --output artifacts/sessao/rgb_traces.csv
```

O download é uma ação separada e verifica versão/hash documentados. Não baixa
imagens de pessoas ou datasets. O modelo oficial é mantido fora do Git.

CSV: timestamp_s, roi, r_mean/g_mean/b_mean, valid_pixel_fraction, landmark_status,
motion_score, roi_area, valid_pixels, dark_fraction, saturated_fraction, brightness
e quality_flags (array JSON). Canais seguem RGB 0–255, médias aritméticas após
exclusão de pixels inválidos. Nunca confundir entrada PyAV RGB24 com BGR OpenCV.
As quatro ROIs são forehead, left_cheek, right_cheek e combined.
RGB vazio significa rejeição; nunca substituir por zero ou valor anterior.
Status e flags explicam ausência/múltiplas faces, tracking, geometria e fotometria.

Um arquivo .metadata.json registra versão das ROIs, hash do modelo, parâmetros
e contagens. Não sobrescreve arquivos existentes. Erros de leitura/detecção não
publicam CSV parcial. CSV e metadados não formam uma transação resistente a
crashes entre arquivos; só consumir pares completos.
Nenhum preview ou vídeo de rosto é salvo automaticamente.

## Uso em código

MediaPipeDetector é um context manager, um por sessão; RGBExtractor mantém
continuidade temporal. Seu método extract(VideoReader(...)) entrega Observation.
Observation.sample é RGBSample somente quando a ROI passa nos gates; stats e
flags continuam disponíveis para auditar rejeições. Use um novo extractor para
reiniciar vídeo. Interromper processamento cedo exige fechar o gerador consumidor.

## Validação

```bash
uv run pytest tests/test_roi.py
```

Testes geométricos e de extração usam landmarks e imagens sintéticos. O teste
local com modelo real é executado se models/face_landmarker.task existir; na CI
offline esse teste é pulado. Nenhuma precisão em rostos reais foi medida.
Inspeção visual de material autorizado ainda é necessária para validar índices,
margens e cobertura em condições reais antes de alegar robustez.
Decisões e thresholds: docs/adrs/0004-face-roi-rgb.md.
