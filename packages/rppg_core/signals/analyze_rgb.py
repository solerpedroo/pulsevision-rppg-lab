"""Analyze a wave-2 RGB CSV; export offline estimates and diagnostic PNG."""

import argparse
import csv
import hashlib
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from numpy.typing import NDArray
from rppg_types.models import Method, Roi

from rppg_core.estimation.pipeline import WindowAnalysis, analyze_trace
from rppg_core.methods.config import MethodConfig, load_method_config

from .config import SignalConfig
from .temporal import FloatArray, SignalInputError


def load_csv(path: Path, roi: Roi) -> tuple[FloatArray, FloatArray, NDArray[np.bool_]]:
    timestamps, rgb, valid = [], [], []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {
            "timestamp_s",
            "roi",
            "r_mean",
            "g_mean",
            "b_mean",
            "landmark_status",
            "quality_flags",
        }
        if not expected.issubset(reader.fieldnames or []):
            raise SignalInputError("Missing RGB trace CSV columns")
        for row in reader:
            if row["roi"] != roi:
                continue
            try:
                timestamps.append(float(row["timestamp_s"]))
                values = [
                    float(row[key]) if row[key] else float("nan")
                    for key in ("r_mean", "g_mean", "b_mean")
                ]
                flags = json.loads(row["quality_flags"])
                if not isinstance(flags, list) or not all(isinstance(x, str) for x in flags):
                    raise ValueError("Flags must be an array of strings")
                # Do not bridge tracking resets or change the membership of combined ROI.
                blocked = {
                    "tracking_gap",
                    "unstable_geometry",
                    "temporal_gap",
                    "illumination_change",
                    "partial_roi",
                    "invalid_geometry",
                }
                good = row["landmark_status"] == "ok" and not blocked.intersection(flags)
                if timestamps and len(timestamps) > 1 and "tracking_reset" in flags:
                    good = False
                rgb.append(values)
                valid.append(good)
            except (ValueError, KeyError, TypeError) as exc:
                raise SignalInputError("Malformed RGB trace CSV row") from exc
    return (
        np.asarray(timestamps, dtype=np.float64),
        np.asarray(rgb, dtype=np.float64).reshape(-1, 3),
        np.asarray(valid, dtype=bool),
    )


def save_plot(analysis: WindowAnalysis, path: Path, *, synthetic: bool) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(2, 1, figsize=(9, 6), layout="constrained")
    title = (
        "Artificial RGB — synthetic demonstration"
        if synthetic
        else f"Experimental offline {analysis.estimate.method}"
    )
    estimate = analysis.estimate
    figure.suptitle(
        title
        + " | "
        + (
            f"{estimate.bpm:.1f} BPM"
            if estimate.bpm is not None
            else "No estimate: " + ", ".join(estimate.reasons)
        )
    )
    axes[0].plot(analysis.timestamps_s, analysis.signal)
    axes[0].set(
        xlabel="Session time (s)",
        ylabel=f"{analysis.estimate.method} (relative intensity)",
        title="Filtered signal; edge samples excluded",
    )
    axes[1].plot(analysis.frequencies_hz, analysis.power)
    axes[1].set(
        xlabel="Frequency (Hz)",
        ylabel="PSD (relative intensity²/Hz)",
        title="Welch PSD",
        xlim=(0, 4),
    )
    figure.savefig(path, dpi=140)
    plt.close(figure)


def export_analysis(
    source: Path,
    output: Path,
    *,
    roi: Roi = "combined",
    method: Method = "GREEN",
    method_config: MethodConfig | None = None,
    config: SignalConfig | None = None,
) -> dict[str, Any]:
    config = config or SignalConfig()
    method_config = method_config or MethodConfig()
    timestamps, rgb, valid = load_csv(source, roi)
    analyses = list(
        analyze_trace(
            timestamps,
            rgb,
            roi=roi,
            method=method,
            method_config=method_config,
            valid=valid,
            config=config,
        )
    )
    synthetic = False
    with source.open(newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["roi"] == roi]
        synthetic = bool(rows) and all(
            "synthetic_reference" in json.loads(row["quality_flags"]) for row in rows
        )
    report = {
        "schema_version": "1.0",
        "method": method,
        "roi": roi,
        "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "input_kind": "synthetic" if synthetic else "unverified_rgb_trace",
        "config": asdict(config),
        "method_config": asdict(method_config),
        "environment": {"numpy": np.__version__, "scipy": scipy.__version__},
        "eligible_windows": len(analyses),
        "coverage": sum(item.estimate.bpm is not None for item in analyses) / len(analyses),
        "window_policy": (
            "complete_half_open_windows; short_trace_abstains; trailing_partial_omitted"
        ),
        "accepted_windows": sum(item.estimate.bpm is not None for item in analyses),
        "estimates": [item.estimate.model_dump(mode="json") for item in analyses],
    }
    output.mkdir(parents=True, exist_ok=False)
    try:
        (output / "estimates.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        save_plot(analyses[-1], output / f"{method.lower()}_diagnostics.png", synthetic=synthetic)
    except Exception:
        shutil.rmtree(output)
        raise
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--roi", choices=["forehead", "left_cheek", "right_cheek", "combined"], default="combined"
    )
    parser.add_argument("--method", choices=["GREEN", "CHROM", "POS", "all"], default="GREEN")
    parser.add_argument("--method-config", type=Path)
    args = parser.parse_args()
    try:
        method_config = (
            load_method_config(args.method_config) if args.method_config else MethodConfig()
        )
        if args.method == "all":
            from .compare_methods import export_comparison

            export_comparison(args.csv, args.output, roi=args.roi, method_config=method_config)
            print(json.dumps({"methods": ["GREEN", "CHROM", "POS"]}))
            return 0
        report = export_analysis(
            args.csv, args.output, roi=args.roi, method=args.method, method_config=method_config
        )
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "eligible_windows": report["eligible_windows"],
                "accepted_windows": report["accepted_windows"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
