import hashlib
import importlib.metadata
import json
import platform
import subprocess
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from rppg_core.methods.config import MethodConfig
from rppg_core.quality.config import QualityConfig
from rppg_core.signals.config import SignalConfig
from rppg_types.models import Roi

Identifier = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")]


class BenchmarkError(ValueError):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Alignment(StrictModel):
    verified: bool = Field(strict=True)
    reference_origin_s: float = Field(allow_inf_nan=False)
    offset_s: float = Field(allow_inf_nan=False)
    evidence_file: str | None = None

    @model_validator(mode="after")
    def evidence_required(self) -> "Alignment":
        if self.verified and not self.evidence_file:
            raise ValueError("Verified alignment requires an evidence record")
        return self


class Session(StrictModel):
    participant_id: Identifier
    session_id: Identifier
    condition: Identifier = "unspecified"
    reference: str
    reference_format: Literal["ubfc_text", "pure_json", "sensor_hr_csv"]
    rgb_csv: str | None = None
    trace_provenance: str | None = None
    video: str | None = None
    alignment: Alignment

    @model_validator(mode="after")
    def exactly_one_input(self) -> "Session":
        if (self.rgb_csv is None) == (self.video is None):
            raise ValueError("Choose exactly one RGB CSV or video input")
        return self


class BenchmarkManifest(StrictModel):
    schema_version: Literal["benchmark-v1"] = "benchmark-v1"
    dataset: Literal["UBFC-rPPG", "PURE", "synthetic"]
    dataset_version: str = Field(min_length=1)
    access_record: str
    access_confirmed: bool = Field(default=False, strict=True)
    protocol_version: str = Field(min_length=1)
    seed: int = Field(default=42, ge=0)
    bootstrap_samples: int = Field(default=1000, ge=100, le=100000)
    reference_max_gap_s: float = Field(default=0.2, gt=0, allow_inf_nan=False)
    roi: Roi = "combined"
    model_path: str | None = None
    splits: dict[Literal["development", "validation", "test"], list[Identifier]]
    sessions: list[Session] = Field(min_length=1)
    signal: SignalConfig = Field(default_factory=SignalConfig)
    methods: MethodConfig = Field(default_factory=MethodConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)

    @model_validator(mode="before")
    @classmethod
    def strict_configs(cls, data: Any) -> Any:
        if isinstance(data, dict):
            data = dict(data)
            for name, config_type in (
                ("signal", SignalConfig),
                ("methods", MethodConfig),
                ("quality", QualityConfig),
            ):
                if isinstance(data.get(name), dict):
                    try:
                        data[name] = config_type(**data[name])
                    except TypeError as exc:
                        raise ValueError("Unknown nested configuration field") from exc
        return data

    @model_validator(mode="after")
    def partitioned(self) -> "BenchmarkManifest":
        if self.dataset != "synthetic":
            if not self.access_confirmed:
                raise ValueError("Real dataset use requires a recorded access confirmation")
            if any(x.rgb_csv and not x.trace_provenance for x in self.sessions):
                raise ValueError("Precomputed real RGB requires provenance evidence")
        participants = [p for group in self.splits.values() for p in group]
        if len(set(participants)) != len(participants):
            raise ValueError("Participant leakage or duplicates in split manifest")
        ids = [(x.participant_id, x.session_id) for x in self.sessions]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate participant/session")
        if not {x.participant_id for x in self.sessions}.issubset(participants):
            raise ValueError("Every session participant must have one explicit split")
        if any(x.video is not None for x in self.sessions) and self.model_path is None:
            raise ValueError("Video processing requires explicit local face model")
        if self.methods.projection_window_s + 2 * self.signal.max_gap_s >= self.signal.window_s / 2:
            raise ValueError("Projection/support margins leave no common spectral interior")
        if self.signal.stride_s > self.quality.max_history_gap_s:
            raise ValueError("History gap must allow configured stride")
        return self


def load_manifest(path: Path) -> BenchmarkManifest:
    return BenchmarkManifest.model_validate_json(path.read_text())


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve(base: Path, value: str) -> Path:
    return (base / value).resolve()


def code_state() -> dict[str, str | bool | None]:
    root = Path(__file__).resolve().parents[1]
    hasher = hashlib.sha256()
    paths = [
        *root.joinpath("packages").rglob("*.py"),
        *root.joinpath("benchmarks").rglob("*.py"),
        root / "pyproject.toml",
        root / "uv.lock",
    ]
    for path in sorted(paths):
        hasher.update(str(path.relative_to(root)).encode())
        hasher.update(path.read_bytes())
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=normal"], cwd=root, text=True
            )
        )
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = None, True
    return {"git_commit": commit, "dirty": dirty, "source_sha256": hasher.hexdigest()}


def snapshot(path: Path) -> dict[str, object]:
    manifest = load_manifest(path)
    base = path.resolve().parent
    if resolve(base, manifest.access_record).stat().st_size == 0:
        raise BenchmarkError("Access record is empty")
    files = {"access_record": digest(resolve(base, manifest.access_record))}
    if manifest.model_path:
        files["face_model"] = digest(resolve(base, manifest.model_path))
    for session in manifest.sessions:
        key = session.participant_id + "/" + session.session_id
        files[key + "/reference"] = digest(resolve(base, session.reference))
        files[key + "/input"] = digest(resolve(base, session.rgb_csv or session.video or ""))
        if session.trace_provenance:
            files[key + "/trace_provenance"] = digest(resolve(base, session.trace_provenance))
        if session.alignment.evidence_file:
            if resolve(base, session.alignment.evidence_file).stat().st_size == 0:
                raise BenchmarkError("Alignment evidence is empty")
            files[key + "/alignment_evidence"] = digest(
                resolve(base, session.alignment.evidence_file)
            )
    return {
        "schema_version": "benchmark-lock-v1",
        "manifest_sha256": digest(path),
        "code": code_state(),
        "inputs": files,
        "environment": {
            "python": platform.python_version(),
            **{
                name: importlib.metadata.version(name)
                for name in ("numpy", "scipy", "av", "mediapipe")
            },
        },
    }


def freeze(path: Path, output: Path) -> None:
    value = snapshot(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as handle:
        handle.write(json.dumps(value, indent=2) + "\n")


def verify_lock(path: Path, lock: Path) -> dict[str, object]:
    expected = json.loads(lock.read_text())
    if not isinstance(expected, dict) or not isinstance(expected.get("code"), dict):
        raise BenchmarkError("Malformed benchmark lock")
    actual = snapshot(path)
    # Dirty status is recorded, but creating an output/lock must not invalidate code identity.
    comparable_expected = json.loads(json.dumps(expected))
    comparable_actual = json.loads(json.dumps(actual))
    comparable_expected.get("code", {}).pop("dirty", None)
    comparable_actual.get("code", {}).pop("dirty", None)
    if comparable_expected != comparable_actual:
        raise BenchmarkError("Frozen manifest/input/code/environment changed; refuse evaluation")
    return actual
