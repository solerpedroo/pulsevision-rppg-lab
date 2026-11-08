# ADR 0009 — API local e processamento isolado por job

Status: aceito · 2026-11-07 · PV-0701–PV-0710

## Contexto

O núcleo offline já existe. Disponibilizar vídeo voluntariamente enviado sem
bloquear HTTP, armazenar rostos por conveniência ou introduzir streaming de webcam.
A validação fisiológica da Onda 6 continua pendente e é independente desta API.

## Decisão

FastAPI 0.162.2/Uvicorn 0.54.0, Linux/Fedora, single-user/local-first.
Uma instância de API por storage, protegida por flock; usar --workers 1.
SQLite registra metadados do ciclo de vida; arquivos ficam em jobs/<uuid aleatório>.
Uma thread supervisora gerencia fila e um subprocesso Python por vez, sem shell.
Worker não compartilha conexão SQLite ou fila Python com o request e pode ser morto.
Apenas parâmetros tipados GREEN/CHROM/POS e ROI são aceitos do cliente.

Upload é body binário de Request.stream, sem multipart/spool ilimitado.
Servidor ignora Content-Disposition/nome fornecido, limita bytes reais mesmo
sem Content-Length, timeout e slots concorrentes. Checa assinatura e família
MIME; decoder no worker inspeciona container/codec antes do pipeline.
Essa inspeção não é validação forense nem garantia contra toda corrupção.
Conteúdo com assinatura válida mas inválido na decodificação gera job failed,
em vez de travar a requisição de upload.

## Limites e worker

Defaults: arquivo 100 MiB, 8 pendentes (inclui reservas em upload), vídeo 120 s,
até 1920 em cada dimensão e 1920×1080 pixels, 60 FPS, 7200 frames,
timeout de upload 60 s, wall time de job 180 s, CPU time 120 s,
espaço de endereçamento 8 GiB, arquivo de saída 128 MiB e diretório/job 256 MiB.
FPS nominal e dimensões são inspecionados antes da conversão; leitura verifica
também timestamps, quantidade e dimensões de cada frame. FPS efetivo pode variar;
há tolerância de 10% na checagem do limite de FPS, não promessa de aquisição.
Limite de memória é RLIMIT_AS, não medição de RSS ou cgroup. Não é sandbox completa
contra vulnerabilidades nativas. Escopo é serviço experimental local controlado.
Limite de diretório é verificado periodicamente, portanto pode haver ultrapassagem
transitória entre verificações. Não há quota global de storage nesta versão.

Linux PR_SET_PDEATHSIG/SIGKILL encerra worker se a thread/processo pai morrer;
verificação de PPID cobre a janela de corrida na inicialização. RLIMIT_CPU/AS/
FSIZE são aplicados antes das bibliotecas de visão/DSP.
Variáveis de ambiente do filho usam allowlist; a chave da API não é repassada.
Stdout/stderr nativos são descartados; erros públicos usam códigos sanitizados.

## Estados e persistência

queued→processing→completed/failed/cancelled/expired.
Cancelamento é idempotente quando já cancelled e rejeitado para terminais
concluídos/falhos; DELETE remove tudo e torna o identificador inacessível.
Cancel/delete matam e aguardam o processo antes de remover diretório.
Falha, timeout, limite e erro ao iniciar worker removem arquivos, sem deixar
original na fila. Resultados só são publicados como completed após done.json
atômico e término com exit code 0. Progress é fase aproximada, não precisão.

Restart marca queued/processing como failed/service_interrupted e remove arquivos.
Diretórios de upload órfãos com UUID são removidos na inicialização. A limpeza
ignora nomes não gerenciados; não remove diretórios arbitrários do storage.
Metadados mínimos dos jobs expirados são removidos após outro período de retenção.

## Resultados e privacidade

Original e CSV de extração são removidos em estado terminal. Só derivados são
acessíveis: estimativas paginadas, séries RGB/rPPG/PSD com paginação/stride e
exports CSV/JSON/PNG. Valores inválidos são null; BPM anterior não é reaproveitado.
Configurações, versões e hashes de vídeo/modelo acompanham export JSON.
Séries rPPG/PSD são por janela; RGB representa o trace da ROI selecionada.
Dados permanecem históricos offline: timestamps científicos são relativos ao vídeo;
created_at/updated_at/expires_at são epoch UTC em segundos. Não misturar relógios.

Resultados expiram 24 h após término, com limpeza periódica e na inicialização;
consulta após prazo remove acesso mesmo antes do próximo sweep.
Enquanto serviço estiver desligado, não há timer externo: sobras de crash são
removidas na próxima inicialização. Unlink não promete apagamento forense/backups.
DELETE revoga novas consultas, mas não retrai conteúdo já baixado pelo usuário.
Respostas normais usam no-store/nosniff; não há endpoint do vídeo original.

## Limite de acesso e contrato

Loopback por padrão, TrustedHost e Origin allowlist de localhost:3000/127.0.0.1:3000.
Acesso não loopback requer PULSEVISION_API_KEY de pelo menos 32 caracteres;
quando configurada, toda requisição não OPTIONS exige X-API-Key.
CORS preflight é permitido para origens autorizadas sem vazar/usar a chave.
Não confiar em X-Forwarded-For no código para rate limit. Um proxy deve ser
configurado conscientemente; isto não é autenticação multiusuário/autorização por pessoa.
Rate limit por peer: 120 requests/min, uploads 10/min. Health fica fora do limiter,
mas continua sujeito a host/origin/acesso. Fila cheia retorna 429.
Múltiplos processos e exposição pública sem proxy/TLS/controle adicional estão fora do escopo.
Não há Redis, URL externa de vídeo, pickle, execução de comando do cliente ou câmera.

OpenAPI e schemas Pydantic descrevem rotas/parâmetros. UI de upload e consentimento
visual ficam na Onda 8; /policy fornece destino/retenção/limites para essa interface.
Testes cobrem subprocesso real com vídeo sintético sem rosto, limites, concorrência,
cancelamento, timeout, restart, expiração, deleção e falhas de upload.
Nenhum teste demonstra precisão fisiológica ou robustez em pessoas.
