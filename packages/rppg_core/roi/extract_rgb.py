"""Extract per-ROI RGB traces to an explicitly requested CSV, without saving frames."""

import argparse
import csv
import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from rppg_core.acquisition import VideoReader
from rppg_core.acquisition.errors import VideoError
from rppg_core.face.detector import FaceError, MediaPipeDetector

from .extraction import ExtractionConfig
from .pipeline import RGBExtractor

FIELDS = [
    "timestamp_s",
    "roi",
    "r_mean",
    "g_mean",
    "b_mean",
    "valid_pixel_fraction",
    "landmark_status",
    "motion_score",
    "roi_area",
    "valid_pixels",
    "dark_fraction",
    "saturated_fraction",
    "brightness",
    "quality_flags",
]


def export_csv(
    video: Path,
    model: Path,
    output: Path,
    *,
    reader: VideoReader | None = None,
    on_regions: Callable[[float, dict[str, NDArray[np.bool_]]], None] | None = None,
) -> dict[str, Any]:
    if output.exists() or output.with_suffix(".metadata.json").exists():
        raise ValueError("Output or metadata file already exists")
    if {output.resolve(), output.with_suffix(".metadata.json").resolve()} & {
        video.resolve(),
        model.resolve(),
    }:
        raise ValueError("Output cannot overwrite inputs")
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=output.parent, suffix=".partial")
    config = ExtractionConfig()
    counts = {"rows": 0, "valid_rows": 0}
    try:
        with os.fdopen(descriptor, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            with MediaPipeDetector(model) as detector:
                for row in RGBExtractor(detector, config, on_regions=on_regions).extract(
                    reader or VideoReader(video)
                ):
                    means = row.sample.rgb_mean if row.sample else ["", "", ""]
                    stats = row.stats
                    writer.writerow(
                        dict(
                            zip(
                                FIELDS,
                                [
                                    row.timestamp_s,
                                    row.roi,
                                    *means,
                                    stats.valid_fraction if stats else "",
                                    row.status,
                                    row.motion_score if row.motion_score is not None else "",
                                    stats.area if stats else "",
                                    stats.valid_pixels if stats else "",
                                    stats.dark_fraction if stats else "",
                                    stats.saturated_fraction if stats else "",
                                    stats.brightness if stats else "",
                                    json.dumps(row.flags),
                                ],
                                strict=True,
                            )
                        )
                    )
                    counts["rows"] += 1
                    counts["valid_rows"] += int(row.sample is not None)
        metadata = {
            "schema_version": "1.0",
            "roi_version": "roi-v1",
            "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            "timestamp_origin": "first_decoded_frame",
            "rgb_scale": "RGB24 0-255",
            "display_orientation_applied": True,
            "config": asdict(config),
            "single_face_only": True,
            **counts,
        }
        os.link(temporary, output)
        try:
            with output.with_suffix(".metadata.json").open("x") as handle:
                handle.write(json.dumps(metadata, indent=2) + "\n")
        except OSError:
            output.unlink()
            raise
        return metadata
    finally:
        Path(temporary).unlink(missing_ok=True)


def main() -> int:
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = export_csv(args.video, args.model, args.output)
    except (VideoError, FaceError, ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
