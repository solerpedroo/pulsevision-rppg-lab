# Estado do projeto

Atualizado: 2026-11-08. Onda atual: 10 — Benchmark Lab/estudos/relatórios implementados; avaliação real pendente.
Próxima onda de engenharia: 11 — polish e apresentação, preservando pendências científicas das Ondas 6/10.
Pendência científica da Onda 6: obter dataset autorizado e executar avaliação congelada.
Validação visual de ROIs em rostos autorizados continua pendente.

## Contexto e retomada

Leia AGENTS.md, plano original, docs/architecture/overview.md e docs/adrs/.
A ideia é obter estimativas rPPG rastreáveis ou abstenção. Aquisição, ROIs/RGB,
GREEN/CHROM/POS, qualidade, API local e Video Lab estão implementados. A UI permite
preview local, upload autorizado, inspeção e exportação. O Live Lab processa webcam
localmente em worker, mediante início explícito. O Benchmark Lab importa revisões
offline localmente e mostra erros/cobertura com proveniência. Não há
validação fisiológica em pessoas nem dataset autorizado local.

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
- Retenção/exclusão inicialmente planejadas foram implementadas na Onda 7;
  UI de descarte e autorização foi integrada na Onda 8.
- Schemas não exprimem validadores relacionais Pydantic; TS deve validá-los na
  futura integração. Métodos usam nomes GREEN/CHROM/POS, snake_case nos contratos.
- API/upload disponíveis desde a Onda 7 e UI de vídeo desde a Onda 8; webcam local disponível desde a Onda 9.
  Não há dados reais ou validação de precisão. Modelo oficial local fora do Git.
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

## Histórico — preparação da Onda 6

PV-0601–PV-0612: verificar acesso/licença de UBFC-rPPG e, se autorizado, PURE;
adapters de vídeo/referência com alinhamento temporal verificável; split por
participante, manifesto/protocolo congelados antes do teste final.
Implementar métricas MAE/RMSE/MedAE/bias/correlação, cobertura e exclusões,
agregação por participante e relatórios reproduzíveis. Não inventar dados,
autorizações, alinhamento ou resultados se o dataset ainda não estiver disponível.

## Onda 6 — infraestrutura entregue, conclusão científica pendente

O usuário confirmou que não possui dataset autorizado. Nenhum UBFC/PURE foi
baixado, nenhum contato externo foi feito e nenhum resultado em pessoas foi produzido.
A definição científica de pronto da Onda 6 ainda não foi atingida.

- [x] PV-0601: fontes oficiais e procedimento de acesso consultados; distribuição/
      termos completos e registro de acesso real ainda pendentes.
- [x] PV-0602: discovery UBFC e parser PPG/HR/timestamps implementados e testados
      em fixtures próprias. Formato ainda precisa ser conferido em dados recebidos.
- [x] PV-0603: parser de referência PURE preparado e acesso acadêmico documentado.
      Imagens PURE e sua sincronização end-to-end não validadas nesta entrega.
- [x] PV-0604: manifesto por participante/sessão/condição; split sem vazamento,
      configuração estrita e freeze verificável por hashes.
- [x] PV-0605: transformação temporal explícita e evidência externa obrigatória;
      alinhamento não verificado exclui sessão sem fabricar métricas.
- [x] PV-0606: referência é HR do sensor ponderada no mesmo interior útil
      espectral dos métodos, independente de aceitação; gaps/bordas inválidos excluem janela.
- [x] PV-0607: MAE/RMSE/MedAE/bias/Pearson, cobertura e tempos computacionais.
- [x] PV-0608: figuras de dispersão, Bland–Altman descritivo, distribuição por
      participante e cobertura; métricas por método/participante/condição.
- [x] PV-0609: agregação igual por participante e bootstrap de participantes,
      com seed/replicações e CI indisponível quando amostra insuficiente.
- [ ] PV-0610 científico: executar GREEN/CHROM/POS em dataset autorizado e
      referência temporal verificada. Demo sintética não substitui esse experimento.
