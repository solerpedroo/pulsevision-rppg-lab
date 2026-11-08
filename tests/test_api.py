import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from starlette.testclient import TestClient
from video_factory import make_video

from services.api.app.config import Settings
from services.api.app.jobs import JobManager
from services.api.app.main import create_app

BASE = "/api/v1/videos/jobs"
MODEL = Path("models/face_landmarker.task").resolve()


def client(settings):
    return TestClient(create_app(settings), client=("127.0.0.1", 50000))


def wait_terminal(api, identifier, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = api.get(BASE + "/" + identifier)
        assert result.status_code == 200
        data = result.json()
        if data["status"] not in {"queued", "processing"}:
            return data
        time.sleep(0.05)
    pytest.fail("Job did not finish within deadline")


@pytest.fixture
def configured(tmp_path):
    if not MODEL.exists():
        pytest.skip("Optional local MediaPipe model not available")
    return Settings(root=tmp_path / "store", model=MODEL)


def test_health_openapi_and_privacy_without_model(tmp_path):
    with client(Settings(root=tmp_path / "store", model=tmp_path / "missing.task")) as api:
        assert api.get("/api/v1/health").json() == {"status": "ok"}
        schema = api.get("/openapi.json").json()
        assert BASE in schema["paths"]
        assert "requestBody" in schema["paths"][BASE]["post"]
        assert api.get("/api/v1/policy").json()["webcam_streaming"] is False
        result = api.post(BASE, content=b"x", headers={"Content-Type": "video/mp4"})
        assert result.status_code == 503
    assert list((tmp_path / "store" / "jobs").iterdir()) == []


def test_streaming_video_roundtrip_and_explicit_delete(configured, tmp_path):
    video = make_video(tmp_path / "blank.mp4", list(range(0, 2000, 40)), width=128, height=128)
    with client(configured) as api:
        response = api.post(
            BASE + "?method=POS",
            content=video.read_bytes(),
            headers={
                "Content-Type": "video/mp4",
                "Content-Disposition": 'attachment; filename="../../private.mov"',
            },
        )
        assert response.status_code == 202, response.text
        identifier = response.json()["id"]
        result = wait_terminal(api, identifier)
        assert result["status"] == "completed", result
        assert result["progress"] == 1
        root = configured.root / "jobs" / identifier
        assert not (root / "input.bin").exists()
        assert not (root / "trace.csv").exists()
        page = api.get(BASE + "/" + identifier + "/results?limit=1").json()
        assert page["total"] == 1 and len(page["items"]) == 1
        assert page["items"][0]["bpm"] is None
        assert page["items"][0]["method"] == "POS"
        assert api.post(BASE + "/" + identifier + "/cancel").status_code == 409
        assert api.get(BASE + "/" + identifier + "/results").status_code == 200
        assert api.get(BASE + "/" + identifier + "/results").headers["cache-control"] == "no-store"
        raw = api.get(BASE + "/" + identifier + "/signals?series=rgb&limit=3&stride=2").json()
        assert raw["total"] == 50 and len(raw["points"]) == 3
        assert raw["points"][0]["r"] is None
        regions = api.get(BASE + "/" + identifier + "/signals?series=roi&offset=1&limit=2").json()
        assert regions["total"] == 50
        assert regions["points"] == [
            {"timestamp_s": 0.04, "regions": {}},
            {"timestamp_s": 0.08, "regions": {}},
        ]
        for kind, mime in [("json", "application/json"), ("csv", "text/csv"), ("png", "image/png")]:
            export = api.get(BASE + "/" + identifier + "/exports?format=" + kind)
            assert export.status_code == 200
            assert export.headers["content-type"].startswith(mime)
        assert api.get(BASE + "/" + identifier + "/results?limit=10000").status_code == 422
        assert api.get(BASE + "/" + identifier + "/signals?window=999").status_code == 404
        assert api.delete(BASE + "/" + identifier).status_code == 204
        assert api.get(BASE + "/" + identifier).status_code == 404
        assert api.get(BASE + "/" + identifier + "/exports").status_code == 404
        assert not root.exists()
        assert not (tmp_path / "private.mov").exists()


@pytest.mark.parametrize(
    "case,expected",
    [
        ("mime", 415),
        ("signature", 415),
        ("empty", 400),
        ("size", 413),
    ],
)
def test_invalid_uploads_leave_no_files(configured, case, expected):
    settings = replace(configured, max_upload_bytes=20)
    body, mime = b"invalid", "video/mp4"
    if case == "mime":
        mime = "text/plain"
    if case == "empty":
        body = b""
    if case == "size":
        body = b"x" * 21
    with client(settings) as api:
        result = api.post(BASE, content=body, headers={"Content-Type": mime})
        assert result.status_code == expected
        assert list((settings.root / "jobs").iterdir()) == []
        assert api.app.state.manager.uploads == 0


def test_chunked_size_cannot_bypass_content_length(configured):
    with client(replace(configured, max_upload_bytes=20)) as api:
        result = api.post(
            BASE, content=iter([b"0000ftypisom", b"x" * 30]), headers={"Content-Type": "video/mp4"}
        )
        assert result.status_code == 413
        assert list((configured.root / "jobs").iterdir()) == []


def test_truncated_upload_fails_job_and_removes_original(configured):
    with client(configured) as api:
        response = api.post(
            BASE, content=b"0000ftypisom" + b"corrupted" * 20, headers={"Content-Type": "video/mp4"}
        )
        assert response.status_code == 202
        identifier = response.json()["id"]
        terminal = wait_terminal(api, identifier)
        assert terminal["status"] == "failed"
        assert not (configured.root / "jobs" / identifier).exists()
        assert api.get(BASE + "/" + identifier + "/results").status_code == 409


def test_active_cancel_timeout_and_health_is_responsive(configured, tmp_path):
    video = make_video(tmp_path / "long.mp4", list(range(0, 25_000, 40)), width=128, height=128)
    with client(replace(configured, job_timeout_s=0.3)) as api:
        response = api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        started = time.monotonic()
        assert api.get("/api/v1/health").status_code == 200
        assert time.monotonic() - started < 0.5
        terminal = wait_terminal(api, identifier)
        assert terminal["status"] == "failed" and terminal["error"] == "job_timeout"
        assert not (configured.root / "jobs" / identifier).exists()
    with client(configured) as api:
        response = api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        cancelled = api.post(BASE + "/" + identifier + "/cancel")
        assert cancelled.json()["status"] == "cancelled"
        assert api.get(BASE + "/" + identifier + "/exports").status_code == 409
        assert not (configured.root / "jobs" / identifier).exists()


def test_queue_and_concurrent_uploads(configured, tmp_path):
    video = make_video(tmp_path / "blank.mp4", [0, 40, 80], width=128, height=128)
    with client(replace(configured, max_pending=1)) as api:

        def submit():
            return api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})

        with ThreadPoolExecutor(max_workers=2) as executor:
            responses = list(executor.map(lambda _: submit(), range(2)))
        assert sorted(result.status_code for result in responses) == [202, 429]
        identifier = next(result.json()["id"] for result in responses if result.status_code == 202)
        assert api.delete(BASE + "/" + identifier).status_code == 204
        assert list((configured.root / "jobs").iterdir()) == []


