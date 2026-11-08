import asyncio
import hmac
import ipaddress
import json
import shutil
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any, Literal

import anyio
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from rppg_types.models import Method, Roi
from starlette.concurrency import run_in_threadpool
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import ClientDisconnect

from .config import Settings
from .jobs import JobManager
from .schemas import EstimatePage, Job, SignalPage

ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
MIMES = {"video/mp4", "video/quicktime", "video/webm", "video/x-msvideo"}


def sniff(header: bytes, mime: str) -> str:
    if len(header) >= 12 and header[4:8] == b"ftyp" and mime in {"video/mp4", "video/quicktime"}:
        return "mp4"
    if header.startswith(b"\x1aE\xdf\xa3") and mime == "video/webm":
        return "webm"
    if header.startswith(b"RIFF") and header[8:12] == b"AVI " and mime == "video/x-msvideo":
        return "avi"
    raise HTTPException(415, "Unsupported media signature or MIME mismatch")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        manager = JobManager(settings)
        app.state.manager = manager
        manager.start()
        try:
            yield
        finally:
            await run_in_threadpool(manager.close)

    app = FastAPI(title="PulseVision Local Video API", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ORIGINS,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["content-type", "x-api-key"],
    )

    @app.middleware("http")
    async def boundary(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        origin = request.headers.get("origin")
        if origin is not None and origin not in ORIGINS:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        peer = request.client.host if request.client else ""
        try:
            local = ipaddress.ip_address(peer).is_loopback
        except ValueError:
            local = False
        if not local and settings.api_key is None:
            return JSONResponse({"detail": "Local access only"}, status_code=403)
        if (
            request.method != "OPTIONS"
            and settings.api_key is not None
            and not hmac.compare_digest(
                request.headers.get("x-api-key", "").encode("utf-8"),
                settings.api_key.encode("utf-8"),
            )
        ):
            return JSONResponse({"detail": "Invalid API key"}, status_code=401)
        if request.url.path != "/api/v1/health" and request.method != "OPTIONS":
            manager: JobManager = request.app.state.manager
            if not manager.allow(
                peer,
                upload=request.method == "POST" and (request.url.path == "/api/v1/videos/jobs"),
            ):
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                    headers={"Retry-After": "60"},
                )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    def manager(request: Request) -> JobManager:
        return request.app.state.manager  # type: ignore[no-any-return]

    def job(request: Request, identifier: str) -> Job:
        try:
            item = manager(request).get(identifier)
        except KeyError:
            raise HTTPException(404, "Job not found") from None
        if item.expires_at <= time.time() and item.status != "expired":
            manager(request).cleanup()
            item = manager(request).get(identifier)
        return item

    def ready(request: Request, identifier: str) -> Path:
        item = job(request, identifier)
        if item.status == "expired":
            raise HTTPException(410, "Job expired")
        if item.status != "completed":
            raise HTTPException(409, "Results are not available")
        return manager(request).directory(identifier)

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        if not app.state.manager.thread.is_alive():
            raise HTTPException(503, "Worker supervisor unavailable")
        return {"status": "ok"}

    @app.get("/api/v1/methods")
    def methods() -> dict[str, Any]:
        return {"methods": ["GREEN", "CHROM", "POS"], "mode": "offline_noncausal"}

    @app.get("/api/v1/policy")
    def policy() -> dict[str, Any]:
        return {
            "max_upload_bytes": settings.max_upload_bytes,
            "max_duration_s": settings.max_duration_s,
            "max_pixels": settings.max_pixels,
            "max_fps": settings.max_fps,
            "retention_s": settings.retention_s,
            "original_deleted_at_terminal_state": True,
            "webcam_streaming": False,
            "experimental_notice": "Experimental estimate; not a medical device.",
        }

    @app.post(
        "/api/v1/videos/jobs",
        status_code=202,
        response_model=Job,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    mime: {"schema": {"type": "string", "format": "binary"}} for mime in MIMES
                },
            }
        },
    )
    async def upload(
        request: Request,
        method: Method = "GREEN",
        roi: Roi = "combined",
    ) -> Job:
        mime = request.headers.get("content-type", "").split(";")[0].lower()
        if mime not in MIMES:
            raise HTTPException(415, "Send a supported video as a raw binary request body")
        length = request.headers.get("content-length")
        if length is not None:
            try:
                declared = int(length)
            except ValueError:
                raise HTTPException(400, "Invalid Content-Length") from None
            if declared < 0:
                raise HTTPException(400, "Invalid Content-Length")
            if declared > settings.max_upload_bytes:
                raise HTTPException(413, "Upload too large")
        if not settings.model.is_file():
            raise HTTPException(503, "Face model unavailable; configure the local model")
        store = manager(request)
        if not await run_in_threadpool(store.reserve):
            raise HTTPException(429, "Video queue is full")
        identifier = uuid.uuid4().hex
        directory = store.directory(identifier)
        accepted = False
        try:
            directory.mkdir(mode=0o700)
            count = 0
            header = bytearray()
            async with asyncio.timeout(settings.upload_timeout_s):
                with (directory / "input.part").open("xb") as handle:
                    async for chunk in request.stream():
                        count += len(chunk)
                        if count > settings.max_upload_bytes:
                            raise HTTPException(413, "Upload too large")
                        if len(header) < 64:
                            header.extend(chunk[: 64 - len(header)])
                        await run_in_threadpool(handle.write, chunk)
            if count == 0:
                raise HTTPException(400, "Empty upload")
            container = sniff(bytes(header), mime)
            (directory / "input.part").rename(directory / "input.bin")
            result = await run_in_threadpool(store.enqueue, identifier, method, roi, container)
            accepted = True
            return result
        except ClientDisconnect:
            raise HTTPException(400, "Upload interrupted") from None
        except TimeoutError:
            raise HTTPException(408, "Upload timed out") from None
        finally:
            with anyio.CancelScope(shield=True):
                await run_in_threadpool(store.release)
                if not accepted:
                    await run_in_threadpool(shutil.rmtree, directory, True)

    @app.get("/api/v1/videos/jobs/{identifier}", response_model=Job)
    def status(request: Request, identifier: str) -> Job:
        return job(request, identifier)

    @app.post("/api/v1/videos/jobs/{identifier}/cancel", response_model=Job)
    def cancel(request: Request, identifier: str) -> Job:
        job(request, identifier)
        try:
            result = manager(request).cancel(identifier)
        except ValueError:
            raise HTTPException(409, "Job is no longer active") from None
        except KeyError:
            raise HTTPException(404, "Job not found") from None
        assert result is not None
        return result

    @app.delete("/api/v1/videos/jobs/{identifier}", status_code=204)
    def delete(request: Request, identifier: str) -> Response:
        job(request, identifier)
        manager(request).cancel(identifier, delete=True)
        return Response(status_code=204)

    @app.get("/api/v1/videos/jobs/{identifier}/results", response_model=EstimatePage)
    def results(
        request: Request,
        identifier: str,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> EstimatePage:
        directory = ready(request, identifier)
        try:
            data = json.loads((directory / "results.json").read_text())
        except OSError:
            raise HTTPException(410, "Results no longer available") from None
        return EstimatePage(
            job_id=identifier,
            total=len(data["estimates"]),
            offset=offset,
            limit=limit,
            items=data["estimates"][offset : offset + limit],
            summary=data["summary"],
        )

    @app.get("/api/v1/videos/jobs/{identifier}/signals", response_model=SignalPage)
    def signals(
        request: Request,
        identifier: str,
        series: Literal["rgb", "rppg", "spectrum", "roi"] = "rppg",
        window: Annotated[int, Query(ge=0, le=10000)] = 0,
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(ge=1, le=1000)] = 500,
        stride: Annotated[int, Query(ge=1, le=1000)] = 1,
    ) -> SignalPage:
        directory = ready(request, identifier)
        file = (
            directory / f"{series}.json"
            if series in {"rgb", "roi"}
            else directory / "signals" / f"{window}.json"
        )
        try:
            data = json.loads(file.read_text())
        except OSError:
            raise HTTPException(404, "Signal window unavailable") from None
        points = data if series in {"rgb", "roi"} else data[series]
        return SignalPage(
            job_id=identifier,
            total=len(points),
            offset=offset,
            stride=stride,
            points=points[offset : offset + limit * stride : stride],
        )

    @app.get("/api/v1/videos/jobs/{identifier}/exports")
    def export(
        request: Request, identifier: str, format: Literal["json", "csv", "png"] = "json"
    ) -> FileResponse:
        directory = ready(request, identifier)
        filename, mime = {
            "json": ("results.json", "application/json"),
            "csv": ("estimates.csv", "text/csv"),
            "png": ("diagnostics.png", "image/png"),
        }[format]
        return FileResponse(directory / filename, media_type=mime, filename="pulsevision." + format)

    return app


app = create_app()