- [ ] PV-0611 científico: investigar falhas em dados reais. Infraestrutura de
      exclusões/abstenções e testes de falhas já disponível.
- [x] PV-0612: dados privados/restritos ausentes do Git; evidências exportadas
      apenas por hash; CSV intermediário do fluxo de vídeo é removido.
- ADR 0008, protocolo operacional, definição das métricas e registro de acesso
  documentam escopo, parâmetros e limitações.

## Evidências da infraestrutura da Onda 6

- uv sync --locked: passou; pacote benchmarks incluído no workspace/checagem de tipos.
- uv run ruff check . e uv run mypy: passaram (53 arquivos fonte).
- uv run pytest: 198 testes passaram localmente, incluindo 24 novos de benchmark.
- Testes específicos de benchmark repetidos após revisão do relatório: 24 passaram.
- npm run lint, npm run typecheck, npm test e npm run build: passaram (2 testes web).
- npm run format:check e git diff --check: passaram.
- Testes cobrem fórmulas de erro, split, hashes alterados, gaps de referência,
  alinhamento recusado, macro por participante, bootstrap, exclusões e reexecução.
- Fluxo AVI CFR sintético → modelo local real → RGB → benchmark sem face executado;
  referência artificial não gera erro de BPM quando o estimador se abstém.
  Em CI sem modelo, esse smoke test é pulado. Nenhuma avaliação em rosto real.
- Gerador AVI de testes usa base CFR correta; decoder mantém recusa estrita de
  contagem divergente, sem enfraquecer integridade temporal.
- Demo local em artifacts/wave6-final-demo/inputs; lock final lock-delivery.json;
  saída results-delivery/{benchmark-v1.json,benchmark-v1.md,windows.csv,participants.csv,figures/}.
  São quatro participantes artificiais, 16 janelas por método, 14 aceitas e
  duas abstenções (movimento simulado e recuperação). Sem exclusões de referência
  nessa demo. Figuras dos três métodos inspecionadas e rotuladas artificiais.
- Locks anteriores do desenvolvimento ficam distintos; não reutilizá-los depois
  de alterações no código. Isso é comportamento esperado, não avaliação final.
- CI não executada remotamente. Sem commit/push/publicação.

## Limitações e próximos passos

Dataset/licença e evidência física de alinhamento dependem de obtenção legítima.
access_confirmed/verified são declarações registradas, não autenticação jurídica
ou descoberta automática de offset. Não retunar parâmetros pelo erro no teste.
HR do sensor pode ser suavizada/defasada; regra e origem precisam de validação.
LoA por janela são descritivos com medidas repetidas; CI reamostra participantes
com pares aceitos e não corrige ausência de dados ou baixa cobertura.
Macro-RMSE/MedAE são médias das métricas individuais, não versões pooled.
Participantes/sessões sem pares permanecem explícitos com métricas indisponíveis.
Pendência visual de ROIs em material autorizado continua aberta.

Para concluir a Onda 6 científica: obter UBFC-rPPG ou PURE pelos responsáveis,
conferir termos/formato/relógios, validar ROIs/referência em desenvolvimento,
fixar manifesto e protocolo e só então executar avaliação final.
A Onda 7 de engenharia pode avançar independentemente conforme dependências do
plano (1–5): FastAPI local, jobs, limites, cancelamento, exportação e limpeza.
Isso não encerra nem substitui a avaliação real pendente.

## Onda 7 — API local e jobs

- [x] PV-0701: FastAPI, healthcheck e OpenAPI de rotas/schemas.
- [x] PV-0702: streaming binário, limite real de bytes/tempo/slots, assinatura,
      família MIME/codec e caminho UUID gerado pelo servidor.
- [x] PV-0703: fila limitada e subprocesso separado por job, supervisionado
      fora do request; não usar BackgroundTasks para processamento científico.
