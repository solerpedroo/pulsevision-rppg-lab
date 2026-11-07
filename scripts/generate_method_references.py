"""Explicitly fetch pinned upstream functions and generate numerical synthetic fixtures.

Upstream GPLv3 source is not bundled; functions execute only during this opt-in regeneration.
Normal tests use numerical fixtures offline.
"""

import ast
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import scipy
from rppg_core.signals.synthetic import synthetic_rgb
from scipy import signal

COMMIT = "a6270f04a97f05a13d145dd0a5e8c8df48d8bd62"
URL = f"https://raw.githubusercontent.com/phuselab/pyVHR/{COMMIT}/pyVHR/BVP/methods.py"


def main() -> None:
    with urllib.request.urlopen(URL, timeout=30) as response:
        source = response.read()
    if hashlib.sha256(source).hexdigest() != (
        "f8ee127601254a05cb0c321706a8da1bc49e2ec8e1e183d04ced51e15f14d3b5"
    ):
        raise ValueError("Upstream source SHA256 mismatch")
    tree = ast.parse(source)
    functions: list[ast.stmt] = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"cpu_POS", "cpu_CHROM"}
    ]
    if len(functions) != 2:
        raise ValueError("Expected reference functions were not found")
    namespace: dict[str, Any] = {"np": np}
    exec(compile(ast.Module(body=functions, type_ignores=[]), URL, "exec"), namespace)
    t, rgb = synthetic_rgb(90, duration_s=20, noise=0.03, seed=42)
    fs, length = 30, 48
    upstream_pos = namespace["cpu_POS"](rgb.T[None, :, :], fps=fs)[0]
    # Matched CHROM preprocessing/composition harness: common parameters,
    # upstream projection function; not a claim of full pyVHR pipeline equivalence.
    chrom = np.zeros(len(t))
    sos = signal.butter(4, [0.7, 3.0], fs=fs, btype="bandpass", output="sos")
    for start in range(0, len(t) - length + 1, length // 2):
        segment = rgb[start : start + length]
        normalized = segment / segment.mean(axis=0)
        filtered = signal.sosfiltfilt(sos, normalized, axis=0, padtype="odd")
        pulse = namespace["cpu_CHROM"](filtered.T[None, :, :])[0]
        chrom[start : start + length] += pulse * signal.windows.hann(length, sym=True)
    g = rgb[:, 1] / rgb[:, 1].mean() - 1
    green = g - np.polyval(np.polyfit(np.arange(len(g)), g, 1), np.arange(len(g)))
    fixture = {
        "provenance": {
            "url": URL,
            "commit": COMMIT,
            "source_sha256": hashlib.sha256(source).hexdigest(),
            "license": "GPL-3.0 (upstream source, not redistributed)",
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "generator": "scripts/generate_method_references.py",
            "kind": "artificial RGB, no physiological ground truth",
        },
        "fs": fs,
        "rgb": rgb.tolist(),
        "GREEN": green.tolist(),
        "POS": upstream_pos.tolist(),
        "CHROM": chrom.tolist(),
        "comparison_slice": [length, len(t) - length],
        "parameters": {
            "projection_window_s": 1.6,
            "epsilon": 1e-9,
            "band_hz": [0.7, 3.0],
            "filter_order": 4,
        },
    }
    target = Path("tests/fixtures/method_reference_v1.json")
    target.write_text(json.dumps(fixture, indent=2, allow_nan=False) + "\n")
    print("Generated pinned upstream numeric reference:", target)


if __name__ == "__main__":
    main()
