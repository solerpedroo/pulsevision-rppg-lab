# Estado do projeto

Atualizado: 2026-11-07. Onda atual: 5 — qualidade instrumental, abstenção e continuidade implementadas.
Próxima onda: 6 — datasets autorizados, ground truth e benchmark científico. Não iniciada.
Validação visual de ROIs em rostos autorizados continua pendente.

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
- Não há API, câmera, upload, dados reais ou validação de precisão. Modelo oficial
  local disponível desde a Onda 2, fora do Git.
- Não houve commit, push, publicação ou modificação do plano original.

## Histórico — preparação da Onda 1

PV-0101–PV-0107: selecionar decoder com PTS (preferência PyAV), piná-lo e testar
no Fedora; implementar FrameSample e erros tipados; gerar fixtures CFR/VFR
sintéticas em execução, sem versionar vídeos privados; criar CLI inspect_video.
Verificar FFmpeg/codecs presentes antes de declarar suporte MP4/WebM/MOV.

## Onda 1 — critérios e implementação

- [x] PV-0101: VideoReader com PyAV 19.0.2; MP4/MOV MPEG-4 e WebM VP9 testados.
- [x] PV-0102: codec, duração, resolução, rotação, FPS informado, base e origem.
- [x] PV-0103: decode por PTS, VFR preservado; imagens idênticas não são removidas.
- [x] PV-0104: FrameSample com RGB24, timestamp relativo estritamente crescente,
      PTS/base racional e timestamp original preservados.
- [x] PV-0105: erros tipados para abertura, stream/decoder, decode e timestamps.
- [x] PV-0106: fixtures sintéticas temporárias CFR/VFR, cor constante e rotação.
- [x] PV-0107: testes de intervalos, contagem, origem, orientação, truncamento e CLI.
- CLI: uv run python -m rppg_core.acquisition.inspect_video <arquivo>.
- ADR 0003 e docs/architecture/acquisition.md descrevem contratos e limitações.
- Nenhuma implementação de algoritmos rPPG ou detecção facial antecipada.

## Evidências da Onda 1

- uv sync/lock: PyAV 19.0.2 e NumPy 2.5.4 pinados.
- O sistema não possui comando ffmpeg; wheel PyAV disponibiliza bibliotecas
  libavcodec/libavformat 63.1.102. Não houve instalação de pacotes do sistema.
- uv run ruff check .: passou.
- uv run mypy: passou em oito arquivos fonte.
- uv run pytest: 33 testes passaram (24 aquisição e 9 contratos).
- npm run lint, npm run typecheck, npm test: passaram (2 testes web).
- NEXT_TELEMETRY_DISABLED=1 npm run build: passou.
- npm run format:check e git diff --check: passaram.
- CI continua configurada; não executada remotamente nesta sessão.

## Limites específicos da aquisição

A integridade completa só é verificada ao consumir todo o gerador. Feche-o
explicitamente se interromper cedo. Descarte resultados parciais após erro.
Não há garantia de detectar todo truncamento quando o container não declara
contagem e o decoder encerra sem erro. Gaps usam FPS informado como heurística;
não são prova de frames perdidos. Pixels mantêm orientação codificada; rotação
deve ser aplicada de forma coerente com ROIs na próxima onda. Não há seek.
Relatório CLI acumula timeline de metadados; reader não acumula pixels.

## Histórico — preparação da Onda 2

PV-0201–PV-0209: integrar Face Landmarker Python com modelo cuja licença seja
verificada, definir ROIs e máscaras com orientação explícita, extrair médias RGB
e qualidade por região, tratar ausência/múltiplas faces e testar geometria/BGR-RGB.
Modelo não deve ser versionado sem autorização de redistribuição.

## Onda 2 — critérios e implementação

- [x] PV-0201: MediaPipe 1.2.2 VIDEO em CPU integrado.
- [x] PV-0202: single_face_only=True obrigatório; detector retorna até duas faces
      para rejeitar múltiplas detecções.
- [x] PV-0203: polígonos roi-v1 de testa e bochechas por landmarks.
- [x] PV-0204: máscaras, redução de bordas e exclusão geométrica de olhos,
      sobrancelhas e boca; cabelo/oclusores sem segmentação semântica.