- [x] PV-0704: queued/processing/completed/failed/cancelled/expired em SQLite.
- [x] PV-0705: cancelamento de processo ativo/pendente e isolamento por diretório.
- [x] PV-0706: status/progresso, estimativas paginadas e séries por janela com stride.
- [x] PV-0707: exports JSON/CSV/PNG, parâmetros, versões e hashes de entrada/modelo.
- [x] PV-0708: wall timeout, CPU time, memória virtual, duração, pixels, FPS,
      frames, tamanho de job/arquivo; host/origin/chave e rate limit.
- [x] PV-0709: retenção, startup/sweep, restart e DELETE com revogação de acesso.
- [x] PV-0710: integração com subprocesso real e uploads concorrentes/adversos.
- ADR 0009, guia de execução e política de privacidade v2 publicados no workspace.
- AGENTS/README atualizados: API ativa, DSP/decoder não executam nas rotas.

## Evidências da Onda 7

- uv sync --locked: passou; FastAPI 0.162.2, Uvicorn 0.54.0 e AnyIO 4.16.0 pinados.
  TestClient usa httpx2 compatível com Starlette instalado, sem aviso de depreciação.
- uv run ruff check . e uv run mypy: passaram (61 arquivos fonte).
- uv run pytest: 223 testes passaram localmente, 25 novos de API.
- npm run lint, npm run typecheck, npm test e npm run build: passaram (2 testes web).
- npm run format:check e git diff --check: passaram.
- HTTP real com Uvicorn em 127.0.0.1:8765: POST→202, health→200 durante job,
  completed, resultado sem BPM em vídeo sintético sem face, exports JSON/CSV/PNG→200,
  original ausente, DELETE→204 e GET posterior→404. Servidor encerrado após teste.
- Health medido em uma requisição: 1,77 ms (smoke, não benchmark de desempenho).
- Teste adicional suspendeu subprocesso ativo com SIGSTOP: health respondeu e
  cancelamento forçou encerramento/removendo artefatos, sem processo órfão.
- Upload desconectado/timeout, chunked acima do limite, MIME inválido, vídeo
  truncado, limite de memória, erro de spawn, TTL/restart/limpeza também testados.
- CI agora busca explicitamente o modelo oficial versionado e valida SHA256
  (cache com chave do hash), para executar integrações em vez de pular por falta
  de pesos. Nenhum vídeo/dataset humano baixado. CI não executada remotamente.
- Testes offline sem pesos ainda pulam integrações que exigem modelo.
- Sem commit/push/publicação. Evidência detalhada em docs/verification/wave7.md.

## Operação e limites atuais da API

Executar da raiz: uv run uvicorn services.api.app.main:app --host 127.0.0.1
--port 8000 --workers 1 --no-access-log. Modelo é configurado localmente; API não baixa pesos.
Uma instância por storage, Linux/Fedora; não é serviço público/multiusuário.
Limite de memória é RLIMIT_AS; não é sandbox completa ou quota global de disco.
Vídeos originais são removidos em estado terminal; derivados expiram em 24 h.
Serviço desligado não executa timer independente; startup limpa sobras de crash.
Cancel de job já concluído é recusado; para descartar resultados, usar DELETE.
É API de arquivos voluntários, sem captura nem streaming de webcam.
A avaliação científica real da Onda 6 e inspeção de ROIs em rostos autorizados
continuam pendentes e não foram substituídas pelos testes de API.

## Histórico — preparação da Onda 8

PV-0801–PV-0810: shell/navegação e Video Lab, consentimento/informação de destino
e retenção antes do envio, validação do arquivo, integração de job/cancel/delete,
timeline/gráficos/resultados e exportação explícita. Preservar BPM null e motivos.
Consumir body binário (não multipart), paginação/séries/índice de janela da API.
Adicionar fluxo E2E de vídeo e acessibilidade. Não implementar câmera antes da Onda 9.

## Onda 8 — Video Lab

Escopo PV-0801–PV-0810; depende da API local da Onda 7. Nenhuma funcionalidade
live/benchmark visual foi antecipada. A Onda 6 científica permanece pendente.

