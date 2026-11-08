from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from rppg_types.models import EstimateResult


@dataclass(frozen=True)
class CoverageSummary:
    eligible_windows: int
    accepted_windows: int
    abstained_windows: int
    coverage: float | None
    status_counts: dict[str, int]
    reason_counts: dict[str, int]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_quality(results: Sequence[EstimateResult]) -> CoverageSummary:
    accepted = sum(item.bpm is not None for item in results)
    statuses = Counter(str(item.status) for item in results)
    reasons = Counter(
        str(reason) for item in results if item.bpm is None for reason in set(item.reasons)
    )
    return CoverageSummary(
        len(results),
        accepted,
        len(results) - accepted,
        accepted / len(results) if results else None,
        dict(statuses),
        dict(reasons),
    )
