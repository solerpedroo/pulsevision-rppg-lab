"""Deterministic artificial RGB. These traces are not physiological ground truth."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from .temporal import FloatArray


def synthetic_rgb(
    bpm: float = 90,
    *,
    duration_s: float = 30,
    fs: float = 30,
    noise: float = 0.1,
    seed: int = 42,
    harmonic_amplitude: float = 0.0,
) -> tuple[FloatArray, FloatArray]:
    if (
        not np.isfinite([bpm, duration_s, fs, noise, harmonic_amplitude]).all()
        or min(bpm, duration_s, fs) <= 0
        or min(noise, harmonic_amplitude) < 0
    ):
        raise ValueError("Invalid synthetic signal parameters")
    t = np.arange(int(round(duration_s * fs)), dtype=float) / fs
    pulse = np.sin(2 * np.pi * (bpm / 60) * t) + harmonic_amplitude * np.sin(
        4 * np.pi * (bpm / 60) * t
    )
    rgb = np.array([140.0, 100.0, 80.0]) + pulse[:, None] * np.array([0.3, 1.0, 0.15])
    rgb += np.random.default_rng(seed).normal(0, noise, rgb.shape)
    if (rgb < 0).any() or (rgb > 255).any():
        raise ValueError("Synthetic signal exceeds RGB24 range")
    return t, rgb


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--bpm", type=float, default=90)
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--noise", type=float, default=0.1)
    args = parser.parse_args()
    t, rgb = synthetic_rgb(args.bpm, duration_s=args.duration, noise=args.noise)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["timestamp_s", "roi", "r_mean", "g_mean", "b_mean", "landmark_status", "quality_flags"]
        )
        for timestamp, channels in zip(t, rgb, strict=True):
            writer.writerow(
                [timestamp, "combined", *channels, "ok", json.dumps(["synthetic_reference"])]
            )
    print("Artificial RGB trace written; not real pulse measurements.")


if __name__ == "__main__":
    main()
