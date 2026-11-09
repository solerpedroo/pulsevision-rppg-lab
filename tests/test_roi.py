import csv
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from rppg_core.acquisition import FrameSample, VideoReader
from rppg_core.face.detector import FaceError, MediaPipeDetector
from rppg_core.roi.extraction import ExtractionConfig, summarize
from rppg_core.roi.geometry import EXCLUSIONS, REGIONS, bgr_to_rgb, orient_rgb, polygon_mask
from rppg_core.roi.pipeline import RGBExtractor
from video_factory import make_video


def landmarks():
    points = np.full((478, 2), 0.5)
    for indices, center in zip(
        REGIONS.values(), [(0.5, 0.2), (0.7, 0.55), (0.3, 0.55)], strict=True
    ):
        angle = np.linspace(0, 2 * np.pi, len(indices), endpoint=False)
        points[list(indices)] = np.column_stack(
            (center[0] + 0.09 * np.cos(angle), center[1] + 0.05 * np.sin(angle))
        )
    for indices, center in zip(
        EXCLUSIONS,
        [(0.35, 0.38), (0.65, 0.38), (0.5, 0.75), (0.35, 0.31), (0.65, 0.31)],
        strict=True,
    ):
        angle = np.linspace(0, 2 * np.pi, len(indices), endpoint=False)
        points[list(indices)] = np.column_stack(
            (center[0] + 0.025 * np.cos(angle), center[1] + 0.015 * np.sin(angle))
        )
    return points


class FakeDetector:
    def __init__(self, sequence):
        self.sequence = iter(sequence)
        self.shapes = []

    def detect(self, rgb, timestamp_s):
        self.shapes.append(rgb.shape)
        return next(self.sequence)


def frame(timestamp=0.0, color=(160, 90, 60), rotation=0):
    rgb = np.empty((256, 320, 3), dtype=np.uint8)
    rgb[:] = color
    return FrameSample(
        0, timestamp, timestamp, int(timestamp * 1000), Fraction(1, 1000), rgb, rotation, ()
    )


def test_rgb_and_orientation():
    bgr = np.array([[[10, 50, 150], [20, 60, 160]]], dtype=np.uint8)
    rgb = bgr_to_rgb(bgr)
    assert rgb[0, 0].tolist() == [150, 50, 10]
    np.testing.assert_array_equal(orient_rgb(rgb, 90), np.rot90(rgb))
    with pytest.raises(ValueError):
        orient_rgb(rgb, 45)


@pytest.mark.parametrize(
    "points",
    [
        [[-0.1, 0], [1, 0], [1, 1]],
        [[0, 0], [float("nan"), 0], [1, 1]],
        [[0.5, 0.5], [0.5, 0.5], [0.5, 0.5]],
    ],
)
def test_bad_polygons(points):
    with pytest.raises(ValueError):
        polygon_mask(np.array(points), 100, 100)


def test_exclusions_and_translation():
    from rppg_core.roi.geometry import region_masks

    points = landmarks()
    masks = region_masks(points, 320, 256)
    assert all(mask.sum() > 30 for mask in masks.values())
    moved = region_masks(points + [0.01, 0], 320, 256)
    assert np.nonzero(moved["forehead"])[1].mean() > np.nonzero(masks["forehead"])[1].mean()
    # Explicitly place one eye exclusion over the forehead ROI.
    points[list(EXCLUSIONS[0])] += [0.15, -0.18]
    cut = region_masks(points, 320, 256)
    assert cut["forehead"].sum() < masks["forehead"].sum()


def test_photometric_mask():
    rgb = np.array([[[160, 90, 60], [255, 100, 80], [0, 0, 0], [80, 100, 120]]], dtype=np.uint8)
    stats = summarize(rgb, np.ones((1, 4), dtype=bool), ExtractionConfig())
    assert stats.valid_fraction == 0.5
    assert stats.dark_fraction == stats.saturated_fraction == 0.25
    assert stats.rgb_mean == (120, 95, 90)
    assert summarize(rgb, np.zeros((1, 4), dtype=bool), ExtractionConfig()).rgb_mean is None


def test_single_face_tracking_and_loss():
    points = landmarks()
    detector = FakeDetector([[points], [points + [0.005, 0]], [], [points, points], [points]])
    extractor = RGBExtractor(detector)
    first = extractor.process(frame())
    assert len(first) == 4 and all(row.sample is not None for row in first)
    assert all(row.sample.rgb_mean == [160, 90, 60] for row in first)
    assert all("tracking_reset" in row.flags for row in first)
    moved = extractor.process(frame(0.04))
    assert all(row.sample is not None and row.motion_score > 0 for row in moved)
    assert all(
        row.sample is None and row.status == "no_face" for row in extractor.process(frame(0.08))
    )
    assert all(
        row.sample is None and row.status == "multiple_faces"
        for row in extractor.process(frame(0.12))
    )
    assert all("tracking_reset" in row.flags for row in extractor.process(frame(0.16)))


