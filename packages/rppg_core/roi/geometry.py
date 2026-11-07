import cv2
import numpy as np
from numpy.typing import NDArray

# Anatomical left/right, for non-mirrored input. Version: roi-v1.
REGIONS = {
    "forehead": (109, 10, 338, 337, 151, 108),
    "left_cheek": (280, 330, 347, 346, 352, 411, 425, 266),
    "right_cheek": (50, 101, 118, 117, 123, 187, 205, 36),
}
EXCLUSIONS = (
    (33, 160, 158, 133, 153, 144),
    (362, 385, 387, 263, 373, 380),
    (61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91),
    (70, 63, 105, 66, 107, 55, 65, 52, 53, 46),
    (336, 296, 334, 293, 300, 276, 283, 282, 295, 285),
)


def orient_rgb(rgb: NDArray[np.uint8], rotation_degrees: int) -> NDArray[np.uint8]:
    if rotation_degrees % 90:
        raise ValueError("Only quarter-turn display rotations are supported")
    return np.ascontiguousarray(np.rot90(rgb, k=rotation_degrees // 90))


def bgr_to_rgb(bgr: NDArray[np.uint8]) -> NDArray[np.uint8]:
    return np.ascontiguousarray(bgr[..., ::-1])


def polygon_mask(
    points: NDArray[np.float64],
    width: int,
    height: int,
    *,
    shrink: float = 0.85,
) -> NDArray[np.bool_]:
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3:
        raise ValueError("Polygon requires at least three 2D vertices")
    if not np.isfinite(points).all() or (points < 0).any() or (points > 1).any():
        raise ValueError("Polygon outside normalized image bounds")
    if not 0 < shrink <= 1 or width <= 0 or height <= 0:
        raise ValueError("Invalid polygon dimensions/shrink")
    center = points.mean(axis=0)
    pixels = np.rint((center + shrink * (points - center)) * [width - 1, height - 1])
    polygon = pixels.astype(np.int32)
    if abs(cv2.contourArea(polygon)) < 4:
        raise ValueError("Degenerate ROI")
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [polygon], 1)
    return mask.astype(bool)


def region_masks(
    landmarks: NDArray[np.float64],
    width: int,
    height: int,
) -> dict[str, NDArray[np.bool_]]:
    if landmarks.shape != (478, 2) or not np.isfinite(landmarks).all():
        raise ValueError("Expected 478 finite 2D landmarks")
    excluded = np.zeros((height, width), dtype=bool)
    for excluded_indices in EXCLUSIONS:
        excluded |= polygon_mask(landmarks[list(excluded_indices)], width, height, shrink=1)
    masks = {}
    for name, indices in REGIONS.items():
        masks[name] = polygon_mask(landmarks[list(indices)], width, height) & ~excluded
    return masks
