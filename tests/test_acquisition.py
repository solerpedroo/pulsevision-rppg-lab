import json
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from rppg_core.acquisition.errors import (
    UnsupportedVideoError,
    VideoDecodeError,
    VideoOpenError,
    VideoTimestampError,
)
from rppg_core.acquisition.inspect_video import inspect_video
from rppg_core.acquisition.reader import TimestampValidator, VideoReader
from video_factory import make_video


@pytest.mark.parametrize("extension", [".mp4", ".mov", ".webm"])
@pytest.mark.parametrize(
    "pts",
    [
        [0, 40, 80, 120, 160, 200],
        [0, 40, 120, 160, 400, 440],
    ],
)
def test_containers_and_timestamps(tmp_path: Path, extension: str, pts: list[int]) -> None:
    path = make_video(tmp_path / ("synthetic" + extension), pts)
    reader = VideoReader(path)
    metadata = reader.metadata()
    frames = list(reader.frames())
    assert len(frames) == len(pts)
    assert metadata.width == 64 and metadata.height == 48
    assert metadata.duration_s is not None and metadata.duration_s >= pts[-1] / 1000
    assert metadata.nominal_fps is not None
    np.testing.assert_allclose([f.timestamp_s for f in frames], np.array(pts) / 1000, atol=0.001)
    assert frames[0].rgb.shape == (48, 64, 3)
    assert frames[0].rgb.dtype == np.uint8
    # Distinct R and B values detect accidental BGR conversion.
    np.testing.assert_allclose(frames[0].rgb.mean(axis=(0, 1)), [180, 80, 40], atol=5)
    assert all(f.pts * f.time_base == Fraction(t, 1000) for f, t in zip(frames, pts))
    assert len(list(reader.frames())) == len(pts)  # Reader reopens at the start.


def test_vfr_report_and_constant_pixels(tmp_path: Path) -> None:
    path = make_video(tmp_path / "vfr.mp4", [0, 40, 80, 400, 440])
    report = inspect_video(path)
    assert report["timing"]["decoded_frames"] == 5
    assert report["timing"]["gap_count"] >= 1
    assert report["timing"]["effective_fps"] == pytest.approx(4 / 0.44)
    assert report["timing"]["interval_cv"] > 0
    # Identical content is preserved when timestamps differ.
    assert len(report["timeline"]) == 5


def test_nonzero_origin(tmp_path: Path) -> None:
    path = make_video(tmp_path / "offset.mov", [0, 40, 80], offset=1000)
    frames = list(VideoReader(path).frames())
    assert frames[0].timestamp_s == 0
    assert frames[0].source_timestamp_s == pytest.approx(1)
    assert frames[-1].timestamp_s == pytest.approx(0.08)


def test_orientation(tmp_path: Path) -> None:
    path = make_video(tmp_path / "portrait.mov", [0, 40], rotation=90)
    reader = VideoReader(path)
    assert abs(reader.metadata().rotation_degrees) == 90
    iterator = reader.frames()
    frame = next(iterator)
    iterator.close()
    assert abs(frame.rotation_degrees) == 90
    assert frame.rgb.shape == (48, 64, 3)  # Pixels retain encoded orientation.


@pytest.mark.parametrize("pts,base", [(None, Fraction(1, 30)), (0, None), (0, Fraction(0))])
def test_missing_timestamp(pts: int | None, base: Fraction | None) -> None:
    with pytest.raises(VideoTimestampError):
        TimestampValidator().accept(pts, base)


@pytest.mark.parametrize("next_pts", [10, 9])
def test_duplicate_or_reversed_pts(next_pts: int) -> None:
    timing = TimestampValidator()
    timing.accept(10, Fraction(1, 30))
    with pytest.raises(VideoTimestampError):
        timing.accept(next_pts, Fraction(1, 30))


def test_missing_and_invalid_file(tmp_path: Path) -> None:
    with pytest.raises(VideoOpenError):
        list(VideoReader(tmp_path / "missing.mp4").frames())
    path = tmp_path / "broken.mp4"
    path.write_bytes(b"not a video")
    with pytest.raises(VideoOpenError):
        VideoReader(path).metadata()


def test_truncated_file(tmp_path: Path) -> None:
    path = make_video(tmp_path / "truncated.mp4", list(range(0, 4000, 40)))
    path.write_bytes(path.read_bytes()[:300])
    with pytest.raises((VideoOpenError, VideoDecodeError, UnsupportedVideoError)):
        list(VideoReader(path).frames())


def test_no_video_stream(tmp_path: Path) -> None:
    import av

    path = tmp_path / "audio.wav"
    with av.open(str(path), "w") as output:
        stream = output.add_stream("pcm_s16le", rate=8000)
        frame = av.AudioFrame.from_ndarray(np.zeros((1, 800), dtype=np.int16), layout="mono")
        frame.sample_rate = 8000
        for packet in stream.encode(frame):
            output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    with pytest.raises(UnsupportedVideoError):
        list(VideoReader(path).frames())


def test_cli(tmp_path: Path) -> None:
    path = make_video(tmp_path / "cli.webm", [0, 40, 80])
    process = subprocess.run(
        [sys.executable, "-m", "rppg_core.acquisition.inspect_video", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(process.stdout)["timing"]["decoded_frames"] == 3
    process = subprocess.run(
        [sys.executable, "-m", "rppg_core.acquisition.inspect_video", str(tmp_path / "absent")],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 2 and not process.stdout
    assert json.loads(process.stderr)["error"]["code"] == "video_open_error"


def test_truncated_payload(tmp_path: Path) -> None:
    path = make_video(tmp_path / "partial.mp4", list(range(0, 4000, 40)))
    original_size = path.stat().st_size
    path.write_bytes(path.read_bytes()[: int(original_size * 0.8)])
    # Header survives faststart, but payload is incomplete.
    with pytest.raises(VideoDecodeError):
        list(VideoReader(path).frames())


def test_single_frame(tmp_path: Path) -> None:
    path = make_video(tmp_path / "single.mp4", [0])
    report = inspect_video(path)
    assert report["timing"]["decoded_frames"] == 1
    assert report["timing"]["effective_fps"] is None


@pytest.mark.parametrize("factor", [1, 0, float("nan"), float("inf")])
def test_invalid_gap_configuration(factor: float) -> None:
    with pytest.raises(ValueError):
        VideoReader("unused.mp4", gap_factor=factor)
