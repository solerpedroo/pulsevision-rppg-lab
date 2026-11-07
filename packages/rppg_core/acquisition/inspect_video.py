"""Usage: python -m rppg_core.acquisition.inspect_video <local-file>."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import av
import numpy as np

from .errors import VideoError
from .reader import VideoReader


def inspect_video(path: str | Path) -> dict[str, Any]:
    reader = VideoReader(path)
    metadata = reader.metadata()
    timeline: list[dict[str, Any]] = []
    for frame in reader.frames():
        timeline.append(
            {
                "index": frame.index,
                "pts": frame.pts,
                "time_base": str(frame.time_base),
                "timestamp_s": frame.timestamp_s,
                "source_timestamp_s": frame.source_timestamp_s,
                "quality_flags": list(frame.quality_flags),
            }
        )
    timestamps = np.array([row["timestamp_s"] for row in timeline], dtype=float)
    deltas = np.diff(timestamps)
    span = float(timestamps[-1] - timestamps[0])
    return {
        "schema_version": "1.0",
        "metadata": asdict(metadata),
        "decoder": {
            "pyav": av.__version__,
            "libraries": {k: list(v) for k, v in av.library_versions.items()},
        },
        "timing": {
            "decoded_frames": len(timeline),
            "observed_span_s": span,
            "effective_fps": (len(timeline) - 1) / span if span > 0 else None,
            "min_interval_s": float(deltas.min()) if deltas.size else None,
            "max_interval_s": float(deltas.max()) if deltas.size else None,
            "interval_cv": float(deltas.std() / deltas.mean()) if deltas.size else None,
            "gap_count": sum("temporal_gap" in row["quality_flags"] for row in timeline),
        },
        "timeline": timeline,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        report = inspect_video(args.file)
    except VideoError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": str(exc)}}), file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
