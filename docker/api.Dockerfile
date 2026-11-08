FROM ghcr.io/astral-sh/uv:0.12.24 AS uv
FROM python:3.12-slim-bookworm AS runtime
RUN apt-get update && apt-get install --no-install-recommends -y libgl1 libegl1 libgles2 libglib2.0-0 libgomp1 && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp/pulsevision PULSEVISION_STORAGE=/storage PULSEVISION_MODEL=/models/face_landmarker.task
COPY pyproject.toml uv.lock ./
COPY packages packages
COPY benchmarks benchmarks
COPY services services
RUN uv sync --locked --no-dev --no-editable --no-cache
RUN groupadd --gid 10001 pulsevision && useradd --uid 10001 --gid pulsevision --no-create-home pulsevision && mkdir /storage /models && chown pulsevision:pulsevision /storage
USER pulsevision
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=20s CMD /app/.venv/bin/python -c "import os,urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8000/api/v1/health',headers={'X-API-Key':os.environ['PULSEVISION_API_KEY']}),timeout=3).read()"
CMD ["/app/.venv/bin/uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log", "--no-server-header"]
