"""Private subprocess entry point. No request/user-controlled executable or shell."""

import ctypes
import json
import os
import resource
import signal
import sys
from pathlib import Path
from typing import Any


def write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, allow_nan=False))
    temporary.replace(path)


def run(directory: Path, options: dict[str, Any]) -> None:
    # MediaPipe eagerly imports its optional audio API, whose PortAudio startup can
    # block on desktop audio daemons. This isolated video-only process has no audio.
    # A None sys.modules entry raises ImportError, handled by MediaPipe AudioRecord.
    sys.modules["sounddevice"] = None  # type: ignore[assignment]
    import csv
    import hashlib
    import importlib.metadata
    from collections.abc import Generator
    from contextlib import closing
    from dataclasses import asdict

    import av
    import numpy as np
    from rppg_core.acquisition import FrameSample, VideoReader
    from rppg_core.estimation.pipeline import analyze_trace, analyze_window
    from rppg_core.methods.config import MethodConfig
    from rppg_core.quality.config import QualityConfig
    from rppg_core.quality.summary import summarize_quality
    from rppg_core.roi.extract_rgb import export_csv
    from rppg_core.signals.analyze_rgb import load_trace_csv, save_plot
    from rppg_core.signals.config import SignalConfig

    source = directory / "input.bin"
    with av.open(str(source)) as container:
        if not container.streams.video:
            raise ValueError("unsupported_video")
        stream = container.streams.video[0]
        codec = stream.codec_context
        if (
            codec.width > options["max_dimension"]
            or codec.height > options["max_dimension"]
            or codec.width * codec.height > options["max_pixels"]
        ):
            raise ValueError("video_limits_exceeded")
        duration = (
            float(stream.duration * stream.time_base)
            if stream.duration is not None and stream.time_base
            else container.duration / av.time_base
            if container.duration is not None
            else None
        )
        if duration is not None and duration > options["max_duration_s"]:
            raise ValueError("video_limits_exceeded")
        if stream.average_rate and float(stream.average_rate) > options["max_fps"] * 1.1:
            raise ValueError("video_limits_exceeded")
        detected = container.format.name
        expected = options["container"]
        if (
            expected == "mp4"
            and "mp4" not in detected
            and "mov" not in detected
            or expected == "webm"
            and "webm" not in detected
            or expected == "avi"
            and "avi" not in detected
        ):
            raise ValueError("container_mismatch")

    class LimitedReader(VideoReader):
        def frames(self) -> Generator[FrameSample, None, None]:
            with closing(super().frames()) as frames:
                for item in frames:
                    height, width = item.rgb.shape[:2]
                    if (
                        height * width > options["max_pixels"]
                        or max(height, width) > options["max_dimension"]
                        or item.index >= options["max_frames"]
                        or item.timestamp_s > options["max_duration_s"]
                        or item.index > 15
                        and item.timestamp_s > 0
                        and item.index / item.timestamp_s > options["max_fps"] * 1.1
                    ):
                        raise ValueError("video_limits_exceeded")
                    if item.index % 10 == 0:
                        fraction = item.timestamp_s / max(
                            duration or options["max_duration_s"], 0.1
                        )
                        write_json(
                            directory / "progress.json",
                            {"progress": min(0.75, 0.05 + 0.7 * fraction)},
                        )
                    yield item

    trace_file = directory / "trace.csv"
    write_json(directory / "progress.json", {"progress": 0.03})
    roi_points: list[dict[str, Any]] = []

    def regions(timestamp: float, masks: dict[str, Any]) -> None:
        import cv2

        polygons = {}
        for name, mask in masks.items():
            contours, hierarchy = cv2.findContours(
                mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
            )
            height, width = mask.shape
            scale_x = max(width - 1, 1)
            scale_y = max(height - 1, 1)
            rings = []
            for contour in contours:
                contour = cv2.approxPolyDP(contour, 1.5, True).reshape(-1, 2)
                if len(contour) >= 3:
                    rings.append(
                        [[float(x) / scale_x, float(y) / scale_y] for x, y in contour]
                    )
            if rings:
                polygons[name] = rings
            del hierarchy
        roi_points.append({"timestamp_s": timestamp, "regions": polygons})

    export_csv(
        source, Path(options["model"]), trace_file, reader=LimitedReader(source), on_regions=regions
    )
    write_json(directory / "roi.json", roi_points)
    trace = load_trace_csv(trace_file, options["roi"])
    write_json(directory / "progress.json", {"progress": 0.8})
    if len(trace.timestamps) >= 2:
        analyses = list(
            analyze_trace(
                trace.timestamps,
                trace.rgb,
                method=options["method"],
                roi=options["roi"],
                valid=trace.valid,
                evidence=trace.evidence,
            )
        )
    else:
        analyses = [
            analyze_window(
                trace.timestamps,
                trace.rgb,
                start_s=0,
                end_s=1,
                method=options["method"],
                roi=options["roi"],
                valid=trace.valid,
                evidence=trace.evidence,
            )
        ]
    estimates = [item.estimate for item in analyses]

    def digest(path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                hasher.update(chunk)
        return hasher.hexdigest()

    write_json(
        directory / "results.json",
        {
            "estimates": [item.model_dump(mode="json") for item in estimates],
            "processing": {
                "signal_config": asdict(SignalConfig()),
                "method_config": asdict(MethodConfig()),
                "quality_config": asdict(QualityConfig()),
                "input_sha256": digest(source),
                "model_sha256": digest(Path(options["model"])),
                "environment": {
                    name: importlib.metadata.version(name)
                    for name in ("numpy", "scipy", "av", "mediapipe")
                },
            },
            "summary": summarize_quality(estimates).as_dict(),
            "diagnostic_windows": len(analyses),
            "method": options["method"],
            "roi": options["roi"],
            "experimental_notice": "Experimental estimate; not a medical device.",
        },
    )
    with (directory / "estimates.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["start_s", "end_s", "method", "roi", "bpm", "status", "reasons"])
        for item in estimates:
            writer.writerow(
                [
                    item.window.start_s,
                    item.window.end_s,
                    item.method,
                    item.roi,
                    item.bpm,
                    item.status,
                    json.dumps(item.reasons),
                ]
            )
    rgb_points = []
    for timestamp, color, evidence in zip(trace.timestamps, trace.rgb, trace.evidence, strict=True):
        rgb_points.append(
            {
                "timestamp_s": float(timestamp),
                **{
                    key: float(value) if np.isfinite(value) else None
                    for key, value in zip(("r", "g", "b"), color, strict=True)
                },
                "landmark_status": evidence.landmark_status,
                "quality_flags": list(evidence.flags),
            }
        )
    write_json(directory / "rgb.json", rgb_points)
    (directory / "signals").mkdir()
    for index, analysis in enumerate(analyses):
        write_json(
            directory / "signals" / f"{index}.json",
            {
                "rppg": [
                    {"timestamp_s": float(t), "value": float(v)}
                    for t, v in zip(analysis.timestamps_s, analysis.signal, strict=True)
                ],
                "spectrum": [
                    {"frequency_hz": float(f), "power": float(p)}
                    for f, p in zip(analysis.frequencies_hz, analysis.power, strict=True)
                ],
            },
        )
    save_plot(analyses[-1], directory / "diagnostics.png", synthetic=False)
    trace_file.unlink(missing_ok=True)
    trace_file.with_suffix(".metadata.json").unlink(missing_ok=True)
    write_json(directory / "done.json", {"ok": True})


def main() -> int:
    directory = Path(sys.argv[1])
    options = json.loads((directory / "options.json").read_text())
    # Kill worker when API parent exits (including abrupt exit), before native libraries load.
    parent = int(sys.argv[2])
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL) != 0 or os.getppid() != parent:
        return 1
    resource.setrlimit(resource.RLIMIT_CPU, (options["cpu_limit_s"], options["cpu_limit_s"]))
    resource.setrlimit(
        resource.RLIMIT_AS, (options["memory_limit_bytes"], options["memory_limit_bytes"])
    )
    file_limit = int(options.get("max_job_bytes", 256 * 1024**2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_limit, file_limit))
    try:
        run(directory, options)
        return 0
    except Exception as exc:
        recognized = {
            "video_limits_exceeded",
            "unsupported_video",
            "container_mismatch",
            "video_open_error",
            "video_decode_error",
            "invalid_timestamps",
        }
        typed = getattr(exc, "code", None)
        code = (
            typed
            if typed in recognized
            else str(exc)
            if str(exc) in recognized
            else ("memory_limit" if isinstance(exc, MemoryError) else "processing_failed")
        )
        write_json(directory / "done.json", {"ok": False, "error": code})
        return 1
    finally:
        (directory / "input.bin").unlink(missing_ok=True)
        (directory / "trace.csv").unlink(missing_ok=True)
        (directory / "trace.metadata.json").unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
