"""Create an original, face-free H.264 fixture; never a physiological sample."""

from fractions import Fraction
from pathlib import Path

import av
import numpy as np


def main() -> None:
    path = Path("artifacts/wave8-fixture.mp4")
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w") as output:
        stream = output.add_stream("libx264", rate=25)
        stream.width = stream.height = 128
        stream.pix_fmt = "yuv420p"
        for index in range(50):
            pixels = np.full((128, 128, 3), (180, 80, 40), dtype=np.uint8)
            frame = av.VideoFrame.from_ndarray(pixels, format="rgb24")
            frame.pts, frame.time_base = index, Fraction(1, 25)
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)


if __name__ == "__main__":
    main()
