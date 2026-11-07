"""Explicit download of the official, versioned model; never runs during imports or CI."""

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/1/face_landmarker.task"
)
SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def main() -> None:
    target = Path("models/face_landmarker.task")
    target.parent.mkdir(exist_ok=True)
    if target.exists():
        if hashlib.sha256(target.read_bytes()).hexdigest() != SHA256:
            raise ValueError("Existing model has an unexpected SHA256; refusing to overwrite")
        print("Verified existing model")
        return
    descriptor, temporary = tempfile.mkstemp(dir=target.parent, suffix=".partial")
    try:
        with os.fdopen(descriptor, "wb") as output:
            with urllib.request.urlopen(URL, timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        if hashlib.sha256(Path(temporary).read_bytes()).hexdigest() != SHA256:
            raise ValueError("Downloaded model SHA256 mismatch")
        os.link(temporary, target)
        print("Downloaded and verified models/face_landmarker.task")
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