- [x] PV-0801: shell responsivo, navegação, tokens de tema, cards/controles e rota `/video`.
- [x] PV-0802: validação de extensão, bytes, duração/resolução no navegador e preview local.
- [x] PV-0803: autorização e destino explícitos, upload binário, polling, progresso,
      cancelamento/exclusão, erros e expiração; chave opcional só em memória.
- [x] PV-0804: gráficos SVG de RGB/rPPG/PSD/BPM e cobertura; null preserva lacunas.
- [x] PV-0805: observer de máscaras no núcleo, contornos por PTS no worker,
      série ROI paginada e overlay por frame/seek, com timeline de janelas.
- [x] PV-0806: método/ROI configuráveis; reanálise cria novo job e exclui o anterior.
- [x] PV-0807: downloads explícitos de CSV/JSON/PNG, sem exportação automática.
- [x] PV-0808: estados vazio, envio/fila/processamento, falha, cancelado, expirado,
      concluído sem face/sem estimativa e rejeições com motivos legíveis.
- [x] PV-0809: controles nativos, foco/skip link, seleção de janela, labels/unidades,
      status acessíveis e teste de teclado; layout mobile sem overflow horizontal.
- [x] PV-0810: E2E Chromium com API/worker/modelo reais e vídeo sintético sem rosto.
- ADR 0010, guia de operação e política de privacidade v3 registrados.
- Next dev gerou `apps/web/AGENTS.md` com orientações do framework; instruções
  da raiz continuam aplicáveis. Contratos científicos Pydantic não foram alterados.

## Evidências da Onda 8

- uv run ruff check .: passou.
- uv run mypy: passou (62 arquivos fonte).
- uv run pytest: 224 testes passaram, incluindo observer de máscaras e paginação
  real de contornos vazios, sem armazenar original/CSV após processamento.
- npm run lint e npm run typecheck: passaram.
- npm test: 10 testes passaram; validação de arquivo/destino, paginação completa,
  lookup temporal sem geometria obsoleta, erros, sessão expirada e gráficos com lacunas.
- npm run test:e2e: 3 testes passaram na execução final (11,2 s no ambiente local).
  Fluxo real: upload POS/testa → completed sem BPM → seek → JSON → reanálise CHROM
  → job antigo 404 → exclusão → novo job 404, preview removido e autorização desmarcada.
  Cenários simulados identificados: indisponibilidade de conexão, cancelamento/falha de UI.
  Uma execução intermediária excedeu o prazo de 45 s enquanto processing; a causa
  não foi determinada. As execuções estáveis subsequentes passaram; não é SLA de latência.
- NEXT_TELEMETRY_DISABLED=1 npm run build: passou; rotas `/`, `/_not-found` e `/video`.
- npm run format:check e git diff --check: passaram.
- Screenshots desktop/mobile inspecionados em artifacts/wave8-desktop.png e
  artifacts/wave8-mobile.png; sem overflow mobile ou exceções de página no fluxo real.
- Fixture H.264 original sem rosto, downloads e storage de E2E permanecem ignorados
  pelo Git. Servidores de teste foram encerrados pelo Playwright.
- CI inclui instalação do Chromium e E2E após build; não foi executada remotamente.
- Sem commit, push, publicação, envio a terceiros ou modificação do plano original.

## Limites atuais do Video Lab

É inspeção offline, com pipeline Python e backend local; nenhuma webcam ou DSP
live foi implementada. A aba não persiste arquivo/chave/job em localStorage;
recarregar perde a seleção, mas jobs aceitos continuam sujeitos ao TTL do servidor.
Excluir sessão limpa backend e preview local; downloads já feitos não são retraídos.
Contornos externos são simplificados e não representam todos os furos/pixels úteis;
qualidade do sinal pode ser ruim mesmo com contorno visível. Há fallback temporal
quando requestVideoFrameCallback não está disponível e supressão após gaps de 250 ms.
Timelines incomuns/edit lists e alinhamento visual em rostos autorizados ainda
precisam de verificação. Não houve inspeção positiva de face humana nesta onda.
Testes sintéticos/sem rosto não são validação fisiológica ou clínica.