@pytest.mark.parametrize(
    "mode", ["motion", "scale", "gap", "illumination", "dark", "saturated", "geometry"]
)
def test_bad_frames_have_no_rgb(mode):
    points = landmarks()
    next_points = points.copy()
    if mode == "motion":
        next_points += [0.15, 0]
    if mode == "scale":
        next_points = 0.5 + 1.5 * (points - 0.5)
    if mode == "geometry":
        next_points[10] = [float("nan"), 0.5]
    extractor = RGBExtractor(FakeDetector([[points], [next_points]]))
    extractor.process(frame())
    color = {"dark": (0, 0, 0), "saturated": (255, 255, 255), "illumination": (220, 180, 160)}.get(
        mode, (160, 90, 60)
    )
    rows = extractor.process(frame(0.5 if mode == "gap" else 0.04, color))
    assert all(row.sample is None for row in rows)


def test_video_to_rgb(tmp_path):
    path = make_video(tmp_path / "synthetic.mov", [0, 40, 80], rotation=90, width=320, height=256)
    detector = FakeDetector([[landmarks()]] * 3)
    rows = list(RGBExtractor(detector).extract(VideoReader(path)))
    assert len(rows) == 12
    assert all(row.sample is not None for row in rows)
    assert set(detector.shapes) == {(320, 256, 3)}
    assert [row.timestamp_s for row in rows[::4]] == [0, 0.04, 0.08]


def test_atomic_export_and_no_false_rgb(tmp_path, monkeypatch):
    import rppg_core.roi.extract_rgb as cli

    class Session(FakeDetector):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(cli, "MediaPipeDetector", lambda _: Session([[], [], []]))
    video = make_video(tmp_path / "synthetic.mp4", [0, 40, 80])
    model = tmp_path / "model.task"
    model.write_bytes(b"synthetic model placeholder for fake detector")
    output = tmp_path / "rgb_traces.csv"
    result = cli.export_csv(video, model, output)
    assert result["rows"] == 12 and result["valid_rows"] == 0
    with output.open() as handle:
        rows = list(csv.DictReader(handle))
    assert all(row["r_mean"] == "" and row["landmark_status"] == "no_face" for row in rows)
    assert json.loads(output.with_suffix(".metadata.json").read_text())["single_face_only"]
    with pytest.raises(ValueError):
        cli.export_csv(video, model, output)


def test_real_mediapipe_no_face(tmp_path):
    # Optional local model; standard CI remains offline.
    model = Path("models/face_landmarker.task")
    if not model.exists():
        pytest.skip("local model not available")
    from rppg_core.roi.extract_rgb import export_csv

    video = make_video(tmp_path / "no_face.mp4", [0, 40, 80], width=128, height=128)
    result = export_csv(video, model, tmp_path / "rgb_traces.csv")
    assert result["rows"] == 12 and result["valid_rows"] == 0
    with MediaPipeDetector(model) as detector:
        blank = np.zeros((128, 128, 3), dtype=np.uint8)
        assert detector.detect(blank, 0) == []
        assert detector.detect(blank, 0.0001) == []


def test_export_failure_leaves_no_partial_files(tmp_path):
    from rppg_core.roi.extract_rgb import export_csv

    output = tmp_path / "result.csv"
    with pytest.raises(FaceError):
        export_csv(tmp_path / "absent.mp4", tmp_path / "absent.task", output)
    assert not output.exists()
    assert not list(tmp_path.glob("*.partial"))


def test_missing_model(tmp_path):
    with pytest.raises(FaceError):
        MediaPipeDetector(tmp_path / "missing.task")


def test_combined_weights_pixels_and_marks_partial():
    from rppg_core.roi.geometry import region_masks

    points = landmarks()
    source = frame()
    masks = region_masks(points, source.rgb.shape[1], source.rgb.shape[0])
    source.rgb[masks["forehead"]] = (0, 0, 0)
    source.rgb[masks["left_cheek"]] = (180, 100, 60)
    source.rgb[masks["right_cheek"]] = (120, 70, 40)
    rows = RGBExtractor(FakeDetector([[points]])).process(source)
    assert rows[0].sample is None
    assert rows[-1].sample is not None
    assert "partial_roi" in rows[-1].flags
    union = masks["left_cheek"] | masks["right_cheek"]
    np.testing.assert_allclose(rows[-1].sample.rgb_mean, source.rgb[union].mean(axis=0))


def test_multiface_mode_cannot_be_enabled():
    with pytest.raises(ValueError):
        ExtractionConfig(single_face_only=False)


def test_region_observer_uses_real_masks_and_clears_missing_faces():
    seen = []
    extractor = RGBExtractor(
        FakeDetector([[landmarks()], [], [landmarks(), landmarks()]]),
        on_regions=lambda timestamp, masks: seen.append((timestamp, masks)),
    )
    for timestamp in [0.0, 0.04, 0.08]:
        extractor.process(frame(timestamp))
    assert set(seen[0][1]) == set(REGIONS)
    assert all(mask.dtype == np.bool_ and mask.shape == (256, 320) for mask in seen[0][1].values())
    assert all(mask.any() for mask in seen[0][1].values())
    assert seen[1:] == [(0.04, {}), (0.08, {})]
