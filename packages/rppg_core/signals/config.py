from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SignalConfig:
    window_s: float = 20.0
    stride_s: float = 1.0
    low_hz: float = 0.7
    high_hz: float = 3.0
    filter_order: int = 4
    edge_trim_s: float = 1.0
    welch_segment_s: float = 20.0
    max_gap_s: float = 0.15
    max_interval_ratio: float = 2.5
    min_relative_std: float = 1e-6
    min_peak_fraction: float = 0.45
    max_competing_peak_ratio: float = 0.5

    def __post_init__(self) -> None:
        if not all(np.isfinite(v) and v > 0 for v in self.__dict__.values()):
            raise ValueError("All DSP parameters must be finite and positive")
        if self.low_hz >= self.high_hz or self.window_s <= 2 * self.edge_trim_s:
            raise ValueError("Invalid band or edge trimming")
        if not isinstance(self.filter_order, int) or self.filter_order > 12:
            raise ValueError("Filter order must be an integer in 1..12")
        if self.min_peak_fraction > 1 or self.max_competing_peak_ratio > 1:
            raise ValueError("Spectral quality ratios must not exceed one")
