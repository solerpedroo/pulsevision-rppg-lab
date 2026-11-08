from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from rppg_types.models import QualityAssessment, Status
from scipy import signal

from rppg_core.signals.config import SignalConfig
from rppg_core.signals.spectrum import select_peak, spectrum
from rppg_core.signals.temporal import FloatArray, SignalInputError

from .config import QualityConfig
from .reasons import ReasonCode


@dataclass(frozen=True)
class SampleQuality:
    landmark_status: str = "ok"
    flags: tuple[str, ...] = ()
    valid_pixel_fraction: float | None = None
    valid_pixels: float | None = None
    motion_score: float | None = None
    dark_fraction: float | None = None
    saturated_fraction: float | None = None
    brightness: float | None = None

    def __post_init__(self) -> None:
        if self.landmark_status not in {"ok", "no_face", "multiple_faces", "unreliable"}:
            raise SignalInputError("Unknown landmark status")
        for key, value in self.__dict__.items():
            if key in {"landmark_status", "flags"} or value is None:
                continue
            if not np.isfinite(value) or value < 0:
                raise SignalInputError("Quality metrics must be finite and nonnegative")
            if key.endswith("fraction") and value > 1:
                raise SignalInputError("Pixel fractions must be in [0,1]")


@dataclass(frozen=True)
class QualityDecision:
    reasons: tuple[str, ...] = ()
    status: Status = Status.UNRELIABLE


