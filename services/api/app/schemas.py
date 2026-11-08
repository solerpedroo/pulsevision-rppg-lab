from typing import Any, Literal

from pydantic import BaseModel, Field
from rppg_types.models import EstimateResult, Method, Roi

JobStatus = Literal["queued", "processing", "completed", "failed", "cancelled", "expired"]


class Job(BaseModel):
    id: str
    status: JobStatus
    method: Method
    roi: Roi
    progress: float = Field(ge=0, le=1)
    created_at: float
    updated_at: float
    expires_at: float
    error: str | None = None


class EstimatePage(BaseModel):
    job_id: str
    total: int
    offset: int
    limit: int
    items: list[EstimateResult]
    summary: dict[str, Any]


class SignalPage(BaseModel):
    job_id: str
    total: int
    offset: int
    stride: int
    points: list[dict[str, Any]]
