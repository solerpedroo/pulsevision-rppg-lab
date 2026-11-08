from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray
from rppg_types.models import EstimateResult, Method, Roi, Status, Window

from rppg_core.methods.config import MethodConfig
from rppg_core.methods.registry import get_method
from rppg_core.quality.config import QualityConfig
from rppg_core.quality.continuity import EstimateContinuity
from rppg_core.quality.service import SampleQuality, SignalQualityService, status_for_reason
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.spectrum import bandpass, spectrum
from rppg_core.signals.temporal import (
    SignalInputError,
    SignalQualityError,
    uniform_trace,
    validate_trace,
)

FloatArray = NDArray[np.float64]


@dataclass
class WindowAnalysis:
    estimate: EstimateResult
    timestamps_s: FloatArray = field(default_factory=lambda: np.empty(0))
    signal: FloatArray = field(default_factory=lambda: np.empty(0))
    frequencies_hz: FloatArray = field(default_factory=lambda: np.empty(0))
    power: FloatArray = field(default_factory=lambda: np.empty(0))


def analyze_window(
    timestamps: FloatArray,
    rgb: FloatArray,
    *,
    start_s: float,
    end_s: float,
    roi: Roi = "combined",
    method: Method = "GREEN",
    method_config: MethodConfig | None = None,
    valid: NDArray[np.bool_] | None = None,
    config: SignalConfig | None = None,
    quality_config: QualityConfig | None = None,
    evidence: Sequence[SampleQuality] | None = None,
) -> WindowAnalysis:
    config = config or SignalConfig()
    quality_service = SignalQualityService(quality_config)
    method_config = method_config or MethodConfig()
    extractor = get_method(method)
    if not np.isfinite([start_s, end_s]).all() or not 0 <= start_s < end_s:
        raise SignalInputError("Window bounds must be finite, nonnegative and ordered")
    if len(timestamps) > 1:
        validate_trace(timestamps, rgb)
    elif len(timestamps) == 1:
        if rgb.shape != (1, 3) or not np.isfinite(timestamps[0]) or timestamps[0] < 0:
            raise SignalInputError("Invalid singleton trace")
    elif rgb.shape != (0, 3):
        raise SignalInputError("Empty RGB must have shape (0,3)")
    if evidence is not None and len(evidence) != len(timestamps):
        raise SignalInputError("Evidence must match timestamps")
    if valid is not None and valid.shape != timestamps.shape:
        raise SignalInputError("Validity mask must match timestamps")
    if len(timestamps) and (timestamps[0] < start_s - 1e-9 or timestamps[-1] >= end_s):
        raise SignalInputError("Rows must lie inside the half-open window")
    fps = (
        (len(timestamps) - 1) / float(timestamps[-1] - timestamps[0])
        if len(timestamps) > 1
        else 0.0
    )
    estimate = EstimateResult(
        bpm=None,
        method=method,
        roi=roi,
        status=Status.INSUFFICIENT_DATA,
        reasons=["insufficient_data"],
        window=Window(
            start_s=start_s, end_s=end_s, sample_count=len(timestamps), effective_fps=fps
        ),
        produced_at_s=end_s,
        quality=quality_service.assessment(),
        metadata={
            "mode": "offline_noncausal",
            "filter": "butterworth_sosfiltfilt",
            "method_version": method_config.version,
            "projection_window_s": method_config.projection_window_s,
            "edge_trim_s": config.edge_trim_s,
            "resampled": False,
        },
    )
    result = WindowAnalysis(estimate)
    assessment = estimate.quality
    assert assessment is not None
    try:
        if len(timestamps) < 3:
            raise SignalQualityError("insufficient_data")
        decision = quality_service.samples(evidence, assessment)
        if decision.reasons:
            estimate.status = decision.status
            estimate.reasons = list(decision.reasons)
            return result
        assessment.evaluated_checks.append("source_validity")
        if valid is not None:
            assessment.metrics["valid_sample_fraction"] = float(valid.mean())
        if valid is not None and not valid.all():
            raise SignalQualityError("invalid_roi_samples")
        if 1 / float(np.median(np.diff(timestamps))) / 2 <= config.high_hz:
            raise SignalQualityError("insufficient_nyquist")
        assessment.evaluated_checks.append("timestamp_resampling")
        trace = uniform_trace(
            timestamps,
            rgb,
            max_gap_s=config.max_gap_s,
            max_interval_ratio=config.max_interval_ratio,
        )
        estimate.metadata["resampled"] = trace.resampled
        estimate.metadata["resample_fs"] = trace.fs
        if (
            end_s - start_s < config.window_s - 1e-8
            or timestamps[0] - start_s > 1.5 / trace.fs
            or end_s - timestamps[-1] > 1.5 / trace.fs
        ):
            raise SignalQualityError("window_too_short")
        for decision in (
            quality_service.temporal(timestamps, start_s, end_s, assessment),
            quality_service.illumination(rgb, evidence, assessment),
        ):
            if decision.reasons:
                estimate.status = decision.status
                estimate.reasons = list(decision.reasons)
                return result
        assessment.evaluated_checks.append("method_extraction")
        extracted = extractor(trace.rgb, trace.fs, config, method_config)
        filtered = (
            extracted.values if extracted.filtered else bandpass(extracted.values, trace.fs, config)
        )
        margin = max(config.edge_trim_s, extracted.edge_margin_s)
        estimate.metadata["edge_trim_s"] = margin
        estimate.metadata["filter_placement"] = (
            "projection_components" if extracted.filtered else "after_extraction"
        )
        trim = int(np.ceil(margin * trace.fs - 1e-9))
        if trim * 2 >= len(filtered) or not extracted.valid_mask[trim:-trim].all():
            raise SignalQualityError("insufficient_projection_support")
        cropped = filtered[trim:-trim]
        if len(cropped) < 8:
            raise SignalQualityError("insufficient_interior")
        result.timestamps_s = trace.timestamps_s[trim:-trim]
        result.signal = cropped
        assessment.evaluated_checks.append("spectral_analysis")
        result.frequencies_hz, result.power = spectrum(cropped, trace.fs, config)
        peak_hz, concentration, spacing = quality_service.peak(
            result.frequencies_hz, result.power, config, assessment
        )
        decision = quality_service.spectral(trace.rgb, trace.fs, config, assessment)
        if decision.reasons:
            estimate.status = decision.status
            estimate.reasons = list(decision.reasons)
            return result
        assessment.passed = True
        estimate.bpm = peak_hz * 60
        estimate.status = Status.GOOD
        estimate.reasons = []
        estimate.metadata.update(
            {
                "peak_fraction": concentration,
                "frequency_bin_hz": spacing,
                "bpm_bin_width": 60 * spacing,
                "valid_start_s": float(result.timestamps_s[0]),
                "valid_end_s": float(result.timestamps_s[-1]),
            }
        )
    except SignalQualityError as exc:
        estimate.bpm = None
        estimate.status = status_for_reason(exc.reason)
        estimate.reasons = [exc.reason]
    return result


