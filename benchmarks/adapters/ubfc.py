from dataclasses import dataclass
from pathlib import Path

from .reference import ReferenceError, ReferenceSeries, read_ubfc_reference


@dataclass(frozen=True)
class UBFCSession:
    participant_id: str
    video: Path
    ground_truth: Path

    def reference(self) -> ReferenceSeries:
        return read_ubfc_reference(self.ground_truth)


def discover(root: Path) -> list[UBFCSession]:
    sessions = []
    for subject in sorted(root.glob("subject*")):
        if not subject.is_dir():
            continue
        video, reference = subject / "vid.avi", subject / "ground_truth.txt"
        if not video.is_file() or not reference.is_file():
            raise ReferenceError("Incomplete UBFC subject directory")
        sessions.append(UBFCSession(subject.name, video, reference))
    if not sessions:
        raise ReferenceError("No UBFC subject directories found")
    return sessions
