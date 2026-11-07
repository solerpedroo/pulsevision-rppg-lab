from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from rppg_core.signals.temporal import SignalInputError, SignalQualityError

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class MethodSignal:
    values: FloatArray
    valid_mask: NDArray[np.bool_]
    filtered: bool
    edge_margin_s: float


def validate_rgb(rgb: FloatArray, fs: float) -> None:
    if rgb.ndim != 2 or rgb.shape[1] != 3 or len(rgb) < 2:
        raise SignalInputError("Method requires RGB array (N,3), N>=2")
    if not np.isfinite(fs) or fs <= 0:
        raise SignalInputError("Method requires finite positive sampling frequency")
    if not np.isfinite(rgb).all() or (rgb < 0).any() or (rgb > 255).any():
        raise SignalQualityError("invalid_method_rgb")
