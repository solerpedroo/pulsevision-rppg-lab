import numpy as np
from numpy.typing import NDArray
from scipy import signal

from .config import SignalConfig
from .temporal import SignalQualityError

FloatArray = NDArray[np.float64]


def bandpass(values: FloatArray, fs: float, config: SignalConfig) -> FloatArray:
    if fs / 2 <= config.high_hz:
        raise SignalQualityError("insufficient_nyquist")
    sos = signal.butter(
        config.filter_order, [config.low_hz, config.high_hz], btype="bandpass", fs=fs, output="sos"
    )
    try:
        # Offline only: samples on both sides contribute.
        filtered = np.asarray(signal.sosfiltfilt(sos, values, padtype="odd"), dtype=np.float64)
    except ValueError as exc:
        raise SignalQualityError("filter_window_too_short") from exc
    if not np.isfinite(filtered).all():
        raise SignalQualityError("nonfinite_filtered_signal")
    return filtered


def spectrum(values: FloatArray, fs: float, config: SignalConfig) -> tuple[FloatArray, FloatArray]:
    segment = min(len(values), int(round(config.welch_segment_s * fs)))
    if segment < 8:
        raise SignalQualityError("insufficient_spectral_resolution")
    frequencies, power = signal.welch(
        values,
        fs=fs,
        window="hann",
        nperseg=segment,
        noverlap=segment // 2,
        nfft=segment,
        detrend=False,
        scaling="density",
        average="mean",
    )
    return np.asarray(frequencies, dtype=np.float64), np.asarray(power, dtype=np.float64)


def select_peak(
    frequencies: FloatArray,
    power: FloatArray,
    config: SignalConfig,
) -> tuple[float, float, float]:
    band = (frequencies >= config.low_hz) & (frequencies <= config.high_hz)
    indices = np.flatnonzero(band)
    if len(indices) < 3 or not np.isfinite(power).all() or power[band].sum() <= 0:
        raise SignalQualityError("insufficient_spectral_energy")
    peak = int(indices[np.argmax(power[band])])
    if peak in (indices[0], indices[-1]):
        raise SignalQualityError("peak_at_band_edge")
    spacing = float(frequencies[1] - frequencies[0])
    local = band & (np.abs(frequencies - frequencies[peak]) <= spacing * 1.01)
    concentration = float(power[local].sum() / power[band].sum())
    competitors = band & (np.abs(frequencies - frequencies[peak]) > spacing * 2.01)
    ratio = float(power[competitors].max() / power[peak]) if competitors.any() else 0.0
    if concentration < config.min_peak_fraction:
        raise SignalQualityError("diffuse_spectrum")
    if ratio > config.max_competing_peak_ratio:
        raise SignalQualityError("ambiguous_peaks")
    return float(frequencies[peak]), concentration, spacing
