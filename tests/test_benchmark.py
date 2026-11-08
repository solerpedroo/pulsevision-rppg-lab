import json
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError
from rppg_core.metrics.errors import paired_metrics

from benchmarks.adapters.reference import (
    ReferenceError,
    ReferenceSeries,
    read_hr_csv,
    read_pure_reference,
    read_ubfc_reference,
)
from benchmarks.adapters.ubfc import discover
from benchmarks.analysis.aggregate import summarize
from benchmarks.manifest import (
    BenchmarkError,
    BenchmarkManifest,
    freeze,
    verify_lock,
)
from benchmarks.runners.run import run_benchmark
from benchmarks.runners.synthetic import create_demo


def test_closed_form_metrics_and_constant_correlation():
    estimated = np.array([61.0, 88.0, 123.0])
    reference = np.array([60.0, 90.0, 120.0])
    result = paired_metrics(estimated, reference)
    assert result["mae"] == 2
    assert result["medae"] == 2
    assert result["bias"] == pytest.approx(2 / 3)
    assert result["rmse"] == pytest.approx(np.sqrt(14 / 3))
    assert result["loa_low"] < result["bias"] < result["loa_high"]
    assert paired_metrics(np.ones(3), np.ones(3))["pearson_r"] is None
    assert paired_metrics(np.array([60.0]), np.array([61.0]))["loa_low"] is None
    assert paired_metrics(np.array([]), np.array([]))["mae"] is None
    with pytest.raises(ValueError):
        paired_metrics(np.array([np.nan]), np.array([60.0]))


def test_ubfc_adapter_and_native_timestamps(tmp_path):
    subject = tmp_path / "subject1"
    subject.mkdir()
    (subject / "vid.avi").write_bytes(b"discovery fixture, no decode requested")
    t = np.arange(1201) / 60 + 100
    np.savetxt(subject / "ground_truth.txt", np.vstack((np.sin(t), np.full(len(t), 75), t)))
    session = discover(tmp_path)[0]
    reference = session.reference()
    assert reference.timestamps_s[0] == 100  # No silent origin reset.
    aligned = reference.aligned(100, 0)
    assert aligned.window_hr(0, 20, 0.2) == pytest.approx(75)
    with pytest.raises(ReferenceError):
        aligned.window_hr(30, 50, 0.2)


def test_missing_ubfc_files_fail_explicitly(tmp_path):
    (tmp_path / "subject1").mkdir()
    with pytest.raises(ReferenceError):
        discover(tmp_path)


def test_reference_formats_do_not_invent_timestamps(tmp_path):
    pure = tmp_path / "pure.json"
    pure.write_text(
        json.dumps(
            {
                "/FullPackage": [
                    {"Timestamp": i * 20_000_000, "Value": {"pulseRate": 80, "waveform": i % 10}}
                    for i in range(1001)
                ]
            }
        )
    )
    ref = read_pure_reference(pure)
    assert ref.timestamps_s[-1] == 20
    assert ref.window_hr(0, 20, 0.2) == 80
    pure.write_text(json.dumps({"/FullPackage": [{"Value": {"pulseRate": 80, "waveform": 0}}]}))
    with pytest.raises(ReferenceError):
        read_pure_reference(pure)
    csv = tmp_path / "hr.csv"
    csv.write_text("timestamp_s,hr_bpm\n0,70\n.1,72\n.2,74\n")
    assert read_hr_csv(csv).window_hr(0, 0.2, 0.11) == pytest.approx(71)
    malformed = tmp_path / "wrong.txt"
    np.savetxt(malformed, np.ones((2, 30)))
    with pytest.raises(ReferenceError):
        read_ubfc_reference(malformed)


@pytest.mark.parametrize("case", ["duplicate", "reverse", "gap", "invalid_hr", "missing_edge"])
def test_reference_invalid_windows_refuse_metrics(case):
    t = np.arange(1201) / 60
    hr = np.full(len(t), 90.0)
    if case == "duplicate":
        t[10] = t[9]
    if case == "reverse":
        t[10] = t[9] - 0.1
    if case == "gap":
        keep = (t < 5) | (t > 6)
        t, hr = t[keep], hr[keep]
    if case == "invalid_hr":
        hr[100] = np.nan
    if case == "missing_edge":
        t, hr = t[60:], hr[60:]
    with pytest.raises(ReferenceError):
        ReferenceSeries(t, hr).window_hr(0, 20, 0.2)


