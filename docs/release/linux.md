# Linux/Fedora installation and local containers

PV-1104/PV-1105 · v1.0.0 · 2026-11-08.

## Native execution

Install Git, uv 0.12.24 and Node.js 24/npm using their maintained installation
instructions. Keep the system Python unchanged: `uv python install 3.12`,
`uv sync --locked`, `npm ci`. The PyAV wheel supplies FFmpeg libraries; a separate
ffmpeg executable and CUDA are unnecessary for the tested acquisition path.
MediaPipe/OpenCV require working system GL/EGL/GLib libraries. If a native import
fails, inspect the named missing library and install its distribution package;
the Debian container recipe records the dependencies tested here. Do not replace
Fedora's system Python or disable SELinux to address a missing library.

Explicitly prepare model and browser assets:

```bash
uv run python scripts/fetch_face_model.py
npm run live:assets
```

Start Uvicorn on `127.0.0.1:8000` with one worker as shown in the README, then start
Next.js. One API instance owns each storage directory; never run multiple workers
against it. Stop both with Ctrl+C. `uploads/api` is ignored by Git. A completed,
failed or cancelled job deletes its original video; derived results expire after
24 hours. The API cleanup loop runs while the service is running, including at
restart. Explicit deletion does not remove downloads already saved elsewhere.

If ports are occupied, preserve the existing services. Example native configuration:

```bash
PULSEVISION_WEB_ORIGINS=http://localhost:3100,http://127.0.0.1:3100 uv run uvicorn services.api.app.main:app --host 127.0.0.1 --port 8100 --workers 1
NEXT_PUBLIC_PULSEVISION_API_URL=http://127.0.0.1:8100 npm run dev -w apps/web -- --port 3100
```

Origins must be explicit loopback HTTP origins with ports. The public URL contains
no credential and is compiled into production builds. Alternatively choose the API
address in Video Lab's connection panel. API keys stay in browser memory, not a
public environment variable. Never put secrets in `NEXT_PUBLIC_*`.

## Camera permission

Open `/live` through localhost, allow the browser's camera permission and press
Start explicitly. Stop releases tracks, worker and buffers. Focus/visibility loss
and track end stop the session. No microphone is requested. If permission was
blocked, reset this site's camera permission in browser settings and reload.
Check OS camera privacy settings and competing apps if no device is available.
Remote plain HTTP is not a secure camera context. This release is for loopback
use; internet deployment and HTTPS configuration are outside the local recipe.

The test suite uses Chromium and a face-free artificial Y4M source. Physical
Fedora cameras, mobile hardware, Firefox and Safari were not validated here.
No model/runtime assets means an explicit error, not an invented estimate.

## Optional Compose

Use Docker Compose v2, or rootless Podman with a Compose provider. The recipe was
exercised with rootless Podman 5.8.9 and podman-compose 1.6.0; Docker compatibility
is declared by the Compose file but was not tested with a Docker daemon.
Generate credentials privately and stage a verified copy of the existing model:

```bash
uv run python scripts/init_container_env.py
uv run python scripts/prepare_container_model.py
docker compose --env-file .env.containers up --build -d
```

Podman alternative (ephemeral provider, no global install):

```bash
uvx --from podman-compose==1.6.0 podman-compose --env-file .env.containers up --build -d
```

`.env.containers` has mode 0600 and is never overwritten or printed by the helper.
The staging directory is 0700; only its model copy is readable inside the non-root
containers and SELinux-relabelled with `z`. The original model's permissions/label
are preserved. Neither weights nor credentials enter the build context.

API and web bind only to host loopback, by default ports 8000/3000. Set
`PULSEVISION_API_PORT=8100 PULSEVISION_WEB_PORT=3100` before Compose to use alternate
ports; in Video Lab choose `http://127.0.0.1:8100`. Enter the private key from your
local env file in its connection panel. Do not paste it into chat or shared logs.
Containers require that key even for health requests. Compose health checks read
it from the API's private environment. Do not share resolved Compose output or
container inspect output: both may reveal environment secrets.

A named volume holds jobs; the model is the only host bind. Services are non-root,
read-only, drop capabilities and have CPU/memory/PID limits. The API supervises its
worker subprocess; a second worker service would violate single-store ownership.
Browser camera processing still runs in the user's browser. Assets are served
locally without a runtime CDN.

```bash
docker compose --env-file .env.containers down
# Only when you deliberately want to destroy this project's stored jobs:
docker compose --env-file .env.containers down --volumes
```

Use the corresponding Podman provider command if applicable. Keep the same project
name across commands. Base image tags are not immutable digests; rebuild/audit
before reuse. This is a bounded local research setup, not an internet sandbox.
