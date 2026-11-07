# PulseVision — rPPG Lab

Laboratório experimental para estimar frequência cardíaca por variações de cor
facial, com resultados rastreáveis e abstenção quando o sinal for insuficiente.
**Uso experimental; não é dispositivo médico.**

## Estado

Ondas 0–3: fundação, ingestão temporal, ROIs/RGB e baseline GREEN offline. Ainda não há câmera, upload,
CHROM/POS ou validação em pessoas. GREEN já estima periodicidade em traces RGB.
Leia [state.md](state.md), [arquitetura](docs/architecture/overview.md),
[protocolo](docs/evaluation/protocol-v1.md) e o plano original.
A evolução segue: ingestão temporal → ROI/RGB → GREEN → CHROM/POS → qualidade →
benchmark → API → interface e webcam.

## Setup Fedora/Linux

Requisitos: Git, uv 0.12.24 e Node 24 com npm. Python 3.12 é gerenciado pelo uv;
não substitua o Python do sistema. PyAV inclui bibliotecas FFmpeg no wheel; o executável ffmpeg não é exigido
para ingestão e fixtures desta onda.
Execute da raiz:

```bash
uv python install 3.12
uv sync --locked
npm ci
npm run dev --workspace apps/web
```

Abra http://localhost:3000. Não há servidor de API nesta onda.
Configuração de câmera, CUDA e datasets não é necessária.

## Verificação

```bash
uv run ruff check .
uv run mypy
uv run pytest
npm run format:check
npm run lint
npm run typecheck
npm test
NEXT_TELEMETRY_DISABLED=1 npm run build
```

Ao alterar contratos:

```bash
uv run python scripts/export_schemas.py
npm run contracts
```

Versione modelos, schemas e tipos gerados juntos. JSON Schema/TS não substituem
validações relacionais em runtime; consulte a arquitetura.

## Estrutura e colaboração

apps/web contém Next.js; packages/rppg_core o núcleo científico;
packages/rppg_types os contratos; services/api a reserva da futura API;
benchmarks o protocolo/configuração; docs decisões e políticas.
AGENTS.md orienta agentes; CLAUDE.md e .cursor/rules/ apontam para a mesma fonte.
Registre progresso em state.md, mudanças em CHANGELOG.md e decisões em docs/adrs/.
Dados privados e vídeos ficam fora do Git. Leia a política em docs/privacy/policy.md.
Código MIT; datasets e modelos seguem seus próprios termos.

## Inspeção de vídeo

```bash
uv run python -m rppg_core.acquisition.inspect_video /caminho/video.mp4
uv run pytest tests/test_acquisition.py
```

A CLI apresenta metadados e timeline com PTS reais em JSON. Suporte testado:
MP4/MOV com MPEG-4 e WebM com VP9. Veja
[contratos e limites da aquisição](docs/architecture/acquisition.md).

## Extração de RGB por região facial

```bash
uv run python scripts/fetch_face_model.py
uv run python -m rppg_core.roi.extract_rgb /caminho/video.mp4 \
  --model models/face_landmarker.task --output artifacts/sessao/rgb_traces.csv
```

Veja [uso e limites](docs/architecture/face-roi.md) e o
[registro do modelo](docs/research/face-model.md). Pesos ficam fora do Git.
Sem face ou ROI confiável, o CSV registra rejeição com RGB vazio.
A geometria em rostos reais ainda requer validação visual
com material autorizado.

## GREEN e análise espectral

```bash
uv run python -m rppg_core.signals.synthetic \
  --output artifacts/green-demo/rgb_synthetic.csv --bpm 90
uv run python -m rppg_core.signals.analyze_rgb artifacts/green-demo/rgb_synthetic.csv \
  --output artifacts/green-demo/analysis
```

Gera estimativas ou abstenções em JSON e diagnóstico PNG. A demonstração é
artificial, sem rosto ou fisiologia real. Veja [especificação e uso](docs/architecture/green-dsp.md).
