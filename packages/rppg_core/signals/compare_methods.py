"""Matched-window comparison, not a benchmark against physiological reference."""

import hashlib
import json
import shutil
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from rppg_types.models import Method, Roi

from rppg_core.estimation.pipeline import WindowAnalysis, analyze_trace
from rppg_core.methods.config import MethodConfig
from rppg_core.quality.config import QualityConfig
from rppg_core.quality.summary import summarize_quality

from .analyze_rgb import load_trace_csv
from .config import SignalConfig
from .temporal import validate_trace

METHODS: tuple[Method, ...] = ("GREEN", "CHROM", "POS")


def save_comparison_plot(
    analyses: dict[Method, list[WindowAnalysis]],
    path: Path,
    *,
    synthetic: bool,
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=(11, 12), layout="constrained")
    grid = figure.add_gridspec(4, 2)
    figure.suptitle(
        "Artificial RGB — method comparison"
        if synthetic
        else "Experimental offline method comparison"
    )
    for row, (method, windows) in enumerate(analyses.items()):
        latest = windows[-1]
        left, right = figure.add_subplot(grid[row, 0]), figure.add_subplot(grid[row, 1])
        left.plot(latest.timestamps_s, latest.signal)
        left.set(
            title=method + " — latest window",
            xlabel="Session time (s)",
            ylabel="Amplitude (a.u.)",
        )
        right.plot(latest.frequencies_hz, latest.power)
        right.set(
            title="Welch PSD",
            xlabel="Frequency (Hz)",
            ylabel="PSD (a.u.²/Hz)",
            xlim=(0, 4),
        )
        if latest.estimate.bpm is None:
            left.text(
                0.02,
                0.9,
                "No estimate: " + ", ".join(latest.estimate.reasons),
                transform=left.transAxes,
            )
    axis = figure.add_subplot(grid[3, :])
    for method, windows in analyses.items():
        axis.plot(
            [w.estimate.window.end_s for w in windows],
            [w.estimate.bpm if w.estimate.bpm is not None else np.nan for w in windows],
            marker=".",
            label=method,
        )
    axis.set(
        title="Accepted estimates; gaps preserve abstention",
        xlabel="Window end, session time (s)",
        ylabel="Estimated BPM",
    )
    axis.ticklabel_format(axis="y", style="plain", useOffset=False)
    accepted = [w.estimate.bpm for windows in analyses.values() for w in windows
                if w.estimate.bpm is not None]
    if accepted:
        axis.set_ylim(min(accepted)-3, max(accepted)+3)
    else:
        axis.set_yticks([])
        axis.text(.5, .5, "No accepted estimates", transform=axis.transAxes,
                  ha="center", va="center")
    axis.legend()
    figure.savefig(path, dpi=140)
    plt.close(figure)


def export_comparison(
    source: Path,
    output: Path,
    *,
    roi: Roi = "combined",
    config: SignalConfig | None = None,
    method_config: MethodConfig | None = None,
    quality_config: QualityConfig | None = None,
) -> dict[str, Any]:
    config = config or SignalConfig()
    method_config = method_config or MethodConfig()
    quality_config = quality_config or QualityConfig()
    trace = load_trace_csv(source, roi)
    timestamps, rgb, valid = trace.timestamps, trace.rgb, trace.valid
    validate_trace(timestamps, rgb)
    # Extra two input intervals cover ceil/even rounding of CHROM projection length.
    margin = max(
        config.edge_trim_s,
        method_config.projection_window_s
        + 2 * min(config.max_gap_s, float(np.diff(timestamps).max())),
    )
    common = replace(config, edge_trim_s=margin)
    analyses = {
        method: list(
            analyze_trace(
                timestamps,
                rgb,
                method=method,
                roi=roi,
                valid=valid,
                config=common,
                method_config=method_config,
                quality_config=quality_config,
                evidence=trace.evidence,
            )
        )
        for method in METHODS
    }
    # Input kind is declared by CSV, not independent source verification.
    import csv

    with source.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["roi"] == roi]
        synthetic = bool(rows) and all(
            "synthetic_reference" in json.loads(row["quality_flags"]) for row in rows
        )
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "input_kind": "synthetic" if synthetic else "unverified_rgb_trace",
        "roi": roi,
        "signal_config": asdict(common),
        "method_config": asdict(method_config),
        "quality_config": asdict(quality_config),
        "environment": {"numpy": np.__version__, "scipy": scipy.__version__},
        "methods": {},
    }
    for method, windows in analyses.items():
        latest = windows[-1]
        report["methods"][method] = {
            "quality_summary": summarize_quality([w.estimate for w in windows]).as_dict(),
            "eligible_windows": len(windows),
            "coverage": sum(w.estimate.bpm is not None for w in windows) / len(windows),
            "accepted_windows": sum(w.estimate.bpm is not None for w in windows),
            "estimates": [w.estimate.model_dump(mode="json") for w in windows],
            "latest_diagnostics": {
                "timestamps_s": latest.timestamps_s.tolist(),
                "signal": latest.signal.tolist(),
                "frequencies_hz": latest.frequencies_hz.tolist(),
                "power": latest.power.tolist(),
            },
        }
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "comparison.json").write_text(
            json.dumps(report, indent=2, allow_nan=False) + "\n"
        )
        save_comparison_plot(analyses, output / "comparison.png", synthetic=synthetic)
    except Exception:
        shutil.rmtree(output)
        raise
    return report
