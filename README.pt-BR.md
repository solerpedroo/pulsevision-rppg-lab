# PulseVision — rPPG Lab

[English](README.md) · [Instalação atualizada](docs/release/linux.md) · [v1.0.0](docs/release/v1.0.0.md)

Onda 11 prepara a versão 1.0.0 local: polish, segurança, containers e apresentação.
Não houve publicação ou validação fisiológica; as pendências científicas continuam.

Laboratório experimental para estimar frequência cardíaca por variações de cor
facial, com resultados rastreáveis e abstenção quando o sinal for insuficiente.
**Uso experimental; não é dispositivo médico.**

## Estado

Ondas 0–5 e 7–9 implementadas; infraestrutura das Ondas 6/10 e Benchmark Lab disponíveis.
Onda 11 de engenharia preparada localmente; detalhes e limites no dossiê da versão.
Avaliação em UBFC/PURE real pendente: ainda não há dataset autorizado local. O Video Lab permite uploads explícitos; o Live Lab processa webcam localmente no navegador.
Não há validação em pessoas. Os métodos clássicos estimam periodicidade em traces RGB.
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

Abra http://localhost:3000. A API é iniciada separadamente pelo comando da seção Onda 7.
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
packages/rppg_types os contratos; services/api a API local com jobs;
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

## Comparar GREEN, CHROM e POS

```bash
uv run python -m rppg_core.signals.analyze_rgb artifacts/green-demo/rgb_synthetic.csv \
  --method all --method-config configs/methods/classical-v1.json \
  --output artifacts/classical-comparison
```

JSON e PNG com suporte temporal comum, sinais, PSD e BPM por janela.
Referências numéricas e limites em
[docs/architecture/classical-methods.md](docs/architecture/classical-methods.md).

## Qualidade, abstenção e cobertura

```bash
uv run python -m rppg_core.signals.analyze_rgb artifacts/sessao/rgb_traces.csv \
  --method all --quality-config configs/quality/quality-v1.json \
  --output artifacts/sessao/quality
```

Relatórios preservam causas de rejeição, confirmação entre janelas e cobertura.
O helper de exibição suprime estimativas vencidas, sem carregar BPM anterior.
Veja [contrato e uso](docs/architecture/signal-quality.md) e
[política experimental](docs/evaluation/quality-policy-v1.md).

## Benchmark e referência temporal

```bash
uv run python -m benchmarks.runners.synthetic --output artifacts/benchmark-demo/inputs
uv run python -m benchmarks.runners.run freeze artifacts/benchmark-demo/inputs/manifest.json \
  --output artifacts/benchmark-demo/lock.json
uv run python -m benchmarks.runners.run run artifacts/benchmark-demo/inputs/manifest.json \
  --lock artifacts/benchmark-demo/lock.json --output artifacts/benchmark-demo/results
```

Essa demonstração é artificial. O runner gera métricas por participante, exclusões,
coverage e gráficos, e recusa configuração alterada ou alinhamento não verificado.
Veja [protocolo operacional](docs/evaluation/benchmark-v1.md) e
[acesso aos datasets](docs/research/dataset-access.md).

## API local de vídeo (Onda 7)

```bash
uv run python scripts/fetch_face_model.py
uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

Upload binário, jobs assíncronos, progresso, cancelamento, séries paginadas,
exportação e exclusão. Originais são removidos no término; derivados expiram em 24 h.
Veja [contrato e setup](docs/architecture/video-api.md) e
[política de privacidade](docs/privacy/policy.md). A interface está disponível em `/video`; veja [uso do Video Lab](docs/architecture/video-lab.md).

## Webcam local (Onda 9)

```bash
npm run live:assets
npm run dev -w apps/web
```

Abra http://localhost:3000/live. Requer o modelo local já verificado pelo script
acima. A câmera começa por ação explícita; frames não são enviados ao backend.
GREEN/POS/CHROM analisam janela passada de 20 s com qualidade e abstenção.
Stop libera tracks, encerra worker e descarta séries. Exporte derivados antes de parar.
Veja [operação e limites do Live Lab](docs/architecture/live-lab.md).

## Benchmark Lab e estudos offline (Onda 10)

```bash
uv run python -m benchmarks.study demo --output artifacts/study-demo
npm run dev -w apps/web
```

Abra http://localhost:3000/benchmark e selecione o JSON em
`artifacts/study-demo/results/review/benchmark-review-v1.json`.
Demonstração artificial de janelas 10/20/30 s, sem validação em pessoas.
A revisão é local, sem upload. Estudos congelados geram JSON/Markdown/PNG;
[guia do Benchmark Lab](docs/architecture/benchmark-lab.md).
Experimentos A–E reais e relatório científico final aguardam dados autorizados.
