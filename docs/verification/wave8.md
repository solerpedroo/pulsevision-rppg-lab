# Verificação da Onda 8 — 2026-11-08

História verificada: seleção de vídeo no Video Lab → upload autorizado → job da
API → subprocesso de visão/DSP → revisão de resultados → exportação → exclusão.

- Navegador: Chromium, layout desktop e 390×844; preview local H.264, consentimento,
  selects, scrubber, estados e downloads operacionais. Sem exceções de página no
  fluxo real e sem overflow horizontal na verificação mobile.
- Cliente/API: POST binário retorna 202; método POS e ROI testa chegam ao resultado.
  Consultas de estado encerram o polling no terminal. Resultados e regiões paginados
  são consumidos pela UI, com BPM null e indicação de face ausente.
- Worker/dados: modelo local real em vídeo original sintético de cor constante,
  sem rosto ou pulso fisiológico. Testes Python verificam remoção de input/CSV,
  geometria vazia por timestamp e contornos de máscaras sintéticas via observer.
- Resposta/UI: janela e motivos preservados; seek modifica o vídeo; JSON é baixado
  com ação explícita. Reanálise CHROM cria outro job e revoga o antigo (404).
  DELETE revoga o novo job (404), remove preview e desmarca autorização.
- Adversidades de UI: arquivo inválido, origem externa recusada, API indisponível
  e reconexão. Cancelamento/falha usam respostas simuladas declaradas no teste;
  cancelamento do subprocesso real permanece coberto na suíte Python da API.
- Gráficos: testes de lacunas entre amostras isoladas, ausência sem curva fabricada,
  escala constante finita e eixos/unidades. Não houve gráfico de BPM humano.
- Operação: testes iniciam/encerram API e Next localmente, sem deploy. CI configurada,
  sem execução remota nesta sessão. Build de produção passou após E2E.

Resultados: 224 testes Python, 10 Vitest e 3 Playwright passaram; Ruff, mypy,
ESLint, TypeScript, build, formatação e diff sem whitespace inválido passaram.
Screenshots locais: `artifacts/wave8-desktop.png` e `artifacts/wave8-mobile.png`.
Artefatos são ignorados pelo Git; não representam dados clínicos ou dataset real.

Uma execução intermediária ficou processing além dos 45 s esperados pelo teste;
a causa não foi determinada e as execuções finais passaram. O timeout real do
job continua 180 s; esta verificação não estabelece SLA nem robustez sob carga.
Precisão fisiológica, inspeção positiva de ROIs em faces autorizadas e compatibilidade
de todos os codecs/timelines permanecem sem validação nesta onda.