## Histórico — preparação da Onda 9

Conforme os IDs da Onda 9 no plano: webcam explícita, face/ROIs, buffer RGB temporal,
DSP client-side com equivalência numérica, qualidade/abstenção, latência observada,
worker/capacidades do navegador e descarte local. Confirmar a lista completa de
IDs no plano antes de implementar; não transmitir frames por padrão.
A avaliação em dataset autorizado e a inspeção de ROIs em pessoas permanecem pendentes.

## Onda 9 — Live Lab local

Escopo PV-0901–PV-0913; depende das Ondas 2–5/8. Nenhuma implementação de
Benchmark Lab/experimento da Onda 10 antecipada. Dataset/validação real seguem pendentes.

- [x] PV-0901: getUserMedia sem áudio, seleção de câmera e tracks liberadas no Stop/unmount.
- [x] PV-0902: Face Landmarker JS 1.2.2 CPU/VIDEO em worker, timestamps de mídia reais.
- [x] PV-0903: polígonos roi-v1, preview com aspecto nativo e espelhamento conjunto de overlay/vídeo.
- [x] PV-0904: médias RGB, exclusões e indicadores de pixels/fotometria/movimento por frame.
- [x] PV-0905: ring buffers de 900 observações por ROI, incluindo rejeições/null e descarte.
- [x] PV-0906: GREEN/POS/CHROM, filtros SOS e Welch em TS após regressões sintéticas Python.
- [x] PV-0907: detector/RGB/DSP em worker; um bitmap em trânsito, deduplicação e backpressure.
- [x] PV-0908: nove casos Python/TS compartilhados, três frequências × três métodos;
      BPM/sinal/tempo/PSD com tolerância absoluta 1e-9 na grade 30 Hz.
- [x] PV-0909: permission/detector/warmup/result/abstention/stopped/error,
      continuidade e supressão por invalidez/freshness, sem reaproveitar BPM.
- [x] PV-0910: `/live`, status, regiões, BPM opcional, gráficos, parâmetros e cadência observada.
- [x] PV-0911: permissão negada/tardia, Stop, foco/visibilidade e track-ended simulados,
      seleção de câmera, navegação/unmount e refresh com câmera artificial.
- [x] PV-0912: rede monitorada durante captura com detector real, sem POST/PUT/PATCH,
      chamadas /api ou origens externas. Nenhum frame transmitido.
- [x] PV-0913: export JSON voluntário de derivados, parâmetros/versões/hash; sem imagens.
- ADR 0011, guia live e política de privacidade v4 registrados.
- Assets preparados explicitamente de npm/modelo local verificado; arquivos ignorados
  pelo Git. Não há CDN ou download de modelo durante build/importação.

## Evidências da Onda 9

- uv run ruff check . e uv run mypy: passaram (64 arquivos fonte).
- uv run pytest: 225 testes passaram, incluindo worker real com armadilha de import de áudio.
- uv run python scripts/export_live_reference.py --check: passou; constantes/fixtures reproduzíveis.
- npm run lint e npm run typecheck: passaram, com vendor WASM ignorado pelas ferramentas de fonte.
- npm test: 25 testes passaram: paridade, ROIs sintéticas, adversidades, buffer, continuidade,
  display sem alterar proveniência histórica, freshness e tolerância de cadência.
- npm run test:e2e: 7 cenários passaram na execução final, 4 de Live Lab e 3 de Video Lab.
  Captura por >20 s em câmera Y4M sem rosto, detector/WASM reais, abstenção, exportação,
  Stop, tracks ended, lifecycle e nenhuma transmissão de frames. Sem webcam física.
- NEXT_TELEMETRY_DISABLED=1 npm run build: passou; `/live` e `/video` disponíveis.
- npm run format:check e git diff --check: passaram.
- Screenshots desktop/mobile revisados em artifacts/wave9-desktop.png e
  artifacts/wave9-mobile.png; viewport mobile 390×844 sem overflow horizontal.
