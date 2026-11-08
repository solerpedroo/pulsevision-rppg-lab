import numpy as np
from rppg_types.models import EstimateResult, QualityAssessment, Status

from .config import QualityConfig
from .reasons import ReasonCode


def reject(result: EstimateResult, reason: str, status: Status) -> None:
    result.bpm = None
    result.status = status
    result.reasons = sorted(set([*result.reasons, reason]))
    if result.quality is not None:
        result.quality.passed = False


class EstimateContinuity:
    """One instance per (session, method, ROI); no smoothing or carry-forward."""

    def __init__(self, config: QualityConfig | None = None) -> None:
        self.config = config or QualityConfig()
        self.last_end: float | None = None
        self.key: tuple[str, str] | None = None
        self.baseline: float | None = None
        self.pending: float | None = None
        self.pending_count = 0
        self.recovering = False

    def apply(self, result: EstimateResult) -> EstimateResult:
        output = result.model_copy(deep=True)
        key = (output.method, output.roi)
        if self.key is not None and key != self.key:
            raise ValueError("Continuity cannot mix method/ROI streams")
        self.key = key
        end = output.window.end_s
        if self.last_end is not None:
            if end <= self.last_end:
                raise ValueError("Continuity requires increasing window ends")
            if end - self.last_end > self.config.max_history_gap_s + 1e-9:
                self.baseline = self.pending = None
                self.pending_count = 0
                self.recovering = True
        self.last_end = end
        if output.quality is not None:
            output.quality.evaluated_checks.append("consecutive_windows")
        if output.bpm is None:
            self.baseline = self.pending = None
            self.pending_count = 0
            self.recovering = True
            return output
        candidate = output.bpm
        changed = self.baseline is not None and (
            abs(candidate - self.baseline) > self.config.max_bpm_jump
        )
        if changed or self.recovering:
            if self.pending is not None and (
                abs(candidate - self.pending) <= self.config.confirmation_tolerance_bpm
            ):
                self.pending_count += 1
            else:
                self.pending_count = 1
            self.pending = candidate
            if self.pending_count < self.config.confirmation_windows:
                reject(
                    output,
                    ReasonCode.UNSTABLE_ESTIMATE if changed else (ReasonCode.RECOVERING_SIGNAL),
                    Status.DEGRADED if changed else Status.WARMING_UP,
                )
                return output
        self.baseline = candidate
        self.pending = None
        self.pending_count = 0
        self.recovering = False
        return output


def display_estimate(
    latest: EstimateResult,
    now_s: float,
    config: QualityConfig | None = None,
) -> EstimateResult:
    config = config or QualityConfig()
    if not np.isfinite(now_s) or now_s < latest.produced_at_s:
        raise ValueError("Display time must be finite and at/after result time")
    result = latest.model_copy(deep=True)
    age = now_s - latest.produced_at_s
    result.metadata.update({"estimate_age_s": age, "stale": age > config.max_estimate_age_s})
    if result.quality is None:
        result.quality = QualityAssessment(passed=result.bpm is not None)
    result.quality.evaluated_checks.append("freshness")
    result.quality.metrics["estimate_age_s"] = age
    if age > config.max_estimate_age_s:
        reject(result, ReasonCode.STALE_ESTIMATE, Status.DEGRADED)
    return result
