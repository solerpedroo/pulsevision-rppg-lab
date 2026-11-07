# Changelog

Mudanças relevantes são registradas aqui; não representa release publicada.

## Não lançado — Onda 2 — 2026-11-07

- PV-0201–PV-0209: Face Landmarker VIDEO/CPU integrado com rejeição de múltiplas faces.
- ROIs roi-v1, máscaras fotométricas e exclusões de olhos, boca e sobrancelhas.
- Extração RGB por região/união, flags de movimento, escala, brilho e tracking.
- CLI CSV com rejeições explícitas e metadados; sem gravação de frames.
- Download explícito de modelo oficial versionado com SHA256 e fontes de licença.
- Testes sintéticos de geometria e pipeline, smoke test local do detector real.
- Pendente validação visual em rostos autorizados; nenhuma precisão alegada.

## Não lançado — Onda 1 — 2026-11-07

- PV-0101–PV-0107: VideoReader sequencial com PyAV e RGB24.
- PTS preservados, timestamps relativos monotônicos e origem auditável.
- Metadados, rotação, gaps temporais e erros tipados sem fallback por FPS.
- CLI inspect_video com relatório JSON e diagnóstico de amostragem.
- Fixtures temporárias CFR/VFR para MP4/MOV MPEG-4 e WebM VP9.
- Testes de entradas inválidas, truncamento, orientação e integridade temporal.
- ADR 0003 e guia de aquisição; dependências PyAV/NumPy pinadas.

## 0.1.0 — 2026-11-07 — Onda 0

- Monorepo Python/TypeScript com ambientes e lockfiles reproduzíveis.
- Fundação Next.js, Tailwind, configuração shadcn, lint, tipos, formatação e testes.
- Contratos Pydantic com timestamps, abstenção e schemas/tipos TS gerados.
- CI de verificação e detecção de divergência dos contratos.
- Arquitetura híbrida, ADRs, privacidade, protocolo científico e licença MIT.
- Orientações AGENTS.md, Claude/Cursor e state.md para continuidade.
- Testes sintéticos de contratos; nenhuma inferência ou métrica real adicionada.
- Limitação conhecida: alertas moderados nas dependências de desenvolvimento
  ESLint, registrados em state.md.