class SignalQualityService:
    def __init__(self, config: QualityConfig | None = None) -> None:
        self.config = config or QualityConfig()

    def assessment(self) -> QualityAssessment:
        return QualityAssessment(passed=False)

    def samples(
        self,
        evidence: Sequence[SampleQuality] | None,
        report: QualityAssessment,
    ) -> QualityDecision:
        if evidence is None:
            report.warnings.append("face_and_roi_metrics_not_supplied")
            return QualityDecision()
        report.evaluated_checks.append("face_roi_photometry")
        report.metrics["face_valid_fraction"] = (
            sum(x.landmark_status == "ok" for x in evidence) / len(evidence) if evidence else 0.0
        )
        reasons: set[str] = set()
        mapping = {
            "no_face": "no_face",
            "multiple_faces": "multiple_faces",
            "invalid_geometry": "invalid_geometry",
            "unstable_geometry": "excessive_motion",
            "tracking_gap": "tracking_interrupted",
            "tracking_reset": "tracking_interrupted",
            "temporal_gap": "temporal_gap",
            "partial_roi": "partial_roi",
            "illumination_change": "illumination_change",
            "insufficient_pixels": "insufficient_pixels",
            "low_valid_fraction": "low_valid_fraction",
            "no_valid_roi": "invalid_roi_samples",
        }
        for item in evidence:
            if item.landmark_status == "no_face":
                reasons.add(ReasonCode.NO_FACE)
            elif item.landmark_status == "multiple_faces":
                reasons.add(ReasonCode.MULTIPLE_FACES)
            elif item.landmark_status != "ok":
                reasons.add(ReasonCode.INVALID_ROI_SAMPLES)
            reasons.update(mapping[flag] for flag in item.flags if flag in mapping)
            informational = {"synthetic_reference", "dark_pixels", "saturated_pixels"}
            unknown = set(item.flags) - set(mapping) - informational
            if unknown:
                reasons.add(ReasonCode.UNKNOWN_QUALITY_FLAG)
                report.warnings.extend(
                    "unrecognized_source_flag:" + flag
                    for flag in sorted(unknown)
                    if "unrecognized_source_flag:" + flag not in report.warnings
                )
            if item.valid_pixel_fraction is not None and (
                item.valid_pixel_fraction < self.config.min_pixel_fraction
            ):
                reasons.add(ReasonCode.LOW_VALID_FRACTION)
            if item.valid_pixels is not None and item.valid_pixels < self.config.min_pixels:
                reasons.add(ReasonCode.INSUFFICIENT_PIXELS)
            if item.motion_score is not None and item.motion_score > self.config.max_motion:
                reasons.add(ReasonCode.EXCESSIVE_MOTION)
            if (
                item.dark_fraction is not None
                and item.dark_fraction > self.config.max_dark_fraction
            ):
                reasons.add(ReasonCode.DARK_ROI)
            if item.saturated_fraction is not None and (
                item.saturated_fraction > self.config.max_saturated_fraction
            ):
                reasons.add(ReasonCode.SATURATED_ROI)
        for field in (
            "valid_pixel_fraction",
            "valid_pixels",
            "motion_score",
            "dark_fraction",
            "saturated_fraction",
        ):
            values = [getattr(item, field) for item in evidence if getattr(item, field) is not None]
            report.metrics[field + "_availability"] = (
                len(values) / len(evidence) if evidence else 0.0
            )
            if values:
                report.metrics[field + "_min"] = float(min(values))
                report.metrics[field + "_max"] = float(max(values))
        status = (
            Status.NO_FACE
            if evidence and all(x.landmark_status == "no_face" for x in evidence)
            else Status.UNRELIABLE
        )
        return QualityDecision(tuple(sorted(reasons)), status)

    def temporal(
        self,
        timestamps: FloatArray,
        start_s: float,
        end_s: float,
        report: QualityAssessment,
    ) -> QualityDecision:
        intervals = np.diff(timestamps)
        median = float(np.median(intervals))
        cv = float(intervals.std() / intervals.mean())
        coverage = min(1.0, len(timestamps) * median / (end_s - start_s))
        report.evaluated_checks.append("sampling_integrity")
        report.metrics.update({"interval_cv": cv, "temporal_coverage": coverage})
        reasons = []
        if cv > self.config.max_interval_cv:
            reasons.append(ReasonCode.IRREGULAR_SAMPLING)
        if coverage < self.config.min_temporal_coverage:
            reasons.append(ReasonCode.LOW_TEMPORAL_COVERAGE)
        return QualityDecision(tuple(reasons))

    def illumination(
        self,
        rgb: FloatArray,
        evidence: Sequence[SampleQuality] | None,
        report: QualityAssessment,
    ) -> QualityDecision:
        use_measured = evidence is not None and all(x.brightness is not None for x in evidence)
        brightness = (
            np.array([x.brightness for x in evidence], dtype=float)
            if use_measured and evidence is not None
            else rgb.mean(axis=1)
        )
        report.evaluated_checks.append("illumination_stability")
        if not use_measured:
            report.warnings.append("illumination_uses_rgb_mean_proxy")
        mean = float(brightness.mean())
        cv = float(brightness.std() / max(mean, 1e-9))
        step = float(np.max(np.abs(np.diff(brightness)) / np.maximum(brightness[:-1], 1.0)))
        report.metrics.update({"illumination_cv": cv, "brightness_max_relative_step": step})
        reasons = []
        if step > self.config.max_brightness_step:
            reasons.append(ReasonCode.ILLUMINATION_CHANGE)
        if cv > self.config.max_illumination_cv:
            reasons.append(ReasonCode.ILLUMINATION_INSTABILITY)
        saturated = float(np.mean(rgb.max(axis=1) >= self.config.saturated_channel_threshold))
        dark = float(np.mean(rgb.mean(axis=1) < self.config.dark_brightness_threshold))
        report.metrics.update(
            {"saturated_rgb_sample_fraction": saturated, "dark_rgb_sample_fraction": dark}
        )
        if saturated > self.config.max_saturated_fraction:
            reasons.append(ReasonCode.SATURATED_ROI)
        if dark > self.config.max_dark_fraction:
            reasons.append(ReasonCode.DARK_ROI)
        return QualityDecision(tuple(reasons))

    def peak(
        self,
        frequencies: FloatArray,
        power: FloatArray,
        config: SignalConfig,
        report: QualityAssessment,
    ) -> tuple[float, float, float]:
        report.evaluated_checks.append("filtered_peak_structure")
        diagnostics: dict[str, float] = {}
        try:
            return select_peak(frequencies, power, config, diagnostics=diagnostics)
        finally:
            report.metrics.update(diagnostics)

    def spectral(
        self,
        uniform_rgb: FloatArray,
        fs: float,
        config: SignalConfig,
        report: QualityAssessment,
    ) -> QualityDecision:
        # Unfiltered G, common to all methods. A heuristic nuisance-energy gate.
        green = uniform_rgb[:, 1]
        centered = signal.detrend(green / float(green.mean()) - 1, type="linear")
        f, power = spectrum(np.asarray(centered, dtype=np.float64), fs, config)
        total = float(power[f > 0].sum())
        band = float(power[(f >= config.low_hz) & (f <= config.high_hz)].sum())
        fraction = band / total if total > 0 else 0.0
        report.evaluated_checks.append("unfiltered_band_energy")
        report.metrics["band_energy_fraction"] = fraction
        return QualityDecision(
            (ReasonCode.LOW_BAND_ENERGY,)
            if (fraction < self.config.min_band_energy_fraction)
            else ()
        )


def status_for_reason(reason: str) -> Status:
    return (
        Status.INSUFFICIENT_DATA
        if reason
        in {
            "insufficient_data",
            "window_too_short",
            "filter_window_too_short",
            "insufficient_interior",
            "projection_window_too_short",
            "insufficient_projection_support",
            "insufficient_spectral_resolution",
        }
        else Status.UNRELIABLE
    )