def test_manifest_leakage_unknown_config_and_access(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    raw = json.loads(path.read_text())
    raw["splits"]["validation"] = ["synthetic01"]
    with pytest.raises(ValidationError):
        BenchmarkManifest.model_validate(raw)
    raw = json.loads(path.read_text())
    raw["signal"]["windw_s"] = 20
    with pytest.raises(ValidationError):
        BenchmarkManifest.model_validate(raw)
    raw = json.loads(path.read_text())
    raw["dataset"] = "UBFC-rPPG"
    with pytest.raises(ValidationError):
        BenchmarkManifest.model_validate(raw)


def test_freeze_detects_mutated_input_and_manifest(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    verify_lock(path, lock)
    with pytest.raises(FileExistsError):
        freeze(path, lock)
    source = path.parent / "synthetic01.csv"
    source.write_text(source.read_text() + "\n")
    with pytest.raises(BenchmarkError):
        verify_lock(path, lock)


def row(participant, error, *, accepted=True, eligible=True):
    return dict(
        participant_id=participant,
        method="GREEN",
        eligible=eligible,
        bpm=90 + error if accepted else None,
        reference_bpm=90 if eligible else None,
        reasons=[] if accepted else ["no_face"],
        exclusion_reason=None if eligible else "reference_temporal_gap",
    )


def test_participant_macro_avoids_window_weighting_and_bootstraps_subjects():
    rows = [row("a", 1)] * 100 + [row("b", 10)] + [row("c", 4)]
    result = summarize(rows, seed=42, bootstrap_samples=1000)["GREEN"]
    assert result["macro_errors"]["mae"] == 5  # Not (100+10+4)/102.
    assert result["bootstrap_unit"] == "participant"
    assert result["bootstrap_subject_ci95"] is not None
    assert result == summarize(rows, seed=42, bootstrap_samples=1000)["GREEN"]


def test_abstentions_exclusions_and_empty_subjects_are_separate():
    rows = [row("a", 1), row("a", 0, accepted=False), row("a", 0, eligible=False)]
    result = summarize(rows, seed=42, bootstrap_samples=100, participant_ids=["a", "unprocessed"])[
        "GREEN"
    ]
    assert result["eligible_windows"] == 2 and result["excluded_windows"] == 1
    assert result["window_coverage"] == 0.5
    assert result["reason_counts"] == {"no_face": 1}
    assert result["exclusion_counts"] == {"reference_temporal_gap": 1}
    assert result["participants"]["unprocessed"]["coverage"] is None
    assert result["bootstrap_subject_ci95"] is None


def test_frozen_runner_is_reproducible_without_claiming_real_accuracy(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    first = run_benchmark(path, lock, tmp_path / "first")
    second = run_benchmark(path, lock, tmp_path / "second")
    assert first["result_kind"] == "synthetic_demonstration"
    assert first["summary"] == second["summary"]
    assert first["windows"] == second["windows"]
    assert len(first["windows"]) == 3 * 3 * 4
    assert not first["session_failures"]
    assert first["session_alignment"][0]["offset_s"] == 0
    assert first["session_alignment"][0]["evidence_sha256"]
    for method in ("GREEN", "CHROM", "POS"):
        summary = first["summary"][method]
        assert summary["eligible_windows"] == 12
        assert summary["accepted_windows"] == 10  # Motion + one recovering window.
        assert summary["reason_counts"] == {"excessive_motion": 1, "recovering_signal": 1}
        assert (tmp_path / "first" / "figures" / (method.lower() + ".png")).is_file()
    assert (tmp_path / "first" / "benchmark-v1.md").is_file()
    assert (tmp_path / "first" / "windows.csv").is_file()
    assert (tmp_path / "first" / "participants.csv").is_file()
    with pytest.raises(FileExistsError):
        run_benchmark(path, lock, tmp_path / "first")


def test_unverified_alignment_produces_no_metrics(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    data = json.loads(path.read_text())
    for session in data["sessions"]:
        session["alignment"]["verified"] = False
        session["alignment"]["evidence_file"] = None
    path.write_text(json.dumps(data))
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    report = run_benchmark(path, lock, tmp_path / "report")
    assert len(report["session_failures"]) == 3
    assert report["windows"] == []
    assert report["summary"]["GREEN"]["declared_participants"] == 3
    assert report["summary"]["GREEN"]["macro_errors"]["mae"] is None
    assert report["summary"]["GREEN"]["window_coverage"] is None


def test_reference_gap_excludes_windows_before_estimator_coverage(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    reference = path.parent / "synthetic01_ground_truth.txt"
    matrix = np.loadtxt(reference)
    keep = (matrix[2] < 5) | (matrix[2] > 6)
    np.savetxt(reference, matrix[:, keep])
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    report = run_benchmark(path, lock, tmp_path / "report")
    summary = report["summary"]["GREEN"]
    assert summary["excluded_windows"] == 4
    assert summary["eligible_windows"] == 8
    assert summary["exclusion_counts"] == {"reference_temporal_gap": 4}
    assert summary["participants"]["synthetic01"]["mae"] is None


def test_short_trace_is_not_a_full_benchmark_window(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3, duration_s=5)
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    report = run_benchmark(path, lock, tmp_path / "report")
    assert report["summary"]["GREEN"]["eligible_windows"] == 0
    assert report["summary"]["GREEN"]["excluded_windows"] == 3
    assert report["summary"]["GREEN"]["window_coverage"] is None


def test_split_selection_does_not_run_reserved_participants(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    data = json.loads(path.read_text())
    data["splits"] = {
        "development": ["synthetic01", "synthetic02"],
        "validation": ["synthetic03"],
        "test": [],
    }
    path.write_text(json.dumps(data))
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    report = run_benchmark(path, lock, tmp_path / "report", split="validation")
    assert {row["participant_id"] for row in report["windows"]} == {"synthetic03"}
    with pytest.raises(BenchmarkError):
        run_benchmark(path, lock, tmp_path / "invalid", split="test")


def test_malformed_reference_excludes_session_not_fakes_hr(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    (path.parent / "synthetic01_ground_truth.txt").write_text("malformed")
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    report = run_benchmark(path, lock, tmp_path / "report")
    assert len(report["session_failures"]) == 1
    assert all(row["participant_id"] != "synthetic01" for row in report["windows"])


def test_offset_is_explicit_not_optimized():
    ref = ReferenceSeries(np.arange(0, 21, 0.1), np.full(210, 90.0))
    shifted = ref.aligned(0, 10)
    with pytest.raises(ReferenceError):
        shifted.window_hr(0, 20, 0.2)
    assert shifted.window_hr(10, 30, 0.2) == pytest.approx(90)


def test_manifest_changes_invalidate_frozen_protocol(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    data = json.loads(path.read_text())
    data["quality"]["max_motion"] = 0.9
    path.write_text(json.dumps(data))
    with pytest.raises(BenchmarkError):
        verify_lock(path, lock)


def test_video_path_runs_without_retaining_intermediate_rgb(tmp_path):
    from video_factory import make_video

    model = Path("models/face_landmarker.task").resolve()
    if not model.exists():
        pytest.skip("Optional local model unavailable")
    path = create_demo(tmp_path / "demo", subjects=3)
    data = json.loads(path.read_text())
    data["sessions"] = [data["sessions"][0]]
    video = make_video(path.parent / "blank.avi", list(range(0, 21_000, 40)), width=128, height=128)
    session = data["sessions"][0]
    session.pop("rgb_csv")
    session["video"] = video.name
    data["model_path"] = str(model)
    path.write_text(json.dumps(data))
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    output = tmp_path / "result"
    report = run_benchmark(path, lock, output)
    assert not report["session_failures"]
    assert report["summary"]["GREEN"]["eligible_windows"] == 2
    assert report["summary"]["GREEN"]["accepted_windows"] == 0
    assert report["summary"]["GREEN"]["macro_errors"]["mae"] is None
    assert not list(output.glob("trace-*"))


def test_bad_lock_is_rejected_cleanly(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    lock = tmp_path / "lock.json"
    lock.write_text("[]")
    with pytest.raises(BenchmarkError):
        verify_lock(path, lock)


def test_reference_interval_matches_shared_spectral_support(tmp_path):
    path = create_demo(tmp_path / "demo", subjects=3)
    lock = tmp_path / "lock.json"
    freeze(path, lock)
    report = run_benchmark(path, lock, tmp_path / "report")
    for row in report["windows"]:
        if row["bpm"] is not None:
            metadata = row["estimate"]["metadata"]
            assert row["reference_start_s"] == pytest.approx(metadata["valid_start_s"])
            assert row["reference_end_s"] == pytest.approx(
                metadata["valid_end_s"] + 1 / metadata["resample_fs"]
            )
