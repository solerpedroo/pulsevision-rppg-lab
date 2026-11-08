"""Generate only artificial RGB/sensor-like reference data and a development manifest."""

import argparse
import csv
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from rppg_core.methods.config import MethodConfig
from rppg_core.quality.config import QualityConfig
from rppg_core.signals.config import SignalConfig
from rppg_core.signals.synthetic import synthetic_rgb


def create_demo(root: Path, *, subjects: int = 4, duration_s: float = 23) -> Path:
    if subjects < 3:
        raise ValueError("Demo requires at least three artificial participants")
    root.mkdir(parents=True, exist_ok=False)
    (root / "access.txt").write_text(
        "Project-generated artificial RGB/reference; no human recordings.\n"
    )
    (root / "alignment.txt").write_text(
        "Artificial clocks are constructed identically; reference origin=0 and offset=0 seconds.\n"
    )
    sessions: list[dict[str, Any]] = []
    for index in range(subjects):
        participant = f"synthetic{index + 1:02d}"
        bpm = 65 + index * 10
        t, rgb = synthetic_rgb(bpm, duration_s=duration_s, seed=42 + index, noise=0.1)
        with (root / (participant + ".csv")).open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "timestamp_s",
                    "roi",
                    "r_mean",
                    "g_mean",
                    "b_mean",
                    "landmark_status",
                    "quality_flags",
                    "motion_score",
                ]
            )
            for timestamp, values in zip(t, rgb, strict=True):
                motion = 0.5 if index == 1 and timestamp == 0 else 0.01
                writer.writerow(
                    [timestamp, "combined", *values, "ok", '["synthetic_reference"]', motion]
                )
        # UBFC-shaped reference: PPG / sensor HR / timestamps, at independent 60 Hz.
        ref_time = np.arange(int(duration_s * 60)) / 60
        matrix = np.vstack(
            (np.sin(2 * np.pi * (bpm / 60) * ref_time), np.full(len(ref_time), bpm), ref_time)
        )
        reference_name = participant + "_ground_truth.txt"
        np.savetxt(root / reference_name, matrix)
        sessions.append(
            {
                "participant_id": participant,
                "session_id": "session1",
                "condition": "synthetic_motion_event" if index == 1 else "synthetic_stationary",
                "rgb_csv": participant + ".csv",
                "reference": reference_name,
                "reference_format": "ubfc_text",
                "alignment": {
                    "verified": True,
                    "reference_origin_s": 0,
                    "offset_s": 0,
                    "evidence_file": "alignment.txt",
                },
            }
        )
    manifest = {
        "schema_version": "benchmark-v1",
        "dataset": "synthetic",
        "dataset_version": "artificial-demo-v1",
        "access_record": "access.txt",
        "protocol_version": "protocol-v1-development",
        "seed": 42,
        "bootstrap_samples": 1000,
        "reference_max_gap_s": 0.2,
        "roi": "combined",
        "splits": {
            "development": [x["participant_id"] for x in sessions],
            "validation": [],
            "test": [],
        },
        "sessions": sessions,
        "signal": asdict(SignalConfig()),
        "methods": asdict(MethodConfig()),
        "quality": asdict(QualityConfig()),
    }
    path = root / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    create_demo(args.output)
    print("Created artificial development fixture; not a dataset accuracy benchmark.")


if __name__ == "__main__":
    main()
