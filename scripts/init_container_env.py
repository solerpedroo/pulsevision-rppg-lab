"""Create a local Compose API key without displaying it or overwriting existing files."""

import argparse
import os
import secrets
from pathlib import Path


def create_env(path: Path) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as handle:
        handle.write("PULSEVISION_API_KEY=" + secrets.token_urlsafe(48) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(".env.containers"))
    args = parser.parse_args()
    create_env(args.output)
    print("Private environment file created with mode 0600. Key was not printed.")


if __name__ == "__main__":
    main()
