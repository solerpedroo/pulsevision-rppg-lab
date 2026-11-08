import csv
import json

import numpy as np
import pytest
from pydantic import ValidationError
from rppg_core.estimation.pipeline import analyze_trace, analyze_window
from rppg_core.quality.config import QualityConfig, load_quality_config
from rppg_core.quality.continuity import EstimateContinuity, display_estimate
from rppg_core.quality.reasons import ReasonCode
from rppg_core.quality.service import SampleQuality
from rppg_core.quality.summary import summarize_quality
from rppg_core.signals.analyze_rgb import export_analysis, load_trace_csv
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.synthetic import synthetic_rgb
from rppg_types.models import EstimateResult, QualityAssessment, Status, Window


def estimate(bpm=90.0, end=20.0, *, reason="no_face", status=Status.NO_FACE):
    return EstimateResult(
        bpm=bpm,
        method="GREEN",
        roi="combined",
        status=Status.GOOD if bpm is not None else status,
        reasons=[] if bpm is not None else [reason],
        window=Window(start_s=end - 20, end_s=end, sample_count=600, effective_fps=30),
        produced_at_s=end,
        quality=QualityAssessment(passed=bpm is not None),
    )


@pytest.mark.parametrize(
    "case,reason",
    [
        ({"landmark_status": "no_face"}, "no_face"),
        ({"landmark_status": "multiple_faces"}, "multiple_faces"),
        ({"valid_pixel_fraction": 0.2}, "low_valid_fraction"),
        ({"valid_pixels": 10}, "insufficient_pixels"),
        ({"motion_score": 0.3}, "excessive_motion"),
        ({"saturated_fraction": 0.7}, "saturated_roi"),
        ({"dark_fraction": 0.8}, "dark_roi"),
        ({"flags": ("partial_roi",)}, "partial_roi"),
        ({"flags": ("tracking_reset",)}, "tracking_interrupted"),
        ({"flags": ("invalid_geometry",)}, "invalid_geometry"),
    ],
)
def test_source_evidence_blocks_estimate_with_specific_reason(case, reason):
    t, rgb = synthetic_rgb(duration_s=20)
    evidence = [SampleQuality(**case)] * len(t)
    result = analyze_window(t, rgb, start_s=0, end_s=20, evidence=evidence).estimate
    assert result.bpm is None and reason in result.reasons
    assert result.quality is not None and not result.quality.passed
    EstimateResult.model_validate(result.model_dump())
    if reason == "no_face":
        assert result.status == Status.NO_FACE


@pytest.mark.parametrize("method", ["GREEN", "CHROM", "POS"])
@pytest.mark.parametrize("artifact", ["flicker", "saturation", "dark", "out_of_band", "irregular"])
def test_adversarial_rgb_is_not_reported_as_bpm(method, artifact):
    t, rgb = synthetic_rgb(duration_s=20, noise=0)
    if artifact == "flicker":
        rgb *= (1 + 0.4 * np.sin(2 * np.pi * 1.2 * t))[:, None]
    if artifact == "saturation":
        rgb = 249 + np.sin(2 * np.pi * 1.5 * t)[:, None] * np.ones((1, 3))
    if artifact == "dark":
        rgb *= 0.1
    if artifact == "out_of_band":
        rgb[:, 1] += 10 * np.sin(2 * np.pi * 6 * t)
    if artifact == "irregular":
        # No long gap; repeated short timing jitter is nonetheless excessive.
        intervals = np.resize([0.018, 0.048], len(t) - 1)
        t = np.r_[0, np.cumsum(intervals)]
    item = analyze_window(t, rgb, method=method, start_s=0, end_s=20)
    assert item.estimate.bpm is None, artifact
    assert set(item.estimate.reasons).issubset({x.value for x in ReasonCode})


def test_valid_quality_audit_is_instrumental_not_probability():
    t, rgb = synthetic_rgb(duration_s=20)
    item = analyze_window(t, rgb, start_s=0, end_s=20).estimate
    assert item.bpm is not None and item.quality.passed
    assert item.quality.metrics["band_energy_fraction"] > 0.5
    assert "face_and_roi_metrics_not_supplied" in item.quality.warnings
    assert "illumination_uses_rgb_mean_proxy" in item.quality.warnings
    assert "consecutive_windows" not in item.quality.evaluated_checks
    assert "confidence" not in item.model_dump_json().lower()


