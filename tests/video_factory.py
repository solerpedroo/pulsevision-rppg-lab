"""Original synthetic fixtures, generated only in temporary directories."""

from fractions import Fraction
from pathlib import Path

import av
import numpy as np


def make_video(
    path: Path,
    pts: list[int],
    *,
    rotation: int = 0,
    offset: int = 0,
    width: int = 64,
    height: int = 48,
) -> Path:
    codec = "libvpx-vp9" if path.suffix == ".webm" else "mpeg4"
    options = {"movflags": "+faststart"} if path.suffix in {".mp4", ".mov"} else {}
    with av.open(str(path), "w", options=options) as output:
        stream = output.add_stream(codec, rate=25)
        stream.width, stream.height = width, height
        stream.pix_fmt = "yuv420p"
        stream.codec_context.time_base = Fraction(1, 1000)
        stream.time_base = Fraction(1, 1000)
        if path.suffix == ".avi":
            # AVI CFR headers count frame slots; use the actual 25 Hz codec time base.
            stream.codec_context.time_base = Fraction(1, 25)
            stream.time_base = Fraction(1, 25)
        if rotation:
            stream.set_display_rotation(rotation)
        for timestamp in pts:
            pixels = np.zeros((height, width, 3), dtype=np.uint8)
            pixels[:] = (180, 80, 40)
            frame = av.VideoFrame.from_ndarray(pixels, format="rgb24")
            frame.pts = timestamp + offset
            frame.time_base = Fraction(1, 1000)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    return path
