import math
from pathlib import Path
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

Landmarks = NDArray[np.float64]


class FaceError(Exception):
    """Model, detector or input failure."""


class FaceDetector(Protocol):
    def detect(self, rgb: NDArray[np.uint8], timestamp_s: float) -> list[Landmarks]: ...


class MediaPipeDetector:
    """Session-scoped VIDEO detector. Two detections allow rejecting multiple faces."""

    def __init__(self, model_path: str | Path) -> None:
        import mediapipe as mp  # type: ignore[import-untyped]

        if not Path(model_path).is_file():
            raise FaceError("Provide an existing Face Landmarker .task model")
        self._mp = mp
        self._last_ms = -1
        try:
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=mp.tasks.BaseOptions(
                    model_asset_path=str(model_path),
                    delegate=mp.tasks.BaseOptions.Delegate.CPU,
                ),
                running_mode=mp.tasks.vision.RunningMode.VIDEO,
                num_faces=2,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                min_tracking_confidence=0.5,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False,
            )
            self._task: Any = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        except (RuntimeError, ValueError, OSError) as exc:
            raise FaceError("Cannot initialize Face Landmarker model") from exc

    def detect(self, rgb: NDArray[np.uint8], timestamp_s: float) -> list[Landmarks]:
        if not math.isfinite(timestamp_s) or timestamp_s < 0:
            raise FaceError("Timestamp must be finite and nonnegative")
        timestamp_ms = math.floor(timestamp_s * 1000)
        if timestamp_ms <= self._last_ms:
            raise FaceError("VIDEO timestamps collide or regress at millisecond precision")
        if rgb.dtype != np.uint8 or rgb.ndim != 3 or rgb.shape[2] != 3:
            raise FaceError("Detector requires uint8 RGB image")
        try:
            result = self._task.detect_for_video(
                self._mp.Image(
                    image_format=self._mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)
                ),
                timestamp_ms,
            )
        except (RuntimeError, ValueError) as exc:
            raise FaceError("Face Landmarker inference failed") from exc
        self._last_ms = timestamp_ms
        return [
            np.array([(p.x, p.y) for p in face], dtype=np.float64) for face in result.face_landmarks
        ]

    def close(self) -> None:
        self._task.close()

    def __enter__(self) -> "MediaPipeDetector":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