- [x] PV-0205: médias RGB e estatísticas por ROI; combined ponderado por pixels.
- [x] PV-0206: flags de brilho, saturação, pixels válidos, movimento e escala.
- [x] PV-0207: ausência/múltiplas faces, perda de tracking e lacunas sem RGB falso.
- [x] PV-0208: CLI CSV e metadados, sem salvar frames ou previews.
- [x] PV-0209: testes de geometria, máscaras, orientação, BGR/RGB e pipeline.
- [ ] Inspecionar geometria em rostos autorizados e condições variadas antes de
      alegar robustez real. Não há material de rosto autorizado nesta sessão.

## Evidências da Onda 2

- uv sync --locked: passou, com MediaPipe 1.2.2/OpenCV contrib 5.0.0.93 pinados.
- Modelo oficial float16/1 baixado em models/, SHA256 verificado por script.
  git check-ignore confirmou que pesos não serão versionados.
- uv run ruff check . e uv run mypy: passaram, 16 fontes tipadas.
- uv run pytest: 54 testes passaram localmente, incluindo modelo real sem rosto.
  Na CI sem pesos, o teste de smoke do modelo real é pulado; demais são offline.
- Testes positivos de landmarks/ROIs usam geometria sintética e detector injetado.
  Não são evidência de detecção positiva/precisão em rostos reais.
- Teste local real cobre imagem vazia, vídeo sintético sem face e exportação de
  rejeições, além de erro de colisão de timestamps em milissegundos.
- npm run lint, npm run typecheck, npm test e npm run build: passaram, 2 testes web.
- npm run format:check e git diff --check: passaram.
- Fontes/licenças e checksum em docs/research/face-model.md; ADR 0004 explica
  arquitetura, thresholds, privacidade e limites. CI não executada remotamente.

## Limitações da Onda 2

Geometria é heurística e não segmenta cabelos, mãos ou demais oclusores de forma
geral. Pode haver detecções persistentes/espúrias e troca de pessoa sem identificação.
Gates instrumentais iniciais não substituem qualidade temporal/espectral da Onda 5.
Bundle não é redistribuído. Sem auto-download na importação, CI ou inferência.
Não há preview com rosto nem medição de BPM. Metadados e CSV devem ser consumidos
como par; não há transação entre arquivos resistente a interrupção abrupta.

## Histórico — preparação da Onda 3

PV-0301–PV-0308: traços RGB → resampling com lacunas explícitas → normalização/
detrending → GREEN → filtro estável → Welch/FFT → BPM ou abstenção.
Usar sinais sintéticos com frequência conhecida e tolerância ligada à resolução
temporal; rejeitar sinais constantes, NaNs, dados curtos e timestamps inválidos.
Não apresentar esses testes como validação clínica ou avaliação em dataset real.

## Onda 3 — critérios e implementação

- [x] PV-0301: cadência mediana, reamostragem linear quando necessária e limite
      explícito de gaps, sem extrapolar nem apagar amostras inválidas.
- [x] PV-0302: normalização G/mean(G)-1, detrend linear e janelas 20 s/stride 1 s.
- [x] PV-0303: Butterworth SOS ordem 4, 0,7–3 Hz e sosfiltfilt offline.
- [x] PV-0304: Welch com Hann, bins sem zero-padding e pico → BPM.
- [x] PV-0305: método GREEN independente de HTTP e componentes web.
- [x] PV-0306: gerador sintético com seed, frequência, ruído e harmônicos.
- [x] PV-0307: frequências, ruído, harmônicos, constantes, trend, NaNs, lacunas,
      Nyquist, timestamps e limites de janela testados.
- [x] PV-0308: EstimateResult com BPM opcional e metadata de DSP;
      JSON Schema e tipos TS regenerados de forma aditiva.
- Exportação: CSV da Onda 2 → estimativas JSON e diagnóstico PNG.
- ADR 0005 e docs/architecture/green-dsp.md registram parâmetros e limites.
- Nenhum método CHROM/POS, API ou DSP live antecipado.

## Evidências da Onda 3

- uv sync --locked: SciPy 1.18.1 pinado; scipy-stubs para tipagem.
- uv run ruff check . e uv run mypy: passaram (26 arquivos fonte).
- uv run pytest: 98 testes passaram localmente, 44 de GREEN/DSP.
- npm run lint, npm run typecheck e npm test: passaram (2 testes web).
- NEXT_TELEMETRY_DISABLED=1 npm run build: passou.
- Schemas exportados e npm run contracts executado.
- npm run format:check e git diff --check: passaram.
- Demo artificial de 90 BPM: artifacts/wave3-demo/rgb_synthetic.csv e
  artifacts/wave3-demo/analysis/{estimates.json,green_diagnostics.png}.
  11 janelas aceitas; PNG inspecionado, rotulado artificial e com eixos/unidades.
  Artefatos locais ignorados pelo Git; não são medidas reais.
