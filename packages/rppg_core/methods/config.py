import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class MethodConfig:
    version: str = "classical-v1"
    projection_window_s: float = 1.6
    epsilon: float = 1e-9

    def __post_init__(self) -> None:
        if self.version != "classical-v1":
            raise ValueError("Unknown method configuration version")
        if not all(np.isfinite(v) and v > 0 for v in (self.projection_window_s, self.epsilon)):
            raise ValueError("Method parameters must be finite and positive")


def load_method_config(path: Path) -> MethodConfig:
    try:
        return MethodConfig(**json.loads(path.read_text()))
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid versioned method configuration") from exc
