# PulseVision Video API

Implementada na Onda 7: FastAPI local, SQLite de metadados e subprocesso isolado
por job. Execute da raiz: uv run uvicorn services.api.app.main:app --host 127.0.0.1
--port 8000 --workers 1 --no-access-log.
Guia completo: ../../docs/architecture/video-api.md.
Contrato OpenAPI em /openapi.json; upload binário, sem multipart ou streaming de webcam.
