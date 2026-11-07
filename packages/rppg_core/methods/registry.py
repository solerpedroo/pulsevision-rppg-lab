from collections.abc import Callable
from types import MappingProxyType

import numpy as np
from rppg_types.models import Method

from rppg_core.signals.config import SignalConfig

from .chrom import chrom
from .common import FloatArray, MethodSignal, validate_rgb
from .config import MethodConfig
from .green import green
from .pos import pos

Extractor = Callable[[FloatArray, float, SignalConfig, MethodConfig], MethodSignal]


def _green(
    rgb: FloatArray, fs: float, config: SignalConfig, method_config: MethodConfig
) -> MethodSignal:
    validate_rgb(rgb, fs)
    values = green(rgb, config.min_relative_std)
    return MethodSignal(values, np.ones(len(rgb), dtype=bool), False, 0.0)


METHOD_REGISTRY: MappingProxyType[str, Extractor] = MappingProxyType(
    {
        "GREEN": _green,
        "CHROM": chrom,
        "POS": pos,
    }
)


def get_method(name: Method) -> Extractor:
    try:
        return METHOD_REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"Unknown rPPG method: {name}") from exc
