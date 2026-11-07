from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class PixelStats:
    rgb_mean: tuple[float, float, float] | None
    area: int
    valid_pixels: int
    valid_fraction: float
    dark_fraction: float
    saturated_fraction: float
    brightness: float | None


@dataclass(frozen=True)
class ExtractionConfig:
    single_face_only: bool = True
    min_pixels: int = 30
    min_valid_fraction: float = 0.5
    dark_threshold: float = 25
    saturated_threshold: float = 245
    max_motion: float = 0.08
    max_scale_change: float = 0.2
    max_brightness_change: float = 0.2
    max_tracking_gap_s: float = 0.25

    def __post_init__(self) -> None:
        if self.single_face_only is not True:
            raise ValueError("This pipeline only supports single_face_only=True")
        values = list(self.__dict__.values())
        if not all(np.isfinite(v) and v > 0 for v in values):
            raise ValueError("Quality parameters must be finite and positive")
        if self.min_pixels < 1 or self.min_valid_fraction > 1:
            raise ValueError("Invalid pixel thresholds")
        if not self.dark_threshold < self.saturated_threshold <= 255:
            raise ValueError("Require dark_threshold < saturated_threshold <= 255")


def summarize(
    rgb: NDArray[np.uint8],
    mask: NDArray[np.bool_],
    config: ExtractionConfig,
) -> PixelStats:
    pixels = rgb[mask]
    area = len(pixels)
    if not area:
        return PixelStats(None, 0, 0, 0, 0, 0, None)
    brightness = pixels.mean(axis=1)
    dark = brightness < config.dark_threshold
    saturated = pixels.max(axis=1) >= config.saturated_threshold
    valid = ~(dark | saturated)
    count = int(valid.sum())
    mean = pixels[valid].mean(axis=0) if count else None
    return PixelStats(
        None if mean is None else (float(mean[0]), float(mean[1]), float(mean[2])),
        area,
        count,
        count / area,
        float(dark.mean()),
        float(saturated.mean()),
        float(brightness.mean()),
    )
