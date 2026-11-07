# Estado do projeto

Atualizado: 2026-11-07. Onda atual: 0 — fundação implementada e validada localmente.
Próxima onda: 1 — ingestão de vídeo e integridade temporal. Não iniciada.

## Contexto e retomada

Leia AGENTS.md, plano original, docs/architecture/overview.md e docs/adrs/.
A ideia é obter estimativas rPPG rastreáveis ou abstenção, começando pelo núcleo
offline e só depois API, interface e webcam local. Não há inferência nesta entrega.

## Onda 0 — critérios

- [x] PV-0001: monorepo com apps/web, packages, services/api, benchmarks e docs.
- [x] PV-0002: Python 3.12.15, uv.lock, Ruff, mypy e pytest.
- [x] PV-0003: Next.js 16.4.5, React, TypeScript, Tailwind 4, configuração shadcn,
      utilitário cn, ESLint, Prettier e Vitest. Componentes de produto ficam para Onda 8.
- [x] PV-0004: workflow de lint, tipos, contratos, testes, formatação e build.
- [x] PV-0005: arquitetura e ADR híbrido.
- [x] PV-0006: política de privacidade e especificação de retenção/exclusão futura.
- [x] PV-0007: amostra RGB, janela, estimativa, status e experimento;
      JSON Schema e declarações TS gerados.
- [x] PV-0008: protocolo metodológico v1; manifesto e thresholds finais pendentes
      até dataset autorizado e validação, antes de qualquer teste final.
- [x] PV-0009: MIT e política de datasets/modelos.
- [x] AGENTS.md, CLAUDE.md, regras Cursor, changelog e template de PR.

## Evidências locais

- uv sync: ambiente Python 3.12.15 criado, sem alterar Python 3.14 do sistema.
- uv run ruff check .: passou.
- uv run mypy: passou em quatro arquivos fonte.
- uv run pytest: 9 testes passaram.
- npm run contracts: quatro contratos gerados.
- npm run lint e npm run typecheck: passaram.
- npm test: 2 testes passaram, com fixture sintética compartilhada.
- NEXT_TELEMETRY_DISABLED=1 npm run build: passou; / e /_not-found estáticos.
- npm audit --omit=dev --audit-level=moderate: zero vulnerabilidades.
- CI foi configurada, mas não executada no GitHub nesta sessão.
- Revisão React: componentes server, sem efeitos/captura, html pt-BR, landmark
  main e título semântico; sem dependência de fontes ou serviços externos no build.

## Limitações e decisões abertas

- npm audit completo: oito alertas moderados transitivos via minimatch na cadeia
  typescript-eslint/eslint-config-next (GHSA-g3hv-75wg-m249). Não aplicar downgrade
  major sugerido automaticamente. Reavaliar atualização compatível do fornecedor.
- skipLibCheck segue configuração comum do Next: há incompatibilidade de tipos
  URLPattern entre declarações de dependências; código próprio continua strict.
- Política de retenção é requisito futuro, não mecanismo implementado.
- Schemas não exprimem validadores relacionais Pydantic; TS deve validá-los na
  futura integração. Métodos usam nomes GREEN/CHROM/POS, snake_case nos contratos.
- Não há API, câmera, upload, modelos, dados reais ou validação de precisão.
- Não houve commit, push, publicação ou modificação do plano original.

## Próxima ação — Onda 1

PV-0101–PV-0107: selecionar decoder com PTS (preferência PyAV), piná-lo e testar
no Fedora; implementar FrameSample e erros tipados; gerar fixtures CFR/VFR
sintéticas em execução, sem versionar vídeos privados; criar CLI inspect_video.
Verificar FFmpeg/codecs presentes antes de declarar suporte MP4/WebM/MOV.