def test_multiple_failures_remain_auditable():
    t, rgb = synthetic_rgb(duration_s=20)
    source = SampleQuality(
        landmark_status="multiple_faces", motion_score=0.3, saturated_fraction=0.8
    )
    result = analyze_window(t, rgb, start_s=0, end_s=20, evidence=[source] * len(t)).estimate
    assert set(result.reasons) == {"multiple_faces", "excessive_motion", "saturated_roi"}
    assert result.quality.metrics["motion_score_max"] == 0.3


def test_low_temporal_coverage():
    t, rgb = synthetic_rgb(duration_s=20)
    keep = np.arange(len(t)) % 10 != 5
    result = analyze_window(
        t[keep],
        rgb[keep],
        start_s=0,
        end_s=20,
        quality_config=QualityConfig(max_interval_cv=1, min_temporal_coverage=0.99),
    ).estimate
    assert result.bpm is None and "low_temporal_coverage" in result.reasons


def test_continuity_suppresses_jump_without_carrying_previous_bpm():
    stream = EstimateContinuity()
    first = stream.apply(estimate())
    second = stream.apply(estimate(125, 21))
    third = stream.apply(estimate(126, 22))
    assert first.bpm == 90
    assert second.bpm is None and second.status == Status.DEGRADED
    assert second.reasons == ["unstable_between_windows"]
    assert third.bpm == 126  # Confirmed candidate, no averaging with old value.
    assert first.bpm == 90  # Earlier result not mutated.
    EstimateResult.model_validate(second.model_dump())


def test_recovery_after_failure_and_history_gap():
    stream = EstimateContinuity()
    assert stream.apply(estimate()).bpm is not None
    failed = stream.apply(estimate(None, 21))
    assert failed.bpm is None and failed.reasons == ["no_face"]
    warm = stream.apply(estimate(90, 22))
    assert warm.bpm is None and warm.status == Status.WARMING_UP
    assert stream.apply(estimate(91, 23)).bpm == 91
    assert stream.apply(estimate(92, 30)).bpm is None  # History expired.


def test_continuity_does_not_accept_alternating_candidates():
    stream = EstimateContinuity()
    stream.apply(estimate())
    for index, bpm in enumerate([130, 160, 130, 160], start=21):
        assert stream.apply(estimate(bpm, index)).bpm is None


def test_continuity_requires_separate_ordered_streams():
    stream = EstimateContinuity()
    stream.apply(estimate())
    with pytest.raises(ValueError):
        stream.apply(estimate())
    mixed = estimate(90, 21)
    mixed.method = "POS"
    with pytest.raises(ValueError):
        stream.apply(mixed)


def test_stale_display_never_reuses_an_old_bpm():
    source = estimate()
    assert display_estimate(source, 23).bpm == 90  # Inclusive max age.
    stale = display_estimate(source, 23.001)
    assert stale.bpm is None and stale.status == Status.DEGRADED
    assert stale.reasons == ["stale_estimate"] and stale.metadata["stale"]
    assert source.bpm == 90
    EstimateResult.model_validate(stale.model_dump())
    failed = estimate(None, 21)
    assert display_estimate(failed, 21).bpm is None
    with pytest.raises(ValueError):
        display_estimate(source, 19)
    with pytest.raises(ValueError):
        display_estimate(source, float("nan"))


def test_coverage_counts_every_eligible_window_and_reason():
    stream = EstimateContinuity()
    results = [
        stream.apply(estimate()),
        stream.apply(estimate(None, 21)),
        stream.apply(estimate(90, 22)),
        stream.apply(estimate(90, 23)),
    ]
    summary = summarize_quality(results)
    assert (summary.eligible_windows, summary.accepted_windows, summary.abstained_windows) == (
        4,
        2,
        2,
    )
    assert summary.coverage == 0.5
    assert summary.reason_counts == {"no_face": 1, "recovering_signal": 1}
    assert summarize_quality([]).coverage is None


def test_quality_and_bpm_must_agree():
    value = estimate().model_dump()
    value["quality"]["passed"] = False
    with pytest.raises(ValidationError):
        EstimateResult.model_validate(value)


