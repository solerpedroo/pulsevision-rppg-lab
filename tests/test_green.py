import json
import subprocess
import sys

import numpy as np
import pytest
from rppg_core.estimation.green_pipeline import analyze_trace, analyze_window
from rppg_core.signals.analyze_rgb import export_analysis, load_csv
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.spectrum import bandpass
from rppg_core.signals.synthetic import synthetic_rgb
from rppg_core.signals.temporal import SignalInputError, uniform_trace
from rppg_types.models import EstimateResult
from scipy import signal


@pytest.mark.parametrize("bpm", [60, 73, 90, 120, 150])
@pytest.mark.parametrize("noise", [0, 0.2, 0.5])
def test_known_frequencies(bpm, noise):
    t, rgb = synthetic_rgb(bpm, duration_s=30, noise=noise)
    analyses = list(analyze_trace(t, rgb))
    assert len(analyses) == 11
    for item in analyses:
        assert item.estimate.bpm is not None, item.estimate.reasons
        assert abs(item.estimate.bpm - bpm) <= item.estimate.metadata["bpm_bin_width"]
        EstimateResult.model_validate(item.estimate.model_dump())
        assert item.estimate.metadata["mode"] == "offline_noncausal"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("constant", "constant_signal"),
        ("nan", "nonfinite_rgb"),
        ("infinity", "nonfinite_rgb"),
        ("gap", "temporal_gap"),
        ("short", "window_too_short"),
        ("nyquist", "insufficient_nyquist"),
        ("invalid_roi", "invalid_roi_samples"),
        ("outside_range", "rgb_out_of_range"),
        ("trend", "constant_signal"),
    ],
)
def test_abstention(case, reason):
    fs = 5 if case == "nyquist" else 30
    t, rgb = synthetic_rgb(duration_s=20, fs=fs)
    valid = np.ones(len(t), dtype=bool)
    if case == "constant":
        rgb[:] = [140, 100, 80]
    if case == "trend":
        rgb[:, 1] = 100 + t
    if case == "nan":
        rgb[100, 1] = np.nan
    if case == "infinity":
        rgb[100, 1] = np.inf
    if case == "outside_range":
        rgb[100, 1] = 256
    if case == "invalid_roi":
        valid[100] = False
    if case == "gap":
        keep = (t < 5) | (t > 5.5)
        t, rgb, valid = t[keep], rgb[keep], valid[keep]
    end = 20
    if case == "short":
        t, rgb, valid = t[:90], rgb[:90], valid[:90]
        end = 3
    item = analyze_window(t, rgb, valid=valid, start_s=0, end_s=end)
    assert item.estimate.bpm is None
    assert item.estimate.reasons == [reason]
    EstimateResult.model_validate(item.estimate.model_dump())


def test_resampling_preserves_frequency_and_does_not_extrapolate():
    t, rgb = synthetic_rgb(duration_s=30)
    jitter = 0.003 * np.sin(np.arange(len(t)))
    t += jitter
    trace = uniform_trace(t, rgb, max_gap_s=0.15, max_interval_ratio=2.5)
    assert trace.resampled
    assert trace.timestamps_s[0] >= t[0] and trace.timestamps_s[-1] <= t[-1]
    for item in analyze_trace(t, rgb):
        assert item.estimate.bpm == pytest.approx(90, abs=4)


@pytest.mark.parametrize("case", ["duplicate", "reverse", "nan", "negative", "shape"])
def test_malformed_trace(case):
    t, rgb = synthetic_rgb()
    if case == "duplicate":
        t[10] = t[9]
    if case == "reverse":
        t[10] = t[9] - 0.01
    if case == "nan":
        t[10] = np.nan
    if case == "negative":
        t[0] = -1
    if case == "shape":
        rgb = rgb[:, :2]
    with pytest.raises(SignalInputError):
        list(analyze_trace(t, rgb))


