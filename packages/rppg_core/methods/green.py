import numpy as np
from numpy.typing import NDArray
from scipy import signal

from rppg_core.signals.temporal import SignalQualityError


def green(rgb: NDArray[np.float64], min_relative_std: float = 1e-6) -> NDArray[np.float64]:
    """G / mean(G) - 1, then linear detrend; no standard-deviation amplification."""
    green_channel = rgb[:, 1]
    mean = float(green_channel.mean())
    if mean <= 0:
        raise SignalQualityError("constant_signal")
    normalized = green_channel / mean - 1
    detrended = np.asarray(signal.detrend(normalized, type="linear"), dtype=np.float64)
    if float(detrended.std()) < min_relative_std:
        raise SignalQualityError("constant_signal")
    return detrended
