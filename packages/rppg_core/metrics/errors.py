from typing import Any

import numpy as np
from numpy.typing import NDArray


def paired_metrics(
    estimated: NDArray[np.float64], reference: NDArray[np.float64]
) -> dict[str, Any]:
    if estimated.ndim != 1 or reference.shape != estimated.shape:
        raise ValueError("Metrics require matching 1D pairs")
    if not np.isfinite(estimated).all() or not np.isfinite(reference).all():
        raise ValueError("Metrics reject nonfinite pairs; do not drop them silently")
    n = len(estimated)
    if not n:
        return dict(
            n=0,
            mae=None,
            rmse=None,
            medae=None,
            bias=None,
            pearson_r=None,
            loa_low=None,
            loa_high=None,
        )
    error = estimated - reference
    bias = float(error.mean())
    spread = float(error.std(ddof=1)) if n > 1 else None
    pearson = (
        float(np.corrcoef(estimated, reference)[0, 1])
        if n > 1 and estimated.std() > 1e-12 and reference.std() > 1e-12
        else None
    )
    return {
        "n": n,
        "mae": float(np.abs(error).mean()),
        "rmse": float(np.sqrt((error**2).mean())),
        "medae": float(np.median(np.abs(error))),
        "bias": bias,
        "pearson_r": pearson,
        "loa_low": bias - 1.96 * spread if spread is not None else None,
        "loa_high": bias + 1.96 * spread if spread is not None else None,
    }
