"""Portable, bounded review contract; metrics are derived from eligible window pairs."""

from typing import Annotated, Literal

from pydantic import Field, JsonValue, model_validator

from .models import Contract, Finite, Method, NonNegative, Roi

Hash = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
Name = Annotated[str, Field(min_length=1, max_length=160)]
Positive = Annotated[Finite, Field(gt=0)]


class ReviewSession(Contract):
    participant_id: Name
    session_id: Name
    condition: Name


class ReviewFailure(ReviewSession):
    reason: Name


class ReviewWindow(ReviewSession):
    method: Method
    start_s: NonNegative
    end_s: Positive
    reference_start_s: NonNegative | None
    reference_end_s: Positive | None
    eligible: bool = Field(strict=True)
    exclusion_reason: Name | None
    bpm: Positive | None
    reference_bpm: Positive | None
    reasons: list[Name]

    @model_validator(mode="after")
    def coherent(self) -> "ReviewWindow":
        if self.start_s >= self.end_s:
            raise ValueError("Window must be ordered")
        if self.bpm is None and not self.reasons:
            raise ValueError("Abstention requires reasons")
        if self.eligible:
            if self.exclusion_reason is not None or self.reference_bpm is None:
                raise ValueError("Eligible window requires reference and no exclusion")
            if (
                self.reference_start_s is None
                or self.reference_end_s is None
                or not self.start_s <= self.reference_start_s < self.reference_end_s <= self.end_s
            ):
                raise ValueError("Eligible reference support must lie inside the window")
        elif not self.exclusion_reason:
            raise ValueError("Excluded window requires a cause")
        return self


class ReviewRun(Contract):
    run_id: Name
    experiment: Literal["A", "B", "C", "D", "E", "import"]
    dataset: Literal["synthetic", "UBFC-rPPG", "PURE"]
    result_kind: Literal["synthetic_demonstration", "dataset_evaluation"]
    dataset_version: Name
    protocol_version: Name
    split: Literal["development", "validation", "test"]
    roi: Roi
    window_s: Positive
    seed: int = Field(ge=0)
    bootstrap_samples: int = Field(ge=100)
    source_report: Name
    report_sha256: Hash
    manifest_sha256: Hash
    provenance: dict[str, JsonValue]
    configuration: dict[str, JsonValue]
    sessions: list[ReviewSession] = Field(min_length=1, max_length=10000)
    failures: list[ReviewFailure]
    windows: list[ReviewWindow] = Field(max_length=100000)
    limitations: list[Name | str]

    @model_validator(mode="after")
    def coherent(self) -> "ReviewRun":
        synthetic = self.dataset == "synthetic"
        if synthetic != (self.result_kind == "synthetic_demonstration"):
            raise ValueError("Dataset and result kind disagree")
        if synthetic and self.split == "test":
            raise ValueError("Synthetic data cannot be a physiological test split")
        ids = {(s.participant_id, s.session_id, s.condition) for s in self.sessions}
        if len(ids) != len(self.sessions):
            raise ValueError("Duplicate declared session")
        if any(
            (w.participant_id, w.session_id, w.condition) not in ids
            for w in [*self.windows, *self.failures]
        ):
            raise ValueError("Undeclared session")
        keys = [
            (w.participant_id, w.session_id, w.method, w.start_s, w.end_s) for w in self.windows
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate method/window")
        return self


class BenchmarkReview(Contract):
    schema_version: Literal["benchmark-review-v1"] = "benchmark-review-v1"
    title: Name
    hypothesis: str = Field(min_length=1, max_length=4000)
    runs: list[ReviewRun] = Field(min_length=1, max_length=64)
    pending: list[str]
    limitations: list[str]

    @model_validator(mode="after")
    def coherent(self) -> "BenchmarkReview":
        if len({r.run_id for r in self.runs}) != len(self.runs):
            raise ValueError("Run IDs must be unique")
        if len({r.result_kind for r in self.runs}) != 1:
            raise ValueError("Do not mix artificial and dataset evaluations")
        if sum(len(r.windows) for r in self.runs) > 100000:
            raise ValueError("Review exceeds window limit")
        return self
