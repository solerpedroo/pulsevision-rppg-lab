import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray


class ReferenceError(ValueError):
    """Reference is unavailable, malformed or not temporally usable."""


@dataclass(frozen=True)
class ReferenceSeries:
    timestamps_s: NDArray[np.float64]
    sensor_hr_bpm: NDArray[np.float64]
    ppg: NDArray[np.float64] | None = None

    def __post_init__(self) -> None:
        t, hr = self.timestamps_s, self.sensor_hr_bpm
        if t.ndim != 1 or len(t) < 2 or hr.shape != t.shape:
            raise ReferenceError("Reference requires matching 1D timestamp and HR arrays")
        if not np.isfinite(t).all() or (np.diff(t) <= 0).any():
            raise ReferenceError("Reference timestamps must be finite and strictly increasing")
        if self.ppg is not None and self.ppg.shape != t.shape:
            raise ReferenceError("PPG and timestamp lengths differ")
        # Invalid HR/PPG values are retained and exclude their windows, not removed.

    def aligned(self, origin_s: float, offset_s: float) -> "ReferenceSeries":
        if not np.isfinite([origin_s, offset_s]).all():
            raise ReferenceError("Invalid alignment transform")
        return ReferenceSeries(
            self.timestamps_s - origin_s + offset_s, self.sensor_hr_bpm.copy(), self.ppg
        )

    def window_hr(self, start_s: float, end_s: float, max_gap_s: float) -> float:
        t, hr = self.timestamps_s, self.sensor_hr_bpm
        selected = (t >= start_s) & (t < end_s)
        times, values = t[selected], hr[selected]
        if len(times) < 2:
            raise ReferenceError("reference_insufficient_samples")
        intervals = np.diff(times)
        if intervals.max() > max_gap_s + 1e-9:
            raise ReferenceError("reference_temporal_gap")
        if times[0] - start_s > max_gap_s or end_s - times[-1] > max_gap_s:
            raise ReferenceError("reference_incomplete_window")
        if not np.isfinite(values).all() or (values <= 0).any():
            raise ReferenceError("reference_invalid_hr")
        if self.ppg is not None and not np.isfinite(self.ppg[selected]).all():
            raise ReferenceError("reference_invalid_ppg")
        # Time-weighted sensor HR, zero-order hold within the SAME half-open window.
        # No interpolation across long gaps or extrapolation beyond max_gap_s.
        weights = np.diff(np.r_[times, end_s])
        weights[0] += times[0] - start_s
        return float(np.average(values, weights=weights))


def read_hr_csv(path: Path) -> ReferenceSeries:
    try:
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        t = np.array([float(row["timestamp_s"]) for row in rows])
        hr = np.array([float(row["hr_bpm"]) for row in rows])
        return ReferenceSeries(t, hr)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ReferenceError("Malformed normalized sensor HR CSV") from exc


def read_ubfc_reference(path: Path) -> ReferenceSeries:
    try:
        matrix = np.loadtxt(path, dtype=float)
        if matrix.ndim != 2 or matrix.shape[0] != 3:
            raise ReferenceError("Expected UBFC rows: PPG, sensor HR, timestamps in seconds")
        return ReferenceSeries(matrix[2], matrix[1], matrix[0])
    except (OSError, ValueError) as exc:
        raise ReferenceError("Malformed UBFC ground_truth.txt") from exc


def read_pure_reference(path: Path) -> ReferenceSeries:
    try:
        records = json.loads(path.read_text())["/FullPackage"]
        raw = [row["Timestamp"] for row in records]
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in raw):
            raise ReferenceError("PURE timestamps must be explicit integer nanoseconds")
        t = np.array([value / 1e9 for value in raw], dtype=np.float64)
        hr = np.array([float(row["Value"]["pulseRate"]) for row in records])
        ppg = np.array([float(row["Value"]["waveform"]) for row in records])
        return ReferenceSeries(t, hr, ppg)
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise ReferenceError("Malformed PURE FullPackage reference") from exc
