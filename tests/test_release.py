import json
import stat
import tomllib
from pathlib import Path

import pytest

from scripts.init_container_env import create_env


def test_release_versions_agree():
    expected = Path("VERSION").read_text().strip()
    assert expected == "1.0.0"
    for path in ["package.json", "apps/web/package.json"]:
        assert json.loads(Path(path).read_text())["version"] == expected
    assert tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"] == expected


def test_local_env_is_private_unique_and_never_overwritten(tmp_path):
    path = tmp_path / "env"
    create_env(path)
    content = path.read_text()
    assert len(content.split("=", 1)[1].strip()) >= 32
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        create_env(path)
    assert path.read_text() == content


def test_model_staging_preserves_original_and_rejects_mutation(tmp_path, monkeypatch):
    import hashlib

    from scripts import prepare_container_model as model

    source = tmp_path / "original.task"
    source.write_bytes(b"synthetic model fixture")
    source.chmod(0o600)
    monkeypatch.setattr(model, "SHA256", hashlib.sha256(source.read_bytes()).hexdigest())
    import os

    previous_umask = os.umask(0o077)
    try:
        target = model.stage(source, tmp_path / "staged")
    finally:
        os.umask(previous_umask)
    assert target.read_bytes() == source.read_bytes()
    assert stat.S_IMODE(source.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(target.stat().st_mode) == 0o444
    assert model.stage(source, target.parent) == target
    target.chmod(0o600)
    target.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="unexpected staged model"):
        model.stage(source, target.parent)


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://example.com",
        "http://localhost:3100/path",
        "http://user@localhost:3100",
        "http://localhost",
    ],
)
def test_web_origins_reject_nonlocal_or_ambiguous_values(origin):
    from services.api.app.config import Settings

    with pytest.raises(ValueError):
        Settings(web_origins=(origin,))


def test_explicit_alternate_loopback_origin():
    from fastapi.testclient import TestClient

    from services.api.app.config import Settings
    from services.api.app.main import create_app

    client = TestClient(
        create_app(Settings(web_origins=("http://localhost:3100",))), client=("127.0.0.1", 50000)
    )
    response = client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:3100", "Access-Control-Request-Method": "GET"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3100"
    assert (
        client.options("/api/v1/health", headers={"Origin": "http://localhost:3000"}).status_code
        == 403
    )
