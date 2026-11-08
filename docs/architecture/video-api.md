# API local de vídeo — Onda 7

Fluxo: cliente envia um vídeo escolhido → API cria job → subprocesso extrai
RGB e executa método → cliente consulta e exporta derivados. Webcam não é enviada.

## Setup e execução

Da raiz do repositório:

```bash
uv sync --locked
uv run python scripts/fetch_face_model.py
uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

OpenAPI: http://127.0.0.1:8000/openapi.json; Swagger: /docs.
A API inicia sem pesos para health/policy; upload retorna 503 até modelo existir.
Storage padrão: uploads/api, fora do Git. Modelo não é baixado pela API.

Variáveis opcionais: PULSEVISION_STORAGE, PULSEVISION_MODEL, PULSEVISION_API_KEY.
Use caminhos absolutos ao executar fora da raiz. A chave, se configurada, precisa
de 32+ caracteres e deve ser enviada como X-API-Key inclusive em health/docs.
Não imprimir nem versionar a chave. Exposição fora de loopback requer chave;
host/origin continuam restritos. Serviço não possui contas/propriedade por usuário.
Outros limites podem ser definidos por Settings na factory create_app; não vêm
de parâmetros arbitrários do request.

## Contrato HTTP

- GET /api/v1/health: disponibilidade da API/supervisor.
- GET /api/v1/policy: limites, retenção e aviso experimental antes do envio.
- GET /api/v1/methods: GREEN/CHROM/POS, processamento offline.
- POST /api/v1/videos/jobs?method=GREEN&roi=combined: upload binário, 202 + Job.
  Content-Type video/mp4, video/quicktime, video/webm ou video/x-msvideo.
  Não usar multipart/form-data; nome original é ignorado.
- GET /api/v1/videos/jobs/{id}: estado, progresso de fase, datas e código de erro.
- POST /api/v1/videos/jobs/{id}/cancel: parar queued/processing, sem manter original.
- GET /api/v1/videos/jobs/{id}/results?offset=0&limit=100: EstimatePage.
- GET /api/v1/videos/jobs/{id}/signals?series=rgb&offset=0&limit=500&stride=1:
  amostras derivadas; rppg/spectrum aceitam window (índice, zero-based).
  `series=roi` retorna `{timestamp_s, regions}` por frame: contornos externos
  normalizados para orientação de exibição, ou regiões vazias sem geometria.
  Mesma paginação, proteção, TTL e exclusão dos demais derivados.
- GET /api/v1/videos/jobs/{id}/exports?format=json|csv|png: download explícito.
- DELETE /api/v1/videos/jobs/{id}: remove job/arquivos e revoga acesso (204).

Exemplo para arquivo próprio/autorizado:

```bash
curl http://127.0.0.1:8000/api/v1/policy
curl --request POST --header 'Content-Type: video/mp4' \
  --data-binary @/caminho/video.mp4 \
  'http://127.0.0.1:8000/api/v1/videos/jobs?method=POS&roi=forehead'
```

Use o id retornado nas rotas seguintes. O backend recebe o arquivo completo;
isso é diferente do futuro modo webcam local no navegador.

Resultados não prontos: 409; expirados: 410; removidos/desconhecidos: 404.
Arquivo muito grande: 413; assinatura/MIME: 415; fila/rate limit: 429;
modelo ausente: 503; timeout de upload: 408. Codec/corrupção/limites da decodificação
são validados no worker e retornam job failed com erro sanitizado.
Paginação/stride possuem limites e offsets não negativos; caminhos livres não existem.
Stride é decimação para visualização, não reamostragem científica/anti-aliasing.

## Retenção e escopo

Original removido ao concluir/falhar/cancelar; derivados expiram em 24 h.
DELETE pode ser solicitado a qualquer momento. Serviço desligado não executa timer;
restart limpa interrupções/órfãos e aplica TTL. Política completa: docs/privacy/policy.md.
Uma instância por storage: não usar múltiplos workers Uvicorn ou compartilhar root
entre serviços simultâneos. Jobs em andamento não são retomados após restart.
A API limita cada job/fila, mas não possui quota global de disco; operador deve
reservar storage suficiente e acompanhar uso ao manter muitos derivados.
Não é deploy público/multiusuário nem validação clínica.

## Verificação

```bash
uv run pytest tests/test_api.py
```

Testes reais de processamento usam o modelo local e vídeos sintéticos; quando os
pesos faltam em execução offline, testes correspondentes são pulados.
CI inclui download explícito de modelo versionado/verificado por SHA256 antes
dos testes, para não pular as integrações por ausência do arquivo.
Nenhum dataset de pessoas é baixado pela CI. A Onda 6 científica continua pendente.

Onda 9: o worker de vídeo desabilita o import opcional de `sounddevice` antes do
MediaPipe. Foi reproduzido um bloqueio em PortAudio durante esse import, anterior
à detecção visual, especialmente no fluxo E2E com navegador. MediaPipe trata a
indisponibilidade do módulo opcional; o processamento visual não é simulado.
Esse isolamento evita inicializar áudio em jobs exclusivamente de vídeo.
