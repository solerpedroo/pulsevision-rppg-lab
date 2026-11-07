# PulseVision — orientações para agentes

Leia nesta ordem: este arquivo, state.md, o plano original e os ADRs pertinentes.
O plano de referência é 09_pulsevision_rppg_implementation_plan.md.
Trabalhe uma onda por vez; a primeira é a Onda 0. Não antecipe inferência ou UI de produto.
Atualize state.md e CHANGELOG.md ao encerrar uma alteração significativa.
Registre decisões duráveis em docs/adrs/ com contexto, decisão e consequências.

## Arquitetura e limites

- packages/rppg_core: ciência independente de HTTP e React.
- packages/rppg_types: contratos Pydantic, JSON Schema e tipos TS gerados.
- apps/web: Next.js; câmera futura processa localmente, sem transmissão padrão.
- services/api: reservado para FastAPI na Onda 7; não iniciar servidor fictício.
- benchmarks: protocolo, configurações, adapters e avaliação reproduzível.
- Nunca invente BPM, métricas, ground truth, downloads ou validação clínica.
- BPM ausente é resultado legítimo; sempre preserve causa, janela e tempo.
- Use timestamps reais; não substitua PTS por índice de frame silenciosamente.
- Não versionar rostos, vídeos pessoais, credenciais, datasets ou modelos restritos.
- Não implementar diagnósticos, faixas clínicas, SpO2 ou identificação facial.

## Fluxo e validação

1. Verifique git status e preserve alterações do usuário.
2. Associe o trabalho a PV-XXXX do plano; declare escopo e dependências.
3. Implemente e teste contratos, casos inválidos e comportamento observável.
4. Rode uv run ruff check ., uv run mypy e uv run pytest.
5. Rode npm run lint, npm run typecheck, npm test e npm run build.
6. Ao alterar modelos: exporte schemas e gere tipos; não edite arquivos gerados.
7. Registre comandos, resultados reais e pendências no estado.
8. Não publique nem envie mensagens a terceiros sem instrução explícita.

Regras do Cursor e CLAUDE.md apontam para este arquivo para evitar divergência.
