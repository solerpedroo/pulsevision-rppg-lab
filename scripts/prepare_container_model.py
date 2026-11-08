"""Stage verified public model weights for read-only container mounts; original stays private."""

import hashlib
import os
import stat
from pathlib import Path

SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"


def stage(source: Path, directory: Path) -> Path:
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError("Unexpected model checksum")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if directory.is_symlink() or stat.S_IMODE(directory.stat().st_mode) != 0o700:
        raise ValueError("Dedicated model staging directory must have mode 0700")
    target = directory / "face_landmarker.task"
    if target.exists():
        if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != SHA256:
            raise ValueError("Refusing to replace an unexpected staged model")
        return target
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o444)
    os.fchmod(descriptor, 0o444)  # Keep container readability even with a private host umask.
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(data)
    return target


def main() -> None:
    target = stage(Path("models/face_landmarker.task"), Path("artifacts/container-model"))
    print(f"Verified model staged at {target}; original unchanged. No download.")


if __name__ == "__main__":
    main()