def test_csv_statistics_and_reasons_survive_to_export(tmp_path):
    t, rgb = synthetic_rgb(duration_s=25)
    source = tmp_path / "source.csv"
    fields = [
        "timestamp_s",
        "roi",
        "r_mean",
        "g_mean",
        "b_mean",
        "landmark_status",
        "quality_flags",
        "motion_score",
        "valid_pixel_fraction",
        "valid_pixels",
        "saturated_fraction",
        "dark_fraction",
        "brightness",
    ]
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(fields)
        for timestamp, color in zip(t, rgb, strict=True):
            # A source motion artifact at t=0 blocks the first window only.
            motion = 0.5 if timestamp == 0 else 0.01
            writer.writerow(
                [timestamp, "combined", *color, "ok", "[]", motion, 0.9, 100, 0, 0, color.mean()]
            )
    loaded = load_trace_csv(source, "combined")
    assert loaded.evidence[0].motion_score == 0.5
    output = tmp_path / "analysis"
    report = export_analysis(source, output)
    reasons = [row["reasons"] for row in report["estimates"]]
    assert reasons[0] == ["excessive_motion"]
    assert reasons[1] == ["recovering_signal"]
    summary = report["quality_summary"]
    assert summary["eligible_windows"] == 6 and summary["accepted_windows"] == 4
    assert summary["coverage"] == pytest.approx(4 / 6)
    assert report["estimates"][0]["quality"]["metrics"]["motion_score_max"] == 0.5
    assert (
        json.loads((output / "estimates.json").read_text())["quality_config"]["version"]
        == "quality-v1"
    )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"version": "unknown"},
        {"max_motion": -1},
        {"max_interval_cv": float("inf")},
        {"confirmation_windows": 1.5},
        {"min_pixel_fraction": 2},
    ],
)
def test_invalid_quality_config(kwargs):
    with pytest.raises(ValueError):
        QualityConfig(**kwargs)


def test_versioned_config():
    from pathlib import Path

    assert load_quality_config(Path("configs/quality/quality-v1.json")) == QualityConfig()


def test_cli_honors_quality_config_for_single_method(tmp_path):
    import subprocess
    import sys
    from dataclasses import asdict

    source = tmp_path / "synthetic.csv"
    subprocess.run(
        [sys.executable, "-m", "rppg_core.signals.synthetic", "--output", str(source)],
        check=True,
        capture_output=True,
    )
    policy = tmp_path / "quality.json"
    policy.write_text(json.dumps(asdict(QualityConfig(max_illumination_cv=1e-8))))
    output = tmp_path / "results"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "rppg_core.signals.analyze_rgb",
            str(source),
            "--quality-config",
            str(policy),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(process.stdout)["accepted_windows"] == 0
    report = json.loads((output / "estimates.json").read_text())
    assert report["quality_config"]["max_illumination_cv"] == 1e-8
    assert report["quality_summary"]["reason_counts"]["illumination_instability"] == 11


def test_unknown_source_flag_is_not_silently_accepted():
    t, rgb = synthetic_rgb(duration_s=20)
    evidence = [SampleQuality(flags=("occlusion_flag_not_supported",))] * len(t)
    result = analyze_window(t, rgb, start_s=0, end_s=20, evidence=evidence).estimate
    assert result.bpm is None and result.reasons == ["unknown_quality_flag"]


def test_malformed_optional_metrics_are_rejected(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "timestamp_s,roi,r_mean,g_mean,b_mean,landmark_status,quality_flags,motion_score\n"
        "0,combined,140,100,80,ok,[],nan\n"
    )
    with pytest.raises(ValueError):
        load_trace_csv(path, "combined")


def test_failed_spectral_gate_keeps_measured_diagnostics():
    t, rgb = synthetic_rgb(duration_s=20, noise=0, bpm=60, harmonic_amplitude=1)
    result = analyze_window(t, rgb, start_s=0, end_s=20).estimate
    assert result.bpm is None and result.reasons == ["ambiguous_peaks"]
    assert result.quality.metrics["competing_peak_ratio"] > SignalConfig().max_competing_peak_ratio


def test_history_expiry_must_allow_configured_stride():
    t, rgb = synthetic_rgb()
    with pytest.raises(ValueError):
        list(analyze_trace(t, rgb, config=SignalConfig(stride_s=5)))
