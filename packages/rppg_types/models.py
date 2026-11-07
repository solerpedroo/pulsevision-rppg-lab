from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Finite = Annotated[float, Field(allow_inf_nan=False)]
NonNegative = Annotated[Finite, Field(ge=0)]
Fraction = Annotated[Finite, Field(ge=0, le=1)]
Channel = Annotated[Finite, Field(ge=0, le=255)]
Method = Literal["GREEN", "CHROM", "POS"]
Roi = Literal["forehead", "left_cheek", "right_cheek", "combined"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Status(StrEnum):
    WARMING_UP = "warming_up"
    GOOD = "good"
    DEGRADED = "degraded"
    UNRELIABLE = "unreliable"
    NO_FACE = "no_face"
    INSUFFICIENT_DATA = "insufficient_data"
    UNSUPPORTED_VIDEO = "unsupported_video"


class RGBSample(Contract):
    timestamp_s: NonNegative
    roi: Roi
    rgb_mean: Annotated[list[Channel], Field(min_length=3, max_length=3)]
    valid_pixel_fraction: Fraction
    landmark_status: Literal["ok", "no_face", "multiple_faces", "unreliable"]
    motion_score: NonNegative
    quality_flags: list[str] = Field(default_factory=list)


class Window(Contract):
    start_s: NonNegative
    end_s: NonNegative
    sample_count: int = Field(ge=0)
    effective_fps: NonNegative

    @model_validator(mode="after")
    def ordered(self) -> "Window":
        if self.end_s <= self.start_s:
            raise ValueError("end_s must be greater than start_s")
        return self


class EstimateResult(Contract):
    schema_version: Literal["1.0"] = "1.0"
    bpm: Annotated[Finite, Field(gt=0)] | None
    method: Method
    roi: Roi
    status: Status
    reasons: list[str]
    window: Window
    produced_at_s: NonNegative
    metadata: dict[str, str | float | int | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def consistent(self) -> "EstimateResult":
        if self.bpm is not None and self.status != Status.GOOD:
            raise ValueError("BPM requires good status")
        if self.bpm is None and not self.reasons:
            raise ValueError("Abstention requires a reason")
        if self.status == Status.GOOD and self.bpm is None:
            raise ValueError("Good status requires BPM")
        if self.produced_at_s < self.window.end_s:
            raise ValueError("Result cannot precede its window")
        return self


class Experiment(Contract):
    schema_version: Literal["1.0"] = "1.0"
    experiment_id: str = Field(min_length=1)
    protocol_version: str = Field(min_length=1)
    seed: int = Field(ge=0)
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    dataset_version: str = Field(min_length=1)
    participant_split: dict[str, list[str]]
    methods: list[Method] = Field(min_length=1)
    parameters: dict[str, str | float | int | bool]
    environment: dict[str, str]
