import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from rppg_core.estimation.pipeline import analyze_trace
from rppg_core.methods.config import MethodConfig
from rppg_core.methods.registry import METHOD_REGISTRY, get_method
from rppg_core.signals.compare_methods import export_comparison
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.spectrum import bandpass, select_peak, spectrum
from rppg_core.signals.synthetic import synthetic_rgb
from rppg_core.signals.temporal import SignalInputError, SignalQualityError

REFERENCE = json.loads(Path("tests/fixtures/method_reference_v1.json").read_text())


@pytest.mark.parametrize("method", ["GREEN", "CHROM", "POS"])
def test_numeric_reference_regression(method):
    rgb = np.array(REFERENCE["rgb"])
    config, method_config = SignalConfig(), MethodConfig()
    result = get_method(method)(rgb, REFERENCE["fs"], config, method_config)
    start, end = REFERENCE["comparison_slice"]
    expected = np.array(REFERENCE[method])
    np.testing.assert_allclose(result.values[start:end], expected[start:end], atol=1e-11, rtol=1e-9)
    assert result.valid_mask[start:end].all()
    assert np.isfinite(result.values).all()
    # Same DSP applied to reference and local method: frequency agreement, not physiology.
    if not result.filtered:
        expected = bandpass(expected, 30, config)
    f, power = spectrum(expected[start:end], 30, config)
    reference_peak = select_peak(f, power, config)[0] * 60
    t = np.arange(len(rgb)) / 30
    actual = next(
        analyze_trace(t, rgb, method=method, config=replace(config, edge_trim_s=1.6))
    ).estimate
    assert actual.bpm == pytest.approx(reference_peak, abs=1e-9)


@pytest.mark.parametrize("method", ["GREEN", "CHROM", "POS"])
@pytest.mark.parametrize("bpm", [60, 90, 120])
def test_frequency_and_windows(method, bpm):
    t, rgb = synthetic_rgb(bpm, duration_s=23, noise=0.03)
    results = list(analyze_trace(t, rgb, method=method))
    assert len(results) == 4
    for item in results:
        estimate = item.estimate
        assert estimate.method == method and estimate.bpm is not None, estimate.reasons
        assert abs(estimate.bpm - bpm) <= estimate.metadata["bpm_bin_width"]
        assert estimate.metadata["method_version"] == "classical-v1"


@pytest.mark.parametrize("method", ["GREEN", "CHROM", "POS"])
@pytest.mark.parametrize("case", ["constant", "achromatic", "nan", "zero_channel"])
def test_invalid_method_input_is_finite_or_typed(method, case):
    t, rgb = synthetic_rgb(noise=0)
    if case == "constant":
        rgb[:] = [140, 100, 80]
    if case == "achromatic":
        rgb[:] = 100 + np.sin(2 * np.pi * 1.5 * t)[:, None]
    if case == "nan":
        rgb[100, 0] = np.nan
    if case == "zero_channel":
        rgb[:, 0] = 0
    try:
        result = get_method(method)(rgb, 30, SignalConfig(), MethodConfig())
    except SignalQualityError:
        return
    assert np.isfinite(result.values).all()
    # GREEN legitimately ignores a missing R modulation; other methods must not fake color data.
    assert method == "GREEN" and case in {"zero_channel", "achromatic"}


@pytest.mark.parametrize("method", ["CHROM", "POS"])
def test_bad_roi_abstention_is_preserved(method):
    t, rgb = synthetic_rgb(duration_s=20)
    valid = np.ones(len(t), dtype=bool)
    valid[5] = False
    item = next(analyze_trace(t, rgb, method=method, valid=valid))
    assert item.estimate.bpm is None and item.estimate.reasons == ["invalid_roi_samples"]


def test_projection_boundaries_and_registry():
    _, rgb = synthetic_rgb(duration_s=20)
    pos = get_method("POS")(rgb, 30, SignalConfig(), MethodConfig())
    assert not pos.valid_mask[:47].any()
    assert not pos.valid_mask[-47:].any()
    assert pos.valid_mask[47:-47].all()
    assert set(METHOD_REGISTRY) == {"GREEN", "CHROM", "POS"}
    with pytest.raises(ValueError):
        get_method("unknown")
    with pytest.raises(TypeError):
        METHOD_REGISTRY["unknown"] = None
    assert MethodConfig(**json.loads(Path("configs/methods/classical-v1.json").read_text())) == (
        MethodConfig()
    )
    with pytest.raises(ValueError):
        MethodConfig(version="unknown")


def test_short_projection_and_bad_shape():
    for method in ("CHROM", "POS"):
        with pytest.raises(SignalQualityError):
            get_method(method)(np.full((10, 3), 100.0), 30, SignalConfig(), MethodConfig())
        with pytest.raises(SignalInputError):
            get_method(method)(np.full((10, 2), 100.0), 30, SignalConfig(), MethodConfig())


def test_cli_comparison_with_common_support(tmp_path):
    source = tmp_path / "synthetic.csv"
    subprocess.run(
        [sys.executable, "-m", "rppg_core.signals.synthetic", "--output", str(source)],
        check=True,
        capture_output=True,
    )
    output = tmp_path / "comparison"
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "rppg_core.signals.analyze_rgb",
            str(source),
            "--output",
            str(output),
            "--method",
            "all",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(process.stdout)["methods"] == ["GREEN", "CHROM", "POS"]
    report = json.loads((output / "comparison.json").read_text())
    assert report["input_kind"] == "synthetic"
    assert (output / "comparison.png").read_bytes().startswith(b"\x89PNG")
    rows = report["methods"]
    for method in rows:
        assert rows[method]["eligible_windows"] == 11
        assert rows[method]["accepted_windows"] == 11
    times = [rows[m]["latest_diagnostics"]["timestamps_s"] for m in rows]
    assert times[0] == times[1] == times[2]
    schedules = [
        [(e["window"]["start_s"], e["window"]["end_s"]) for e in rows[m]["estimates"]] for m in rows
    ]
    assert schedules[0] == schedules[1] == schedules[2]
    with pytest.raises(FileExistsError):
        export_comparison(source, output)
