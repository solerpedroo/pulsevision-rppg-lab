from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


class SignalInputError(ValueError):
    """Malformed trace: no meaningful window can be assigned."""


class SignalQualityError(ValueError):
    """A meaningful window exists, but no estimate should be emitted."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class UniformTrace:
    timestamps_s: FloatArray
    rgb: FloatArray
    fs: float
    resampled: bool


def validate_trace(timestamps: FloatArray, rgb: FloatArray) -> None:
    if timestamps.ndim != 1 or rgb.shape != (len(timestamps), 3):
        raise SignalInputError("Expected timestamps (N,) and RGB (N,3)")
    if len(timestamps) < 2:
        raise SignalInputError("At least two timestamped rows are required")
    if not np.isfinite(timestamps).all() or (timestamps < 0).any():
        raise SignalInputError("Timestamps must be finite and nonnegative")
    if (np.diff(timestamps) <= 0).any():
        raise SignalInputError("Timestamps must increase strictly")


def uniform_trace(
    timestamps: FloatArray,
    rgb: FloatArray,
    *,
    max_gap_s: float,
    max_interval_ratio: float,
) -> UniformTrace:
    validate_trace(timestamps, rgb)
    if not np.isfinite(rgb).all():
        raise SignalQualityError("nonfinite_rgb")
    if (rgb < 0).any() or (rgb > 255).any():
        raise SignalQualityError("rgb_out_of_range")
    intervals = np.diff(timestamps)
    dt = float(np.median(intervals))
    if intervals.max() > min(max_gap_s, max_interval_ratio * dt) + 1e-9:
        raise SignalQualityError("temporal_gap")
    fs = 1 / dt
    if np.allclose(intervals, dt, rtol=1e-5, atol=1e-9):
        return UniformTrace(timestamps.copy(), rgb.copy(), fs, False)
    # Linear interpolation at median cadence, without extrapolation or downsampling.
    grid = timestamps[0] + np.arange(int(np.floor((timestamps[-1] - timestamps[0]) / dt)) + 1) * dt
    values = np.column_stack([np.interp(grid, timestamps, rgb[:, i]) for i in range(3)])
    return UniformTrace(grid, values, fs, True)
