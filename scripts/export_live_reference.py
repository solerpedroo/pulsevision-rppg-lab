"""Export browser constants and synthetic regressions from the Python reference."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from rppg_core.estimation.pipeline import analyze_window
from rppg_core.quality.config import QualityConfig
from rppg_core.roi.geometry import EXCLUSIONS, REGIONS
from rppg_types.models import Method
from scipy.signal import butter, sosfilt_zi


def outputs() -> dict[Path, dict[str, Any]]:
    fs = 30
    sos = butter(4, [0.7, 3.0], btype="bandpass", fs=fs, output="sos")
    quality = asdict(QualityConfig())
    # Browser cadence jitters below 30 Hz when MediaPipe runs on CPU.
    quality["max_interval_cv"] = 0.45
    config = {
        "generator": "scripts/export_live_reference.py",
        "version": "live-v1",
        "fs": fs,
        "sos": sos.tolist(),
        "zi": sosfilt_zi(sos).tolist(),
        "regions": REGIONS,
        "exclusions": EXCLUSIONS,
        "quality": quality,
    }
    cases = []
    for frequency in [1.0, 1.5, 2.2]:
        t = np.arange(600, dtype=float) / fs
        wave = np.sin(2 * np.pi * frequency * t)
        rgb = np.column_stack((160 + 0.3 * wave, 90 + wave, 60 + 0.2 * wave))
        expected = {}
        methods: tuple[Method, ...] = ("GREEN", "POS", "CHROM")
        for method in methods:
            result = analyze_window(t, rgb, start_s=0, end_s=20, method=method)
            expected[method] = {
                "bpm": result.estimate.bpm,
                "reasons": result.estimate.reasons,
                "timestamps": result.timestamps_s.tolist(),
                "signal": result.signal.tolist(),
                "frequencies": result.frequencies_hz.tolist(),
                "power": result.power.tolist(),
            }
        cases.append(
            {
                "frequency_hz": frequency,
                "timestamps": t.tolist(),
                "rgb": rgb.tolist(),
                "expected": expected,
            }
        )
    return {
        Path("apps/web/features/live/generated-config.json"): config,
        Path("tests/fixtures/live-dsp.json"): {
            "generator": "scripts/export_live_reference.py",
            "synthetic": True,
            "fs": fs,
            "cases": cases,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    for path, data in outputs().items():
        encoded = json.dumps(data, indent=2, allow_nan=False) + "\n"
        if args.check:
            if path.read_text() != encoded:
                raise SystemExit(f"Stale generated reference: {path}")
        else:
            path.write_text(encoded)


if __name__ == "__main__":
    main()
