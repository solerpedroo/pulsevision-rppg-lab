"""Original face-free Y4M for Chromium's fake camera; never access a real device."""
from pathlib import Path


def main() -> None:
    target = Path("artifacts/wave9-camera.y4m")
    target.parent.mkdir(exist_ok=True)
    width, height = 320, 240
    with target.open("wb") as handle:
        handle.write(f"YUV4MPEG2 W{width} H{height} F30:1 Ip A1:1 C420jpeg\n".encode())
        frame = bytes([96]) * (width * height) + bytes([128]) * (width * height // 2)
        for _ in range(36):
            handle.write(b"FRAME\n" + frame)


if __name__ == "__main__":
    main()
