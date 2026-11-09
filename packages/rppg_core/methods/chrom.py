import numpy as np
from scipy import signal

from rppg_core.signals.config import SignalConfig
from rppg_core.signals.spectrum import bandpass
from rppg_core.signals.temporal import SignalQualityError

from .common import FloatArray, MethodSignal, validate_rgb
from .config import MethodConfig


def chrom(
    rgb: FloatArray, fs: float, config: SignalConfig, method_config: MethodConfig
) -> MethodSignal:
    """Windowed chrominance projection, per-component filtering and Hann overlap-add."""
    validate_rgb(rgb, fs)
    length = int(np.ceil(method_config.projection_window_s * fs - 1e-9))
    sections = signal.butter(
        config.filter_order, [config.low_hz, config.high_hz], btype="bandpass", fs=fs, output="sos"
    )
    # sosfiltfilt pad must fit inside each projection window.
    minimum = 3 * (2 * len(sections) + 1) + 1
    if length < minimum:
        length = minimum
    length += length % 2
    if length < 4 or length > len(rgb):
        raise SignalQualityError("projection_window_too_short")
    hop = length // 2
    output = np.zeros(len(rgb), dtype=np.float64)
    coverage = np.zeros(len(rgb), dtype=np.float64)
    taper = signal.windows.hann(length, sym=True)
    for start in range(0, len(rgb) - length + 1, hop):
        segment = rgb[start : start + length]
        mean = segment.mean(axis=0)
        if (mean <= method_config.epsilon).any():
            raise SignalQualityError("invalid_channel_mean")
        normalized = segment / mean
        x = bandpass(3 * normalized[:, 0] - 2 * normalized[:, 1], fs, config)
        y = bandpass(1.5 * normalized[:, 0] + normalized[:, 1] - 1.5 * normalized[:, 2], fs, config)
        denominator = float(y.std())
        if denominator <= method_config.epsilon:
            raise SignalQualityError("degenerate_chrom_projection")
        pulse = x - float(x.std()) / denominator * y
        output[start : start + length] += pulse * taper
        coverage[start : start + length] += taper
    valid = coverage > method_config.epsilon
    if not valid.any() or float(output[valid].std()) < config.min_relative_std:
        raise SignalQualityError("constant_signal")
    # No division by coverage: match Hann overlap-add convention; exclude edge support.
    return MethodSignal(output, valid, True, length / fs)