- CI configurada, sem execução remota nesta sessão.

## Limites específicos do GREEN

sosfiltfilt não é causal. Corte de bordas de 1 s é heurístico; PSD utiliza
somente interior. Para 20 s, segmento útil ~18 s → bins ~3,33 BPM, sem alegar
essa resolução como precisão. Welch pode usar só um segmento nessa configuração.
Picos de iluminação e harmônicos dominantes ainda podem produzir estimativas
plausíveis. Gates iniciais não são mecanismo completo de qualidade da Onda 5.
Sem ground truth fisiológico, benchmark, validação em pessoas ou calibração clínica.
Janelas rejeitadas preservam BPM null e motivo; não há carry-forward.
Erro estrutural de timestamps/shape gera SignalInputError, em vez de inventar
janela. Contagens/cobertura do trace não equivalem a métricas de acurácia.

## Histórico — preparação da Onda 4

PV-0401–PV-0408: CHROM e POS com normalização/projeções e composição temporal
especificadas; registry, parâmetros versionados e comparação justa com GREEN.
Consultar publicações e implementações primárias; validar mesma entrada/tempos,
bordas e filtragem. Documentar diferenças e criar regressões numéricas.

## Onda 4 — critérios e implementação

- [x] PV-0401: CHROM com normalização local, projeções, filtragem pré-alpha e Hann/OLA.
- [x] PV-0402: POS com projeções, normalização e overlap-add por amostra.
- [x] PV-0403: registry imutável e MethodConfig classical-v1 versionada em JSON.
- [x] PV-0404: comparação com mesmas entradas, ROI, janelas, banda, Welch e margem útil.
- [x] PV-0405: comparação JSON/PNG com sinais, PSD e BPM ao longo do tempo.
- [x] PV-0406: regressão com funções pyVHR em commit fixado, nos mesmos dados/
      parâmetros. CHROM: projeção com harness de pré-processamento/composição alinhado;
      POS: composição no interior comum. Não é equivalência de pipelines completos.
- [x] PV-0407: diferenças de filtros, arredondamento e bordas em ADR 0006.
- [x] PV-0408: regressão numérica GREEN/CHROM/POS e testes adicionais.
- Engine generalizado em estimation/pipeline.py; import green_pipeline compatível.
- CLI --method GREEN/CHROM/POS/all e --method-config.
- Fontes, licença upstream e reprodução em docs/research/classical-references.md.

## Evidências da Onda 4

- uv run ruff check . e uv run mypy: passaram (34 arquivos fonte).
- uv run pytest: 127 testes passaram localmente (29 novos).
- npm run lint, npm run typecheck, npm test e npm run build: passaram (2 testes web).
- npm run format:check e git diff --check: passaram.
- Fixture numérica gerada executando cpu_CHROM/cpu_POS do pyVHR, commit
  a6270f04a97f05a13d145dd0a5e8c8df48d8bd62. URL/SHA256/versões registrados;
  testes normais rodam offline, sem instalar pyVHR ou dependências GPU.
- Diferença máxima no interior: CHROM ~5,3e-15 e POS ~6,5e-15; tolerância
  automatizada atol=1e-11/rtol=1e-9. GREEN usa detrend independente via polyfit.
- Demo artificial de 90 BPM: 11 janelas aceitas por método e timestamps úteis
  idênticos. artifacts/wave4-demo/comparison-reviewed/{comparison.json,comparison.png}.
  PNG inspecionado e rótulos de amplitude encurtados para legibilidade.
  Artefatos ignorados pelo Git; não são medições em pessoas.
- CI não executada remotamente; não houve commit/push/publicação.

## Limites específicos dos métodos clássicos

CHROM filtra componentes antes da combinação; POS/GREEN filtram saída.
A configuração comum não transforma essas diferenças algorítmicas em operações
idênticas. Escalas de sinal/PSD são distintas e não medem qualidade diretamente.
Análise individual pode usar margens diferentes; usar --method all para comparação.
pyVHR usa floor em POS e omite primeira janela; local usa ceil e inclui a primeira.
Equivalência da fixture POS é limitada ao interior de um caso a 30 Hz.
Projeções degeneradas produzem abstenção/erro de qualidade explícito.
Não há avaliação em pessoas, ground truth sincronizado, comparação causal/live
ou conclusão sobre superioridade de método. Pendência visual de ROIs permanece.

