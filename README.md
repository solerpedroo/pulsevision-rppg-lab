# PulseVision — rPPG Lab

Laboratório experimental para estimar frequência cardíaca por variações de cor
facial, com resultados rastreáveis e abstenção quando o sinal for insuficiente.
**Uso experimental; não é dispositivo médico.**

## Estado

Ondas 0–1: fundação e ingestão temporal de vídeo. Ainda não há câmera, upload,
algoritmos rPPG ou resultados de BPM.
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
