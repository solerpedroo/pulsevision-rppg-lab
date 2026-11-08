# Changelog

Mudanças relevantes são registradas aqui; não representa release publicada.

## Não lançado — Onda 7 — 2026-11-07

- PV-0701–PV-0710: FastAPI/OpenAPI local com upload binário em streaming e fila limitada.
- Subprocessos supervisionados com limites, cancelamento e encerramento com o pai.
- SQLite de metadados, restart, expiração e exclusão completa por job.
- Estimativas/séries paginadas e exportação JSON/CSV/PNG com hashes/configurações.
- Bloqueios de host/origin, chave opcional, rate limit e ausência de cache.
- Testes de HTTP real e cenários adversos; CI busca modelo oficial pinado por hash.
- Privacidade v2 e ADR 0009; sem interface de vídeo ou validação fisiológica.

## Não lançado — Onda 6 (infraestrutura) — 2026-11-07

- Adapters UBFC e referência PURE/CSV com timestamps explícitos e validação estrita.
- Manifesto por participante/sessão, controle de acesso declarado e lock de hashes.
- Runner GREEN/CHROM/POS com referência nas mesmas janelas e exclusões separadas.
- Métricas por participante, agregação macro, coverage e bootstrap por participante.
- JSON/CSV/Markdown e figuras de dispersão, Bland–Altman descritivo, erro e cobertura.
- Testes/demonstração artificiais; rota de vídeo remove CSV intermediário.
- Pendente avaliação real PV-0610 e confirmação dos adapters em distribuição autorizada.
- Nenhum dataset pessoal/biométrico baixado ou resultado fisiológico alegado.

## Não lançado — Onda 5 — 2026-11-07

- PV-0501–PV-0508: SignalQualityService com evidências faciais, fotométricas,
  temporais e espectrais, sem score de confiança clínica.
- Configuração quality-v1, catálogo de motivos e auditoria QualityAssessment.
- CSV preserva estatísticas e causas específicas; flags desconhecidas são rejeitadas.
- Confirmação de mudanças/recuperação entre janelas e supressão de resultados vencidos.
- Cobertura e contagem de abstenções/status/motivos nos exports e helper reutilizável.
- Testes adversos sintéticos e de integração; contratos/schemas/TS atualizados.
- ADR 0007 e política de avaliação; sem benchmark fisiológico nesta onda.

## Não lançado — Onda 4 — 2026-11-07

- PV-0401–PV-0408: CHROM/POS com janelas internas, overlap-add e suporte explícito.
- Registry imutável e configuração classical-v1; engine compartilhado preserva GREEN.
- CLI para método individual ou comparação com janela, ROI e margem temporal comuns.
- Exportação de sinais, PSD e BPM temporal, com abstenções e contagens por método.
- Referência pyVHR fixada por commit e fixture sintética de regressão offline.
- Documentadas diferenças de filtragem, arredondamento, bordas e licenças upstream.
- Sem benchmark em pessoas ou implementação causal/live.

## Não lançado — Onda 3 — 2026-11-07

- PV-0301–PV-0308: validação temporal, reamostragem limitada e janelamento offline.
- GREEN com normalização/detrending, Butterworth SOS não causal e Welch.
- BPM opcional e motivos de abstenção, sem reutilizar resultados anteriores.
- Metadata opcional de processamento em EstimateResult; schemas/TS regenerados.
- Gerador determinístico RGB artificial e CLI de análise CSV → JSON/PNG.
- Gates iniciais de energia/concentração, ambiguidade, validade e Nyquist.
- Testes de frequência, harmônicos, ruído, lacunas, NaNs e integração dos exports.
- Sem validação em pessoas, equivalência live ou alegações de precisão clínica.

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