def test_retention_deletes_artifacts_and_reports_expired(configured, tmp_path):
    video = make_video(tmp_path / "blank.mp4", [0, 40, 80], width=128, height=128)
    with client(configured) as api:
        response = api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        assert wait_terminal(api, identifier)["status"] == "completed"
        api.app.state.manager.update(identifier, expires_at=time.time() - 1)
        assert api.get(BASE + "/" + identifier).json()["status"] == "expired"
        assert api.get(BASE + "/" + identifier + "/results").status_code == 410
        assert not (configured.root / "jobs" / identifier).exists()


def test_local_boundary_auth_origin_host_and_rate_limits(tmp_path):
    settings = Settings(root=tmp_path / "store", api_key="x" * 32)
    with client(settings) as api:
        assert api.get("/api/v1/health").status_code == 401
        assert api.get("/api/v1/health", headers={"X-API-Key": "x" * 32}).status_code == 200
        assert (
            api.get(
                "/api/v1/health", headers={"X-API-Key": "x" * 32, "Origin": "https://evil.test"}
            ).status_code
            == 403
        )
        assert (
            api.get(
                "/api/v1/health", headers={"X-API-Key": "x" * 32, "Host": "evil.test"}
            ).status_code
            == 400
        )
    with client(Settings(root=tmp_path / "store2", request_limit_per_minute=1)) as api:
        assert api.get("/api/v1/methods").status_code == 200
        assert api.get("/api/v1/methods").status_code == 429
        assert api.get("/api/v1/health").status_code == 200
    with TestClient(
        create_app(Settings(root=tmp_path / "remote")), client=("203.0.113.1", 1000)
    ) as api:
        assert api.get("/api/v1/health").status_code == 403