## Histórico — preparação da Onda 5

PV-0501–PV-0508: centralizar indicadores instrumentais e reason codes;
incorporar qualidade temporal/espectral, validade ROI e estabilidade consecutiva;
definir abstenção, obsolescência e cobertura. Testar movimento, iluminação,
FPS irregular, ruído e saturação; thresholds continuam heurísticos, não clínicos.

## Onda 5 — critérios e implementação

- [x] PV-0501: evidências de face/ROI e métricas opcionais preservadas pelo CSV.
- [x] PV-0502: gates de movimento, iluminação, cobertura temporal, irregularidade,
      energia em banda e estrutura do pico centralizados em SignalQualityService.
- [x] PV-0503: catálogo ReasonCode, estados e QualityAssessment por resultado.
- [x] PV-0504: configs/quality/quality-v1.json com thresholds heurísticos versionados;
      parâmetros de pico herdados continuam em SignalConfig por compatibilidade.
- [x] PV-0505: confirmação entre janelas após salto/recuperação, sem suavização.
- [x] PV-0506: display_estimate suprime resultado vencido e retorna cópia datada.
- [x] PV-0507: testes de adversidades, fonte CSV, continuidade e vencimento.
- [x] PV-0508: summarize_quality conta aceitas, abstenções, cobertura, status e
      motivos; integrado aos exports e reutilizável pelo futuro runner de benchmark.
- O runner/dataset com referência ainda pertence à Onda 6; nenhuma execução
  fisiológica ou métrica de erro é alegada nesta entrega.
- ADR 0007, contrato de uso e política experimental de avaliação adicionados.
- EstimateResult.quality é opcional e aditivo; Pydantic valida concordância
  entre passed e disponibilidade de BPM. Schemas/TS regenerados.

## Evidências da Onda 5

- uv run ruff check . e uv run mypy: passaram (40 arquivos fonte).
- uv run pytest: 174 testes passaram localmente; 47 novos testes de qualidade.
- npm run lint, npm run typecheck, npm test e npm run build: passaram (2 testes web).
- Exportação de schemas e npm run contracts executados.
- npm run format:check e git diff --check: passaram.
- Demo artificial: artifacts/wave5-demo/rgb_synthetic_quality.csv, com 45 s de
  pulso RGB sintético e evento de movimento simulado em [20,20.2) s.
  Relatório/PNG em artifacts/wave5-demo/comparison-reviewed/.
  Por método: 26 janelas, 5 aceitas, 20 rejeições por movimento e 1 recuperação;
  coverage=5/26. Gráfico preserva lacunas; não interpola BPM durante rejeição.
  Inspeção visual motivou escala de BPM sem offset científico em sinais constantes.
- Artefatos e indicadores dessa demo são artificiais e ignorados pelo Git.
- CI não executada remotamente. Sem commit, push ou publicação.

## Limites específicos de qualidade

Gates são instrumentais iniciais e não representam confiança clínica calibrada.
Uma amostra rejeitada bloqueia toda a janela, reduzindo cobertura. Confirmação
pode suprimir mudanças fisiológicas reais; janelas sobrepostas não são independentes.
Energia do G antes do filtro pode rejeitar dados que CHROM/POS recuperariam.
Média RGB é proxy de brilho quando faltam estatísticas; não prova qualidade
facial/presença de pele. Ausência de evidência fica registrada em warnings.
Flicker/movimento periódicos de baixa amplitude ainda podem gerar BPM plausível.
display_estimate usa tempo da sessão e o resultado mais recente, inclusive ruim;
não procurar o último resultado bom. analyze_window é stateless; analyze_trace
coordena continuidade. max_history_gap_s deve ser >= stride_s.
Elegibilidade das estatísticas atuais é o agendamento do trace; critérios prévios
de exclusão de dataset/ground truth serão definidos no runner da Onda 6.
Pendência de inspeção visual das ROIs em rostos autorizados continua aberta.

## Próxima ação — Onda 6

PV-0601–PV-0612: verificar acesso/licença de UBFC-rPPG e, se autorizado, PURE;
adapters de vídeo/referência com alinhamento temporal verificável; split por
participante, manifesto/protocolo congelados antes do teste final.
Implementar métricas MAE/RMSE/MedAE/bias/correlação, cobertura e exclusões,
agregação por participante e relatórios reproduzíveis. Não inventar dados,
autorizações, alinhamento ou resultados se o dataset ainda não estiver disponível.
