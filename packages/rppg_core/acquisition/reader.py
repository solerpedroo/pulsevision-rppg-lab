from collections.abc import Generator
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from numpy.typing import NDArray

from .errors import (
    UnsupportedVideoError,
    VideoDecodeError,
    VideoOpenError,
    VideoTimestampError,
)


@dataclass(frozen=True)
class VideoMetadata:
    container: str
    codec: str
    width: int
    height: int
    duration_s: float | None
    nominal_fps: float | None
    time_base: str
    start_time_s: float | None
    declared_frame_count: int | None
    rotation_degrees: int
    stream_index: int


@dataclass(frozen=True)
class FrameSample:
    index: int
    timestamp_s: float
    source_timestamp_s: float
    pts: int
    time_base: Fraction
    rgb: NDArray[np.uint8]
    rotation_degrees: int
    quality_flags: tuple[str, ...]
    mirrored: bool = False


class TimestampValidator:
    """Strict PTS ordering; never synthesize or discard timestamps."""

    def __init__(self) -> None:
        self.origin: Fraction | None = None
        self.previous: Fraction | None = None

    def accept(self, pts: int | None, time_base: Fraction | None) -> tuple[float, float]:
        if pts is None or time_base is None or time_base <= 0:
            raise VideoTimestampError("Frame has no valid PTS/time base")
        current = pts * time_base
        if self.previous is not None and current <= self.previous:
            raise VideoTimestampError(
                "Frame PTS must increase strictly (duplicate or reversed PTS)"
            )
        if self.origin is None:
            self.origin = current
        self.previous = current
        return float(current - self.origin), float(current)


def display_orientation(frame: av.VideoFrame) -> tuple[int, bool]:
    """Quarter turn plus an optional horizontal mirror, from the display matrix.

    `frame.rotation` drops the mirror and can report a flipped clip as 180 degrees.
    """
    matrix = next(
        (
            item
            for kind, item in frame.side_data.items()
            if getattr(kind, "name", "") == "DISPLAYMATRIX"
        ),
        None,
    )
    if matrix is None:
        angle = int(frame.rotation)
        quarter = int(round(angle / 90))
        if abs(angle - quarter * 90) > 2:
            raise ValueError("Only quarter-turn display rotations are supported")
        return quarter * 90, False
    values = np.frombuffer(bytes(matrix), dtype=np.int32)
    if values.size != 9:
        raise ValueError("Display matrix has an unexpected size")
    linear = values.reshape(3, 3)[:2, :2].astype(np.float64) / 65536
    mirrored = bool(np.linalg.det(linear) < 0)
    if mirrored:
        linear = linear @ np.array([[-1.0, 0.0], [0.0, 1.0]])
    angle = int(round(np.degrees(np.arctan2(linear[1, 0], linear[0, 0])) / 90) * 90)
    return angle, mirrored


class VideoReader:
    """Reopen on each iteration; pixels are RGB24 in encoded orientation.

    Explicitly close the iterator if stopping early. Full iteration closes it automatically.
    No seek or frame-index fallback is performed.
    """

    def __init__(self, path: str | Path, *, gap_factor: float = 2.5) -> None:
        self.path = Path(path)
        if not np.isfinite(gap_factor) or gap_factor <= 1:
            raise ValueError("gap_factor must be finite and greater than one")
        self.gap_factor = gap_factor

    def _open(self) -> av.container.InputContainer:
        if not self.path.is_file():
            raise VideoOpenError("Input must be an existing local file")
        try:
            return av.open(str(self.path), mode="r", options={"err_detect": "explode"})
        except (av.FFmpegError, OSError, ValueError) as exc:
            raise VideoOpenError("Cannot open input as a video container") from exc

    @staticmethod
    def _stream(container: av.container.InputContainer) -> av.video.stream.VideoStream:
        if not container.streams.video:
            raise UnsupportedVideoError("Container has no video stream")
        stream = container.streams.video[0]
        if stream.codec_context.codec is None or not stream.codec_context.codec.is_decoder:
            raise UnsupportedVideoError("Video codec has no decoder")
        return stream

    def metadata(self) -> VideoMetadata:
        with self._open() as container:
            stream = self._stream(container)
            try:
                first = next(container.decode(stream), None)
                if first is None:
                    raise VideoDecodeError("Video has no decodable frames")
                duration = (
                    float(stream.duration * stream.time_base)
                    if stream.duration is not None and stream.time_base
                    else (
                        float(container.duration / av.time_base)
                        if container.duration is not None
                        else None
                    )
                )
                return VideoMetadata(
                    container=container.format.name,
                    codec=stream.codec_context.name,
                    width=stream.codec_context.width,
                    height=stream.codec_context.height,
                    duration_s=duration,
                    nominal_fps=float(stream.average_rate) if stream.average_rate else None,
                    time_base=str(stream.time_base),
                    start_time_s=(
                        float(stream.start_time * stream.time_base)
                        if stream.start_time is not None and stream.time_base
                        else None
                    ),
                    declared_frame_count=stream.frames or None,
                    rotation_degrees=(
                        display_orientation(first)[0]
                        if any(
                            getattr(kind, "name", "") == "DISPLAYMATRIX"
                            for kind in first.side_data
                        )
                        or int(first.rotation) % 90 == 0
                        else 0
                    ),
                    stream_index=stream.index,
                )
            except (av.FFmpegError, ValueError) as exc:
                raise VideoDecodeError("Cannot decode video metadata/first frame") from exc

    def frames(self) -> Generator[FrameSample, None, None]:
        with self._open() as container:
            stream = self._stream(container)
            timing = TimestampValidator()
            previous_s: float | None = None
            count = 0
            nominal = float(stream.average_rate) if stream.average_rate else None
            try:
                for frame in container.decode(stream):
                    if frame.is_corrupt:
                        raise VideoDecodeError("Decoder marked a frame as corrupt")
                    base = (
                        Fraction(frame.time_base.numerator, frame.time_base.denominator)
                        if frame.time_base
                        else None
                    )
                    relative, source = timing.accept(frame.pts, base)
                    flags: tuple[str, ...] = ()
                    if (
                        previous_s is not None
                        and nominal
                        and nominal > 0
                        and relative - previous_s > self.gap_factor / nominal
                    ):
                        flags = ("temporal_gap",)
                    if frame.pts is None or base is None:
                        raise VideoTimestampError("Missing PTS")
                    rgb = np.asarray(frame.to_ndarray(format="rgb24"), dtype=np.uint8)
                    try:
                        angle, mirrored = display_orientation(frame)
                    except ValueError:
                        angle, mirrored = 45, False
                        flags = (*flags, "invalid_geometry")
                    yield FrameSample(
                        index=count,
                        timestamp_s=relative,
                        source_timestamp_s=source,
                        pts=frame.pts,
                        time_base=base,
                        rgb=rgb,
                        rotation_degrees=angle,
                        quality_flags=flags,
                        mirrored=mirrored,
                    )
                    count += 1
                    previous_s = relative
            except (av.FFmpegError, ValueError) as exc:
                raise VideoDecodeError(
                    "Video decoding failed; partial results are invalid"
                ) from exc
            if not count:
                raise VideoDecodeError("Video has no decodable frames")
            if stream.frames and count != stream.frames:
                raise VideoDecodeError("Decoded frame count differs from container declaration")
