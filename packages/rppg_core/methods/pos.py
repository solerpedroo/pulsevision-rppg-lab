import numpy as np

from rppg_core.signals.config import SignalConfig
from rppg_core.signals.temporal import SignalQualityError

from .common import FloatArray, MethodSignal, validate_rgb
from .config import MethodConfig


def pos(
    rgb: FloatArray, fs: float, config: SignalConfig, method_config: MethodConfig
) -> MethodSignal:
    """Temporal normalization, orthogonal projection and samplewise overlap-add."""
    validate_rgb(rgb, fs)
    length = int(np.ceil(method_config.projection_window_s * fs - 1e-9))
    if length < 2 or length > len(rgb):
        raise SignalQualityError("projection_window_too_short")
    output = np.zeros(len(rgb), dtype=np.float64)
    coverage = np.zeros(len(rgb), dtype=int)
    for start in range(len(rgb) - length + 1):
        segment = rgb[start : start + length]
        mean = segment.mean(axis=0)
        if (mean <= method_config.epsilon).any():
            raise SignalQualityError("invalid_channel_mean")
        normalized = segment / (mean + method_config.epsilon)
        s1 = normalized[:, 1] - normalized[:, 2]
        s2 = -2 * normalized[:, 0] + normalized[:, 1] + normalized[:, 2]
        denominator = float(s2.std())
        if denominator <= method_config.epsilon:
            raise SignalQualityError("degenerate_pos_projection")
        pulse = s1 + float(s1.std()) / (denominator + method_config.epsilon) * s2
        output[start : start + length] += pulse - pulse.mean()
        coverage[start : start + length] += 1
    valid = coverage == length
    if not valid.any():
        raise SignalQualityError("insufficient_projection_support")
    if float(output[valid].std()) < config.min_relative_std:
        raise SignalQualityError("constant_signal")
    return MethodSignal(output, valid, False, length / fs)