def test_restart_cleans_interrupted_jobs_and_single_process_lock(tmp_path):
    settings = Settings(root=tmp_path / "store")
    manager = JobManager(settings)
    identifier = "a" * 32
    directory = manager.directory(identifier)
    directory.mkdir()
    (directory / "input.bin").write_bytes(b"private content")
    manager.enqueue(identifier, "GREEN", "combined", "mp4")
    with pytest.raises(RuntimeError):
        JobManager(settings)
    # Simulate abrupt exit: no thread/child was started.
    manager.db.close()
    manager.guard.close()
    with client(settings) as api:
        assert api.get(BASE + "/" + identifier).json()["error"] == "service_interrupted"
        assert not directory.exists()
        assert api.get(BASE + "/..%2F..%2Fprivate").status_code in {404, 405}


@pytest.mark.parametrize(
    "limit,value",
    [("max_pixels", 100), ("max_duration_s", 0.1), ("max_fps", 5), ("max_frames", 10)],
)
def test_worker_enforces_video_limits(configured, tmp_path, limit, value):
    video = make_video(tmp_path / "blank.mp4", list(range(0, 2000, 40)), width=128, height=128)
    with client(replace(configured, **{limit: value})) as api:
        response = api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        result = wait_terminal(api, identifier)
        assert result["status"] == "failed" and result["error"] == "video_limits_exceeded"
        assert not (configured.root / "jobs" / identifier).exists()


def test_disconnect_during_stream_cleans_reservation_and_bytes(configured):
    from starlette.requests import ClientDisconnect

    def chunks():
        yield b"0000ftypisom"
        raise ClientDisconnect()

    with client(configured) as api:
        response = api.post(BASE, content=chunks(), headers={"Content-Type": "video/mp4"})
        assert response.status_code == 400
        assert api.app.state.manager.uploads == 0
        assert list((configured.root / "jobs").iterdir()) == []


def test_restart_removes_orphan_upload_but_preserves_unmanaged_paths(tmp_path):
    settings = Settings(root=tmp_path / "store")
    orphan = settings.root / "jobs" / ("b" * 32)
    orphan.mkdir(parents=True)
    (orphan / "input.part").write_bytes(b"private partial upload")
    unrelated = settings.root / "jobs" / "notes"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("unmanaged")
    with client(settings) as api:
        assert api.get("/api/v1/health").status_code == 200
        assert not orphan.exists()
        assert (unrelated / "keep.txt").read_text() == "unmanaged"


def test_authenticated_cors_preflight_does_not_require_secret_header(tmp_path):
    settings = Settings(root=tmp_path / "store", api_key="x" * 32)
    with client(settings) as api:
        response = api.options(
            BASE,
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,x-api-key",
            },
        )
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_worker_address_space_limit_cleans_up(configured, tmp_path):
    video = make_video(tmp_path / "blank.mp4", [0, 40, 80], width=128, height=128)
    with client(replace(configured, memory_limit_bytes=32 * 1024 * 1024)) as api:
        response = api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        result = wait_terminal(api, identifier)
        assert result["status"] == "failed"
        assert not (configured.root / "jobs" / identifier).exists()