- Foi corrigido o bloqueio intermitente do Video Lab: stack dump reproduzido apontou
  import de MediaPipe/audio_record/sounddevice preso em Pa_Initialize. O worker de vídeo
  agora indisponibiliza esse módulo opcional no processo isolado, sem simular inferência.
  Teste com módulo-armadilha e E2E completo passaram após a correção. Não se determinou
  a condição interna do driver/daemon; o caminho de inicialização de áudio foi removido.
- Diagnóstico temporário de stack dumps/PYTHONPATH foi removido da configuração final.
- CI verifica referências geradas e executa E2E com câmera falsa; não executada remotamente.
- Servidores de teste encerrados; sem commit, push, publicação ou mensagem a terceiros.

## Limites atuais do Live Lab

A estimativa resume uma janela passada de 20 s, com atualização 1 s e corte de
bordas 1 s (GREEN)/1,6 s (POS/CHROM). Não é filtro incremental/instantâneo.
Reamostragem explícita para 30 Hz exige cadência mediana >=12 Hz e gates de gaps/CV;
30 Hz da grade não equivale ao FPS analisado e não recupera informação perdida.
Tempos de processamento não são latência sensor→tela ou benchmark generalizável.
Os coeficientes gerados só valem para fs=30 Hz. Kernels equivalem nos nove casos
uniformes testados; não se alega equivalência total de aquisição/ROIs/qualidade.
Rasterização por centros de pixels difere do OpenCV; combined exige todas as regiões.
O fallback currentTime existe, mas requestVideoFrameCallback é o caminho testado.

Eventos de foco/visibilidade/track-ended foram simulados quando o headless não
reproduziu troca física/visibilidade nativa. Câmeras físicas, mobile real, Safari/Firefox,
inspeção positiva de ROIs em pessoas e validação fisiológica permanecem pendentes.
Sem peso/runtime local ou suporte do browser, a UI informa erro e libera recursos.
Stop descarta buffers/worker; só downloads voluntários permanecem com o usuário.
Não há diagnóstico, SpO2, identificação ou precisão clínica demonstrada.

## Histórico — preparação da Onda 10

PV-1001–PV-1010: Benchmark Lab consumindo resultados offline, relatórios e
experimentos reproduzíveis conforme dependências do plano. Infraestrutura/UI pode
usar fixtures artificiais explicitamente rotuladas; comparações com referência e
conclusões reais continuam dependendo de dataset autorizado, manifesto e protocolo
congelados da Onda 6. O usuário informou que ainda não dispõe desses datasets.

## Onda 10 — infraestrutura de estudos e revisão

Escopo realizado PV-1001–PV-1003/PV-1009 e infraestrutura documental de PV-1010.
Dependências de engenharia 6/8/9 atendidas; dependência científica de dados reais não atendida.
Não declarar esta onda cientificamente concluída.

- [x] PV-1001: `/benchmark` importa revisão JSON offline, sem upload ou execução na rota.
- [x] PV-1002: filtros/agrupamentos por método, participante, ROI, cenário, janela e execução;
      gráficos/tabela com erros macro, cobertura, exclusões, falhas e ausência legítima de métrica.
- [x] PV-1003: conversão/estudo gera JSON, resumo com bootstrap, Markdown e comparação PNG;
      resultados individuais do runner mantêm figuras e CSVs originais.
- [ ] PV-1004: comparação de métodos em dataset autorizado continua pendente.
- [ ] PV-1005: comparação anatômica de ROIs continua pendente; não duplicar combined sob outros nomes.
- [ ] PV-1006: avaliação real de janelas/latência/erro/cobertura pendente;
      demonstração artificial executou 10/20/30 s sem medir latência sensor→tela.
- [ ] PV-1007: ruído/desfoque/luz/compressão em vídeos autorizados com alterações verificadas pendentes.
- [ ] PV-1008: movimento/cadência/frames faltantes reais pendentes; proxy artificial não substitui vídeo.
- [x] PV-1009: estudo predefinido congela plano/locks/código, reutiliza verificação de entradas,
      registra parâmetros/seeds/versões/hashes e preserva exclusões/abstenções.