def analyze_trace(
    timestamps: FloatArray,
    rgb: FloatArray,
    *,
    roi: Roi = "combined",
    method: Method = "GREEN",
    method_config: MethodConfig | None = None,
    valid: NDArray[np.bool_] | None = None,
    config: SignalConfig | None = None,
    quality_config: QualityConfig | None = None,
    evidence: Sequence[SampleQuality] | None = None,
) -> Iterator[WindowAnalysis]:
    validate_trace(timestamps, rgb)
    config = config or SignalConfig()
    quality_service = SignalQualityService(quality_config)
    method_config = method_config or MethodConfig()
    get_method(method)
    if evidence is not None and len(evidence) != len(timestamps):
        raise SignalInputError("Evidence must match timestamps")
    if valid is not None and valid.shape != timestamps.shape:
        raise SignalInputError("Validity mask must match timestamps")
    if config.stride_s > quality_service.config.max_history_gap_s:
        raise SignalInputError("Quality history gap must be at least the configured window stride")
    continuity = EstimateContinuity(quality_service.config)
    start = float(timestamps[0])
    coverage_end = float(timestamps[-1] + np.median(np.diff(timestamps)))
    if coverage_end - start < config.window_s - 1e-8:
        analysis = analyze_window(
            timestamps,
            rgb,
            start_s=start,
            end_s=coverage_end,
            roi=roi,
            method=method,
            method_config=method_config,
            valid=valid,
            config=config,
            quality_config=quality_service.config,
            evidence=evidence,
        )
        analysis.estimate = continuity.apply(analysis.estimate)
        yield analysis
        return
    count = int(np.floor((coverage_end - start - config.window_s + 1e-8) / config.stride_s)) + 1
    for index in range(count):
        left = start + index * config.stride_s
        right = left + config.window_s
        mask = (timestamps >= left - 1e-9) & (timestamps < right - 1e-9)
        analysis = analyze_window(
            timestamps[mask],
            rgb[mask],
            start_s=left,
            end_s=right,
            roi=roi,
            method=method,
            method_config=method_config,
            valid=valid[mask] if valid is not None else None,
            config=config,
            quality_config=quality_service.config,
            evidence=[item for item, keep in zip(evidence, mask, strict=True) if keep]
            if evidence is not None
            else None,
        )

        analysis.estimate = continuity.apply(analysis.estimate)
        yield analysis