def test_failed_worker_start_does_not_leave_queued_original(configured, monkeypatch):
    import services.api.app.jobs as jobs

    def fail(*args, **kwargs):
        raise OSError("synthetic process startup failure")

    monkeypatch.setattr(jobs.subprocess, "Popen", fail)
    with client(configured) as api:
        response = api.post(BASE, content=b"0000ftypisom", headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        result = wait_terminal(api, identifier)
        assert result["status"] == "failed" and result["error"] == "worker_start_failed"
        assert not (configured.root / "jobs" / identifier).exists()


def test_async_upload_timeout_cleans_partial_bytes(configured):
    import asyncio

    settings = replace(configured, upload_timeout_s=0.05)
    app = create_app(settings)
    messages = []

    async def story():
        counter = 0

        async def receive():
            nonlocal counter
            if counter == 0:
                counter += 1
                return {"type": "http.request", "body": b"0000ftypisom", "more_body": True}
            await asyncio.sleep(0.3)
            return {"type": "http.request", "body": b"tail", "more_body": False}

        async def send(message):
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": BASE,
            "raw_path": BASE.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver"), (b"content-type", b"video/mp4")],
            "client": ("127.0.0.1", 50001),
            "server": ("testserver", 80),
        }
        await app(scope, receive, send)

    with TestClient(app, client=("127.0.0.1", 50000)):
        asyncio.run(story())
        assert next(x["status"] for x in messages if x["type"] == "http.response.start") == 408
        assert app.state.manager.uploads == 0
        assert list((settings.root / "jobs").iterdir()) == []


def test_non_ascii_api_key_is_rejected_without_server_error(tmp_path):
    with client(Settings(root=tmp_path / "store", api_key="x" * 32)) as api:
        assert api.get("/api/v1/health", headers={"X-API-Key": b"\xff"}).status_code == 401


def test_suspended_worker_keeps_health_responsive_and_can_be_killed(configured):
    import os
    import signal

    with client(configured) as api:
        response = api.post(BASE, content=b"0000ftypisom", headers={"Content-Type": "video/mp4"})
        identifier = response.json()["id"]
        deadline = time.monotonic() + 3
        suspended = False
        while time.monotonic() < deadline:
            manager = api.app.state.manager
            with manager.lock:
                if manager.active and manager.active[0] == identifier:
                    process = manager.active[1]
                    if process.poll() is None:
                        os.kill(process.pid, signal.SIGSTOP)
                        suspended = True
                        break
            time.sleep(0.01)
        assert suspended
        try:
            started = time.monotonic()
            assert api.get("/api/v1/health").status_code == 200
            assert time.monotonic() - started < 0.5
            assert api.post(BASE + "/" + identifier + "/cancel").json()["status"] == "cancelled"
            assert process.poll() is not None
            assert not (configured.root / "jobs" / identifier).exists()
        finally:
            # Test failure must not leave a deliberately suspended child behind.
            if process.poll() is None:
                process.kill()
                process.wait(timeout=3)


def test_vision_worker_never_initializes_optional_audio(configured, tmp_path, monkeypatch):
    trap = tmp_path / "audio_trap"
    trap.mkdir()
    marker = tmp_path / "audio_imported"
    (trap / "sounddevice.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
        "raise RuntimeError('Video worker must not initialize audio')\n"
    )
    monkeypatch.setenv("PYTHONPATH", str(trap))
    video = make_video(tmp_path / "blank.mp4", list(range(0, 200, 40)), width=128, height=128)
    with client(configured) as api:
        response = api.post(BASE, content=video.read_bytes(), headers={"Content-Type": "video/mp4"})
        assert response.status_code == 202
        assert wait_terminal(api, response.json()["id"])["status"] == "completed"
    assert not marker.exists()


def test_rejections_have_privacy_headers_and_version(tmp_path):
    settings = Settings(
        root=tmp_path / "store",
        model=tmp_path / "none",
        api_key="a" * 32,
        request_limit_per_minute=1,
    )
    with client(settings) as api:
        denied = api.get("/api/v1/policy")
        assert denied.status_code == 401
        headers = {"X-API-Key": "a" * 32}
        origin = api.get("/api/v1/policy", headers={**headers, "Origin": "https://invalid.test"})
        assert origin.status_code == 403
        assert api.get("/openapi.json", headers=headers).json()["info"]["version"] == "1.0.0"
        limited = api.get("/api/v1/policy", headers=headers)
        assert limited.status_code == 429 and limited.headers["retry-after"] == "60"
        for response in [denied, origin, limited]:
            assert response.headers["cache-control"] == "no-store"
            assert response.headers["x-content-type-options"] == "nosniff"
