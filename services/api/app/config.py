import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    root: Path = Path("uploads/api")
    model: Path = Path("models/face_landmarker.task")
    api_key: str | None = None
    web_origins: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")
    max_upload_bytes: int = 100 * 1024 * 1024
    max_pending: int = 8
    max_duration_s: float = 120.0
    max_pixels: int = 1920 * 1080
    max_dimension: int = 1920
    max_fps: float = 60.0
    max_frames: int = 7200
    job_timeout_s: float = 180.0
    cpu_limit_s: int = 120
    memory_limit_bytes: int = 8 * 1024**3
    max_job_bytes: int = 256 * 1024 * 1024
    upload_timeout_s: float = 60.0
    retention_s: float = 86400.0
    cleanup_interval_s: float = 30.0
    request_limit_per_minute: int = 120
    upload_limit_per_minute: int = 10

    def __post_init__(self) -> None:
        import math

        for key, value in self.__dict__.items():
            if key in {"root", "model", "api_key", "web_origins"}:
                continue
            if not math.isfinite(value) or value <= 0:
                raise ValueError("API limits must be finite and positive")
        if not self.web_origins:
            raise ValueError("At least one explicit web origin is required")
        for origin in self.web_origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme != "http"
                or parsed.hostname not in {"localhost", "127.0.0.1"}
                or parsed.port is None
                or parsed.netloc != f"{parsed.hostname}:{parsed.port}"
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("Web origins must be explicit loopback HTTP origins with a port")
        if self.api_key is not None and len(self.api_key) < 32:
            raise ValueError("API key must contain at least 32 characters")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            root=Path(os.environ.get("PULSEVISION_STORAGE", "uploads/api")),
            model=Path(os.environ.get("PULSEVISION_MODEL", "models/face_landmarker.task")),
            api_key=os.environ.get("PULSEVISION_API_KEY"),
            web_origins=tuple(
                os.environ.get(
                    "PULSEVISION_WEB_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
                ).split(",")
            ),
        )