- [ ] PV-1010: gerador produz relatório com hipótese/método/resultados/limitações/trabalhos futuros;
      relatório científico final de experimentos reais permanece pendente.
- Protocolos A–E em benchmarks/protocols/experiments-v1.json são draft, não resultados/pré-registro independente.
- ADR 0012, guia de uso e política de privacidade v5 registrados. Não houve trabalho da Onda 11.

## Evidências da Onda 10

- uv run ruff check . e uv run mypy: passaram (67 arquivos fonte).
- uv run pytest: 230 testes passaram; cinco novos de estudo/contrato/conversão/congelamento.
- Script de schemas executado e npm run contracts gerou BenchmarkReview/JSON Schema/TS;
  modelos científicos anteriores mantidos. Arquivos gerados não foram editados manualmente.
- npm run lint e npm run typecheck: passaram.
- npm test: 30 testes passaram, incluindo peso igual por participante, null sem pares,
  exclusões/abstenções, inconsistências do relatório e export CSV com rótulos seguros.
- npm run test:e2e: nove cenários passaram (dois de benchmark, quatro live, três vídeo).
- Após ajuste de legibilidade/rolagem interna dos gráficos, os dois E2E de benchmark
  passaram novamente; viewport 390×844 sem overflow horizontal do documento.
- NEXT_TELEMETRY_DISABLED=1 npm run build: passou; `/benchmark`, `/live` e `/video` disponíveis.
- npm run format:check e git diff --check: passaram.
- CLI real em RGB/referência artificiais: três participantes, GREEN/CHROM/POS e janelas
  de 10/20/30 s. Pacote em artifacts/wave10-first-demo/results/review/.
  comparison.png e screenshots artifacts/wave10-desktop.png/wave10-mobile.png inspecionados.
- Resumo recomputado da revisão coincide com resumo original por execução. Mutação de
  plano/dado congelado foi recusada; sem pares mantém erro null e cobertura de elegíveis.
- E2E importou bundle produzido pelo runner, filtrou/agrupou, exportou CSV e descartou.
  Nenhuma chamada /api ou método de envio durante a revisão; nenhuma exceção de página.
- CI já exporta/verifica contratos e roda E2E; global setup prepara estudo artificial em
  pasta única ignorada. Não houve execução remota da CI.
- Servidores de testes encerrados; sem commit/push/publicação ou envio a terceiros.

## Limites e retomada científica

A UI valida contrato/consistência, mas não autentica origem, acesso, licença ou hashes
contra arquivos originais. Resultados importados são declarações auditáveis do produtor.
Métricas do recorte são descritivas e condicionais à aceitação; não escolher vencedor
ignorando cobertura, coorte, participantes sem pares ou suporte temporal. Nenhum bootstrap
é recalculado na UI; summary.json offline mantém o bootstrap por participante.
O CSV contém todo o recorte; JSON completo contém a revisão inteira. A página limita a
18 grupos por vez e mantém execuções separadas. Limites de import: 20 MiB/64 runs/100 mil janelas.
Dados ficam na aba, sem localStorage; descartar não apaga fonte ou downloads anteriores.

Os protocolos e o lote não implementam/validam automaticamente transformações externas
nem provam qualidade de ROIs/alinhamento. Não houve avaliação real de erro, latência,
robustez facial, diagnóstico ou validação clínica. O usuário já informou que não tem
dataset; não tratar essa ausência como autorização de acesso/download.

## Próxima ação — Onda 11 de engenharia

Consultar os IDs e dependências da Onda 11 antes de implementar polish/apresentação.
Preservar rótulos artificiais e pendências PV-0610/PV-1004–PV-1008/PV-1010; não apresentar
portfólio como validação fisiológica concluída. Release/deploy não foram autorizados.
Para fechar a parte científica, obter dados autorizados, registrar termos/alinhamento,
congelar protocolo e executar avaliação real antes de redigir conclusões finais.
