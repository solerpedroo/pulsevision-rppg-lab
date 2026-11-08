import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class QualityConfig:
    version: str = "quality-v1"
    min_pixel_fraction: float = 0.5
    min_pixels: int = 30
    max_dark_fraction: float = 0.4
    max_saturated_fraction: float = 0.1
    max_motion: float = 0.08
    dark_brightness_threshold: float = 25.0
    saturated_channel_threshold: float = 245.0
    max_brightness_step: float = 0.2
    max_illumination_cv: float = 0.1
    max_interval_cv: float = 0.2
    min_temporal_coverage: float = 0.9
    min_band_energy_fraction: float = 0.25
    max_bpm_jump: float = 15.0
    confirmation_tolerance_bpm: float = 6.0
    confirmation_windows: int = 2
    max_history_gap_s: float = 3.0
    max_estimate_age_s: float = 3.0

    def __post_init__(self) -> None:
        if self.version != "quality-v1":
            raise ValueError("Unknown quality policy")
        numbers = [v for key, v in self.__dict__.items() if key != "version"]
        if not all(np.isfinite(v) and v > 0 for v in numbers):
            raise ValueError("Quality parameters must be finite and positive")
        if not self.dark_brightness_threshold < self.saturated_channel_threshold <= 255:
            raise ValueError("Invalid photometric intensity thresholds")
        for name in (
            "min_pixel_fraction",
            "max_dark_fraction",
            "max_saturated_fraction",
            "min_temporal_coverage",
            "min_band_energy_fraction",
        ):
            if getattr(self, name) > 1:
                raise ValueError("Fraction thresholds must not exceed one")
        if not isinstance(self.min_pixels, int) or not isinstance(self.confirmation_windows, int):
            raise ValueError("Counts must be integers")


def load_quality_config(path: Path) -> QualityConfig:
    try:
        return QualityConfig(**json.loads(path.read_text()))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid quality configuration") from exc