def test_noise_and_competing_harmonic():
    t, rgb = synthetic_rgb(60, duration_s=20, noise=0, harmonic_amplitude=1)
    result = next(analyze_trace(t, rgb)).estimate
    assert result.bpm is None and result.reasons == ["ambiguous_peaks"]
    rgb = 100 + np.random.default_rng(5).normal(0, 1, rgb.shape)
    result = next(analyze_trace(t, rgb)).estimate
    assert result.bpm is None and result.reasons == ["diffuse_spectrum"]


def test_weak_harmonic_keeps_fundamental():
    t, rgb = synthetic_rgb(60, duration_s=20, harmonic_amplitude=0.2)
    assert next(analyze_trace(t, rgb)).estimate.bpm == pytest.approx(60, abs=4)


def test_filter_rejects_out_of_band_and_is_finite():
    fs = 30
    t = np.arange(1800) / fs
    config = SignalConfig()
    values = np.sin(2 * np.pi * 1.5 * t) + np.sin(2 * np.pi * 6 * t)
    filtered = bandpass(values, fs, config)
    assert np.isfinite(filtered).all()
    f, p = signal.periodogram(filtered[60:-60], fs=fs)
    assert p[np.argmin(abs(f - 1.5))] > 1000 * p[np.argmin(abs(f - 6))]


def test_gaps_do_not_poison_later_windows():
    t, rgb = synthetic_rgb(duration_s=45)
    valid = np.ones(len(t), dtype=bool)
    valid[(t > 5) & (t < 6)] = False
    results = list(analyze_trace(t, rgb, valid=valid))
    assert results[0].estimate.bpm is None
    assert results[-1].estimate.bpm == pytest.approx(90, abs=4)


def test_cli_synthetic_report_and_png(tmp_path):
    source = tmp_path / "synthetic.csv"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "rppg_core.signals.synthetic",
            "--output",
            str(source),
            "--bpm",
            "90",
        ],
        check=True,
        capture_output=True,
    )
    target = tmp_path / "analysis"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "rppg_core.signals.analyze_rgb",
            str(source),
            "--output",
            str(target),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(process.stdout)["accepted_windows"] == 11
    report = json.loads((target / "estimates.json").read_text())
    assert report["input_kind"] == "synthetic"
    assert (target / "green_diagnostics.png").read_bytes().startswith(b"\x89PNG")
    with pytest.raises(FileExistsError):
        export_analysis(source, target)


def test_csv_preserves_missing_rgb_and_tracking_reset(tmp_path):
    path = tmp_path / "rgb.csv"
    path.write_text(
        "timestamp_s,roi,r_mean,g_mean,b_mean,landmark_status,quality_flags\n"
        "0,combined,140,100,80,ok,[]\n"
        "0.04,combined,,,,no_face,[]\n"
        '0.08,combined,140,100,80,ok,"[""tracking_reset""]"\n'
    )
    t, rgb, valid = load_csv(path, "combined")
    assert len(t) == 3 and np.isnan(rgb[1]).all()
    assert valid.tolist() == [True, False, False]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"high_hz": 0.5},
        {"window_s": 1},
        {"stride_s": 0},
        {"filter_order": 2.5},
        {"max_gap_s": float("nan")},
    ],
)
def test_invalid_config(kwargs):
    with pytest.raises(ValueError):
        SignalConfig(**kwargs)


@pytest.mark.parametrize("count", [0, 1])
def test_empty_or_singleton_window_abstains(count):
    timestamps = np.arange(count, dtype=float)
    rgb = np.full((count, 3), 100.0)
    item = analyze_window(timestamps, rgb, start_s=0, end_s=20)
    assert item.estimate.bpm is None
    assert item.estimate.reasons == ["insufficient_data"]


def test_green_uses_green_channel():
    t, rgb = synthetic_rgb(90, duration_s=20, noise=0)
    rgb[:, 0] = 140 + 10 * np.sin(2 * np.pi * 2.3 * t)
    rgb[:, 2] = 80 + 10 * np.sin(2 * np.pi * 2.7 * t)
    assert next(analyze_trace(t, rgb)).estimate.bpm == pytest.approx(90, abs=4)
