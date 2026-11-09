from collections.abc import Callable, Generator
from contextlib import closing
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from rppg_types.models import RGBSample, Roi

from rppg_core.acquisition import FrameSample, VideoReader
from rppg_core.face.detector import FaceDetector

from .extraction import ExtractionConfig, PixelStats, summarize
from .geometry import REGIONS, orient_rgb, region_masks

LandmarkStatus = Literal["ok", "no_face", "multiple_faces", "unreliable"]
ROIS: tuple[Roi, ...] = ("forehead", "left_cheek", "right_cheek", "combined")


@dataclass(frozen=True)
class Observation:
    timestamp_s: float
    roi: Roi
    status: LandmarkStatus
    sample: RGBSample | None
    stats: PixelStats | None
    flags: tuple[str, ...]
    motion_score: float | None


class RGBExtractor:
    def __init__(
        self,
        detector: FaceDetector,
        config: ExtractionConfig | None = None,
        on_regions: Callable[[float, dict[str, NDArray[np.bool_]]], None] | None = None,
    ) -> None:
        self.on_regions = on_regions
        self.detector = detector
        self.config = config or ExtractionConfig()
        self.previous: NDArray[np.float64] | None = None
        self.previous_s: float | None = None
        self.last_accepted_s: float | None = None
        self.source_origin_s: float | None = None
        self.previous_brightness: dict[str, float] = {}

    def process(self, frame: FrameSample) -> list[Observation]:
        if self.source_origin_s is None:
            self.source_origin_s = frame.source_timestamp_s
        try:
            rgb = orient_rgb(frame.rgb, frame.rotation_degrees, frame.mirrored)
        except ValueError:
            return [
                Observation(
                    frame.timestamp_s,
                    roi,
                    "unreliable",
                    None,
                    None,
                    tuple(frame.quality_flags) + ("invalid_geometry",),
                    None,
                )
                for roi in ROIS
            ]
        if self.previous_s is not None and frame.timestamp_s <= self.previous_s:
            raise ValueError("Extractor requires strictly increasing session timestamps")
        faces = self.detector.detect(rgb, frame.timestamp_s)
        flags = list(frame.quality_flags)
        if len(faces) != 1:
            if self.on_regions:
                self.on_regions(frame.timestamp_s, {})
            status: LandmarkStatus = "no_face" if not faces else "multiple_faces"
            self.previous = None
            self.previous_brightness.clear()
            self.previous_s = frame.timestamp_s
            return [
                Observation(
                    frame.timestamp_s, roi, status, None, None, tuple(flags + [status]), None
                )
                for roi in ROIS
            ]
        landmarks = faces[0]
        try:
            masks = region_masks(landmarks, rgb.shape[1], rgb.shape[0])
        except ValueError:
            if self.on_regions:
                self.on_regions(frame.timestamp_s, {})
            self.previous = None
            self.previous_brightness.clear()
            self.previous_s = frame.timestamp_s
            return [
                Observation(
                    frame.timestamp_s,
                    roi,
                    "unreliable",
                    None,
                    None,
                    tuple(flags + ["invalid_geometry"]),
                    None,
                )
                for roi in ROIS
            ]
        if self.on_regions:
            self.on_regions(frame.timestamp_s, {name: mask.copy() for name, mask in masks.items()})
        motion = 0.0
        reject = False
        if self.previous is None:
            flags.append("tracking_reset")
            if (
                self.last_accepted_s is not None
                and frame.timestamp_s - self.last_accepted_s > self.config.max_tracking_gap_s
            ):
                flags.append("tracking_gap")
                reject = True
        else:
            scale = float(np.linalg.norm(np.ptp(self.previous, axis=0)))
            motion = float(
                np.sqrt(np.mean(np.sum((landmarks - self.previous) ** 2, axis=1)))
                / max(scale, 1e-9)
            )
            scale_change = abs(
                float(np.linalg.norm(np.ptp(landmarks, axis=0))) / max(scale, 1e-9) - 1
            )
            if motion > self.config.max_motion or scale_change > self.config.max_scale_change:
                flags.append("unstable_geometry")
                reject = True
            elif (
                self.last_accepted_s is not None
                and frame.timestamp_s - self.last_accepted_s > self.config.max_tracking_gap_s
            ):
                flags.append("tracking_gap")
                reject = True
        self.previous_s = frame.timestamp_s
        observations = []
        valid_masks = []
        for roi in ROIS[:-1]:
            mask = masks.get(roi)
            if mask is None:
                observations.append(
                    Observation(
                        frame.timestamp_s,
                        roi,
                        "unreliable",
                        None,
                        None,
                        tuple(flags + ["invalid_geometry"]),
                        motion,
                    )
                )
                continue
            stats = summarize(rgb, mask, self.config)
            local_flags = flags.copy()
            if stats.valid_pixels < self.config.min_pixels:
                local_flags.append("insufficient_pixels")
            if stats.valid_fraction < self.config.min_valid_fraction:
                local_flags.append("low_valid_fraction")
            if stats.dark_fraction:
                local_flags.append("dark_pixels")
            if stats.dark_fraction > self.config.max_dark_fraction:
                local_flags.append("dark_roi")
            if stats.saturated_fraction:
                local_flags.append("saturated_pixels")
            if stats.saturated_fraction > self.config.max_saturated_fraction:
                local_flags.append("saturated_roi")
            if stats.brightness is not None:
                old = self.previous_brightness.get(roi)
                if old is not None and abs(stats.brightness - old) / max(old, 1) > (
                    self.config.max_brightness_change
                ):
                    local_flags.append("illumination_change")
            invalid = reject or any(
                x in local_flags
                for x in (
                    "insufficient_pixels",
                    "low_valid_fraction",
                    "illumination_change",
                    "dark_roi",
                    "saturated_roi",
                    "tracking_gap",
                )
            )
            if not invalid and stats.brightness is not None:
                self.previous_brightness[roi] = stats.brightness
            sample = None
            if not invalid and stats.rgb_mean is not None:
                sample = RGBSample(
                    timestamp_s=frame.timestamp_s,
                    roi=roi,
                    rgb_mean=list(stats.rgb_mean),
                    valid_pixel_fraction=stats.valid_fraction,
                    landmark_status="ok",
                    motion_score=motion,
                    quality_flags=local_flags,
                )
                valid_masks.append(mask)
            observations.append(
                Observation(
                    frame.timestamp_s,
                    roi,
                    "unreliable" if invalid else "ok",
                    sample,
                    stats,
                    tuple(local_flags),
                    motion,
                )
            )
        if not reject and any(item.sample is not None for item in observations):
            self.previous = landmarks.copy()
            self.last_accepted_s = frame.timestamp_s
        else:
            self.previous = None
        combined_mask = np.zeros(rgb.shape[:2], dtype=bool)
        for mask in valid_masks:
            combined_mask |= mask
        stats = summarize(rgb, combined_mask, self.config)
        combined_flags = flags + ([] if valid_masks else ["no_valid_roi"])
        if len(valid_masks) < len(REGIONS):
            combined_flags.append("partial_roi")
        combined = None
        if stats.rgb_mean is not None:
            combined = RGBSample(
                timestamp_s=frame.timestamp_s,
                roi="combined",
                rgb_mean=list(stats.rgb_mean),
                valid_pixel_fraction=stats.valid_fraction,
                landmark_status="ok",
                motion_score=motion,
                quality_flags=combined_flags,
            )
        observations.append(
            Observation(
                frame.timestamp_s,
                "combined",
                "ok" if combined else "unreliable",
                combined,
                stats,
                tuple(combined_flags),
                motion,
            )
        )
        return observations

    def extract(self, reader: VideoReader) -> Generator[Observation, None, None]:
        with closing(reader.frames()) as frames:
            for frame in frames:
                yield from self.process(frame)
